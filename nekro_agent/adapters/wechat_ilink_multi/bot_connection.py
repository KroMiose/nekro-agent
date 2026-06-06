import asyncio
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles

from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_adapter_instance import DBAdapterInstance
from nekro_agent.models.db_adapter_instance_session import DBAdapterInstanceSession
from nekro_agent.services.adapter_instance_service import adapter_instance_service

from .client import OpenILinkMonitorCallbacks, OpenILinkMultiClient
from .config import WeChatILinkMultiConfig
from .message_processor import OpenILinkMultiMessageProcessor
from .schemas import (
    ContextToken,
    MediaKind,
    OpenILinkCredentials,
    OpenILinkMedia,
    OpenILinkMessage,
    OpenILinkRecipient,
    RecipientKind,
    SyncState,
)

if TYPE_CHECKING:
    from .adapter import WeChatILinkMultiAdapter

logger = get_sub_logger("adapter.wechat_ilink_multi.connection")

ClientFactory = Callable[[WeChatILinkMultiConfig], OpenILinkMultiClient]
DEDUP_MAX_SIZE = 2000


class BotConnection:
    """单个 OpenILink 多实例账号连接。"""

    def __init__(
        self,
        *,
        adapter: "WeChatILinkMultiAdapter",
        instance: DBAdapterInstance,
        session: DBAdapterInstanceSession,
        config: WeChatILinkMultiConfig,
        client_factory: ClientFactory,
    ):
        self.adapter = adapter
        self.instance = instance
        self.session = session
        self.config = config
        self.client = client_factory(config)
        self.processor = OpenILinkMultiMessageProcessor(
            instance_id=instance.instance_key,
            adapter_key=adapter.key,
            dedup_window_seconds=config.DEDUP_WINDOW_SECONDS,
            build_chat_key=adapter.build_chat_key,
        )
        self._monitor_task: asyncio.Task[None] | None = None
        self._renew_task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()
        self._online_started = asyncio.Event()
        self._startup_error: str | None = None
        self._online = False
        self._recent_remote_message_ids: dict[tuple[str, str], float] = {}
        self._last_dedup_gc_ts = 0.0

    @property
    def instance_key(self) -> str:
        return self.instance.instance_key

    @property
    def is_online(self) -> bool:
        return self._online

    async def start(self) -> None:
        if self._monitor_task is not None and not self._monitor_task.done():
            return

        self._stopped.clear()
        self._online_started.clear()
        self._startup_error = None
        self._monitor_task = asyncio.create_task(
            self._run_monitor(),
            name=f"wechat-ilink-monitor-{self.instance_key}",
        )
        self._renew_task = asyncio.create_task(
            self._run_renew_loop(),
            name=f"wechat-ilink-renew-{self.instance_key}",
        )

    async def wait_until_online(self, timeout_seconds: float | None = None) -> None:
        if self._online:
            return
        if self._monitor_task is None:
            raise RuntimeError(f"实例 {self.instance_key} 尚未启动监控任务")

        online_waiter = asyncio.create_task(self._online_started.wait())
        done, pending = await asyncio.wait(
            {online_waiter, self._monitor_task},
            timeout=timeout_seconds,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if online_waiter in pending:
            online_waiter.cancel()
        if online_waiter in done and self._online:
            return
        if self._startup_error:
            raise RuntimeError(self._startup_error)
        if self._monitor_task.done():
            raise RuntimeError(f"实例 {self.instance_key} 监控任务已退出")
        raise TimeoutError(f"实例 {self.instance_key} 监控启动超时")

    async def stop(self) -> None:
        self._stopped.set()
        tasks = [task for task in (self._renew_task, self._monitor_task) if task is not None]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._renew_task = None
        self._monitor_task = None
        await self._stop_client_monitor()
        self._online = False

    async def send_text(
        self,
        *,
        recipient: OpenILinkRecipient,
        text: str,
        ref_msg_id: str | None = None,
    ) -> str:
        result = await self.client.send_text(
            recipient=recipient,
            text=text,
            context_token=self._build_context_token(recipient, ref_msg_id),
        )
        return result.message_id

    async def send_file(
        self,
        *,
        recipient: OpenILinkRecipient,
        file_path: Path,
        ref_msg_id: str | None = None,
    ) -> str:
        result = await self.client.send_file(
            recipient=recipient,
            file_path=file_path,
            context_token=self._build_context_token(recipient, ref_msg_id),
        )
        return result.message_id

    async def download_media(self, media: OpenILinkMedia) -> bytes | Path:
        if media.size_bytes is not None and media.size_bytes > self.config.MEDIA_DOWNLOAD_MAX_BYTES:
            raise ValueError(f"媒体文件过大: {media.size_bytes} bytes")
        return await asyncio.wait_for(
            self.client.download_media(media),
            timeout=self.config.MEDIA_DOWNLOAD_TIMEOUT_SECONDS,
        )

    async def renew_once(self) -> None:
        previous_status = self.instance.status
        self.instance = await adapter_instance_service.set_status(
            self.instance,
            "renewing",
            "实例会话续期中",
        )
        try:
            credentials = self._load_credentials()
            sync_state = self._load_sync_state()
            result = await self.client.renew_session(credentials, sync_state)
        except Exception as e:
            await self._mark_renew_failure(e)
            raise

        self.session = await adapter_instance_service.upsert_session(
            instance=self.instance,
            credentials_json=result.credentials.model_dump_json(),
            sync_state_json=result.sync_state.model_dump_json(),
            expires_at=result.credentials.expires_at,
            last_cursor=result.sync_state.cursor or "",
        )
        self.session.renewed_at = datetime.now(timezone.utc)
        await self.session.save()
        if result.credentials.expires_at is not None:
            self.instance = await adapter_instance_service.schedule_renew(
                instance=self.instance,
                expires_at=result.credentials.expires_at,
                renew_before_minutes=self.instance.renew_before_minutes or self.config.DEFAULT_RENEW_BEFORE_MINUTES,
            )
        restored_status = previous_status if previous_status not in ("renewing", "error") else "online"
        self.instance = await adapter_instance_service.set_status(
            self.instance,
            restored_status,
            "实例会话续期完成",
        )
        logger.info(f"OpenILink 多实例会话续期完成: instance={self.instance_key}")

    async def _run_monitor(self) -> None:
        try:
            await self.client.start_monitor(
                credentials=self._load_credentials(),
                sync_state=self._load_sync_state(),
                callbacks=OpenILinkMonitorCallbacks(
                    on_message=self._handle_message,
                    on_sync_state=self._handle_sync_state,
                    on_error=self._handle_monitor_error,
                ),
            )
            # 必须先持久化 online 状态并发出 SSE 事件，再放行 wait_until_online，
            # 否则等待方可能在 DB 仍为 binding、online 事件尚未广播时就返回（竞态）。
            self._online = True
            self.instance = await adapter_instance_service.set_status(
                self.instance,
                "online",
                "实例监控已启动",
            )
            self._online_started.set()
            await self._stopped.wait()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._online = False
            self._startup_error = str(e)
            self._online_started.set()
            self.instance = await adapter_instance_service.set_status(
                self.instance,
                "error",
                str(e),
            )
            logger.warning(f"OpenILink 多实例监控失败: instance={self.instance_key}, error={e}")
        finally:
            self._online = False
            await self._stop_client_monitor()

    async def _run_renew_loop(self) -> None:
        consecutive_failures = 0
        try:
            while not self._stopped.is_set():
                if self.instance.next_renew_at is None and self.session.expires_at is None:
                    # 无任何过期信息（如 iLink token 无 TTL）-> 无需续期，休眠至停止；
                    # 避免对无过期会话每小时空转 renew_once 产生 renewing<->online 抖动与 SSE 噪声。
                    await self._stopped.wait()
                    return
                wait_seconds = self._seconds_until_next_renew()
                if consecutive_failures > 0:
                    # 续期失败后指数退避，避免 next_renew_at 处于过去时间时产生 1s 紧循环
                    backoff = min(60.0 * (2 ** (consecutive_failures - 1)), 1800.0)
                    wait_seconds = max(wait_seconds, backoff)
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=wait_seconds)
                    return
                except TimeoutError:
                    pass
                try:
                    await self.renew_once()
                    consecutive_failures = 0
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    # 单次续期失败不应终止续期循环（否则失败后再也不会自动重试）；
                    # renew_once 已记录 session_expired/error 与 last_error。
                    # 若凭据已确定过期(session_expired)，自动续期无法挽救，需人工重新绑定 ->
                    # 停止自动重试，避免 renewing<->session_expired 状态抖动与日志/SSE 噪声；
                    # 仅对瞬时 error 做指数退避重试。
                    if self.instance.status == "session_expired":
                        logger.warning(
                            f"OpenILink 多实例会话已过期，停止自动续期，等待重新绑定: instance={self.instance_key}, error={e}",
                        )
                        return
                    consecutive_failures += 1
                    logger.warning(
                        f"OpenILink 多实例续期失败(第 {consecutive_failures} 次)，将退避后重试: "
                        f"instance={self.instance_key}, error={e}",
                    )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"OpenILink 多实例续期任务异常退出: instance={self.instance_key}, error={e}")

    async def _handle_message(self, message: OpenILinkMessage) -> None:
        if self._is_duplicate_message(message.message_id):
            logger.debug(f"重复 OpenILink 消息已过滤: instance={self.instance_key}, message_id={message.message_id}")
            return

        try:
            parsed = await self.processor.parse(await self._message_to_processor_payload(message))
        except Exception as e:
            logger.exception(f"OpenILink 消息解析失败，使用错误文本兜底: instance={self.instance_key}, message_id={message.message_id}")
            parsed = await self.processor.parse(
                self._message_to_fallback_payload(message, f"[OpenILink 消息解析失败: {e}]")
            )
        if parsed is None:
            await self._persist_message_cursor(message)
            return
        await collect_message(
            adapter=self.adapter,
            platform_channel=parsed.channel,
            platform_user=parsed.user,
            platform_message=parsed.message,
        )
        await self._persist_message_cursor(message)

    async def _handle_sync_state(self, sync_state: SyncState) -> None:
        self.session.sync_state_json = sync_state.model_dump_json()
        self.session.last_cursor = sync_state.cursor or ""
        await self.session.save()

    async def _handle_monitor_error(self, error: Exception) -> None:
        logger.warning(f"OpenILink 多实例监控回调错误: instance={self.instance_key}, error={error}")

    async def _mark_renew_failure(self, error: Exception) -> None:
        status = "session_expired" if self._credentials_expired() else "error"
        self.instance = await adapter_instance_service.set_status(
            self.instance,
            status,
            f"实例会话续期失败: {error}",
        )

    async def _stop_client_monitor(self) -> None:
        try:
            await self.client.stop_monitor()
        except NotImplementedError:
            logger.debug(f"OpenILink 多实例 stop_monitor 未实现: instance={self.instance_key}")
        except Exception as e:
            logger.warning(f"停止 OpenILink 多实例监控失败: instance={self.instance_key}, error={e}")

    def _load_credentials(self) -> OpenILinkCredentials:
        if not self.session.credentials_json:
            raise ValueError(f"实例 {self.instance_key} 缺少会话凭据")
        return OpenILinkCredentials.model_validate_json(self.session.credentials_json)

    def _credentials_expired(self) -> bool:
        try:
            expires_at = self._load_credentials().expires_at or self.session.expires_at
        except ValueError:
            expires_at = self.session.expires_at
        if expires_at is None:
            return False
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= datetime.now(timezone.utc)

    def _load_sync_state(self) -> SyncState:
        if not self.session.sync_state_json:
            return SyncState()
        return SyncState.model_validate_json(self.session.sync_state_json)

    def _seconds_until_next_renew(self) -> float:
        renew_at = self.instance.next_renew_at
        if renew_at is None:
            expires_at = self.session.expires_at
            if expires_at is None:
                return 3600.0
            renew_at = expires_at

        now = datetime.now(timezone.utc)
        if renew_at.tzinfo is None:
            renew_at = renew_at.replace(tzinfo=timezone.utc)
        return max((renew_at - now).total_seconds(), 1.0)

    async def _message_to_processor_payload(self, message: OpenILinkMessage) -> dict[str, object]:
        payload: dict[str, object] = {
            "message_id": message.message_id,
            "sender_id": message.sender_id,
            "timestamp": message.timestamp,
            "type": message.raw_type or ("text" if message.text else "file"),
            "content": message.text or "",
            "conversation_id": message.context_token.conversation_id,
            "sync_cursor": message.context_token.sync_cursor or "",
        }
        if message.recipient.kind == RecipientKind.GROUP:
            payload["group_id"] = message.recipient.id
        if message.media:
            first_media = message.media[0]
            payload["type"] = first_media.kind.value
            payload["file_name"] = first_media.file_name or first_media.media_id
            if first_media.size_bytes is not None and first_media.size_bytes > self.config.MEDIA_DOWNLOAD_MAX_BYTES:
                error = ValueError(f"媒体文件过大: {first_media.size_bytes} bytes")
                logger.warning(
                    f"OpenILink 媒体超过下载限制: instance={self.instance_key}, "
                    f"message_id={message.message_id}, media_id={first_media.media_id}, size={first_media.size_bytes}",
                )
                payload["type"] = "text"
                payload["content"] = self._media_download_failure_text(first_media, error)
                return payload
            if first_media.url:
                if first_media.kind.value == "image":
                    payload["image_url"] = first_media.url
                elif first_media.kind.value == "voice":
                    payload["voice_url"] = first_media.url
                else:
                    payload["file_url"] = first_media.url
            else:
                try:
                    media_bytes = await self._download_media_as_bytes(first_media)
                except Exception as e:
                    logger.exception(
                        f"OpenILink 媒体下载失败: instance={self.instance_key}, "
                        f"message_id={message.message_id}, media_id={first_media.media_id}",
                    )
                    payload["type"] = "text"
                    payload["content"] = self._media_download_failure_text(first_media, e)
                    return payload
                if first_media.kind == MediaKind.IMAGE:
                    payload["image_data"] = media_bytes
                elif first_media.kind == MediaKind.VOICE:
                    payload["voice_data"] = media_bytes
                else:
                    payload["file_data"] = media_bytes
        return payload

    async def _download_media_as_bytes(self, media: OpenILinkMedia) -> bytes:
        result = await self.download_media(media)
        if isinstance(result, bytes):
            return result
        async with aiofiles.open(result, "rb") as file:
            data = await file.read()
        if len(data) > self.config.MEDIA_DOWNLOAD_MAX_BYTES:
            raise ValueError(f"媒体文件过大: {len(data)} bytes")
        return data

    def _is_duplicate_message(self, remote_message_id: str) -> bool:
        now = time.time()
        ttl = max(self.config.DEDUP_WINDOW_SECONDS, 1)
        cutoff = now - ttl
        gc_interval = max(min(ttl // 4, 30), 5)
        if now - self._last_dedup_gc_ts >= gc_interval:
            self._recent_remote_message_ids = {
                key: ts for key, ts in self._recent_remote_message_ids.items() if ts >= cutoff
            }
            self._last_dedup_gc_ts = now

        dedup_key = (self.instance_key, remote_message_id)
        if dedup_key in self._recent_remote_message_ids:
            return True

        self._recent_remote_message_ids[dedup_key] = now
        if len(self._recent_remote_message_ids) > DEDUP_MAX_SIZE:
            overflow_count = len(self._recent_remote_message_ids) - DEDUP_MAX_SIZE
            oldest_keys = sorted(
                self._recent_remote_message_ids,
                key=self._recent_remote_message_ids.__getitem__,
            )[:overflow_count]
            for key in oldest_keys:
                self._recent_remote_message_ids.pop(key, None)
        return False

    async def _persist_message_cursor(self, message: OpenILinkMessage) -> None:
        sync_cursor = message.context_token.sync_cursor
        if sync_cursor:
            self.session.last_cursor = sync_cursor
        self.session.last_message_remote_id = message.message_id
        await self.session.save()
        # 记录实例最近活跃时间（轻量 update，避免重载整行）
        await DBAdapterInstance.filter(id=self.instance.id).update(last_active_at=datetime.now(timezone.utc))

    def _message_to_fallback_payload(self, message: OpenILinkMessage, text: str) -> dict[str, object]:
        payload: dict[str, object] = {
            "message_id": message.message_id,
            "sender_id": message.sender_id,
            "timestamp": message.timestamp,
            "type": "text",
            "content": text,
            "conversation_id": message.context_token.conversation_id,
            "sync_cursor": message.context_token.sync_cursor or "",
        }
        if message.recipient.kind == RecipientKind.GROUP:
            payload["group_id"] = message.recipient.id
        return payload

    def _media_download_failure_text(self, media: OpenILinkMedia, error: Exception) -> str:
        if media.kind == MediaKind.IMAGE:
            media_label = "图片"
        elif media.kind == MediaKind.VOICE:
            media_label = "语音"
        else:
            media_label = "文件"
        return f"[{media_label}下载失败: {error}]"

    def _build_context_token(self, recipient: OpenILinkRecipient, ref_msg_id: str | None) -> ContextToken:
        return ContextToken(
            conversation_id=recipient.id,
            message_id=ref_msg_id,
            sync_cursor=self.session.last_cursor or None,
        )
