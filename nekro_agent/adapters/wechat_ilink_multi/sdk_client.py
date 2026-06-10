import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiohttp

from nekro_agent.core.os_env import OsEnv

from .client import MediaDownloadResult, OpenILinkMonitorCallbacks, OpenILinkMultiClient
from .config import WeChatILinkMultiConfig
from .schemas import (
    BindPollResult,
    BindStartResult,
    BindStatus,
    ContextToken,
    MediaKind,
    OpenILinkCredentials,
    OpenILinkMedia,
    OpenILinkMessage,
    OpenILinkRecipient,
    RecipientKind,
    RenewResult,
    SendMessageResult,
    SyncState,
)


class WeChatBotSDKOpenILinkMultiClient(OpenILinkMultiClient):
    """基于 wechatbot-sdk 的 OpenILink 多实例传输实现。"""

    def __init__(self, config: WeChatILinkMultiConfig):
        super().__init__(config)
        self._bot: Any | None = None
        self._login_task: asyncio.Task[Any] | None = None
        self._monitor_task: asyncio.Task[None] | None = None
        self._bind_status = BindStatus.PENDING
        self._bind_session_id = ""
        self._bind_qr_url = ""
        self._bind_error = ""
        self._bind_credentials: OpenILinkCredentials | None = None
        self._bind_cred_path: Path | None = None
        self._media_messages: dict[str, Any] = {}

    async def start_bind(self) -> BindStartResult:
        self._bind_session_id = f"wechatbot-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        self._bind_status = BindStatus.PENDING
        self._bind_error = ""
        self._bind_credentials = None
        self._bind_qr_url = ""
        self._bind_cred_path = self._credential_path(self._bind_session_id)
        self._bot = self._create_bot(self._bind_cred_path)
        self._login_task = asyncio.create_task(self._login_for_bind(), name=f"wechat-ilink-bind-{self._bind_session_id}")

        deadline = asyncio.get_running_loop().time() + 20.0
        while not self._bind_qr_url and not self._bind_error:
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError("等待 OpenILink 二维码生成超时")
            await asyncio.sleep(0.2)

        if self._bind_error:
            raise RuntimeError(self._bind_error)
        return BindStartResult(
            session_id=self._bind_session_id,
            qr_url=self._bind_qr_url,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.config.BIND_TIMEOUT_SECONDS),
        )

    async def poll_bind(self, session_id: str) -> BindPollResult:
        if session_id != self._bind_session_id:
            return BindPollResult(status=BindStatus.FAILED, error_message="绑定会话不存在或已失效")

        if self._login_task is not None and self._login_task.done() and self._bind_credentials is None and not self._bind_error:
            try:
                await self._login_task
            except Exception as exc:  # 登录任务错误需要转为绑定失败状态返回给 API 调用方
                self._bind_error = str(exc)
                self._bind_status = BindStatus.FAILED

        return BindPollResult(
            status=self._bind_status,
            credentials=self._bind_credentials,
            provider_account_id=self._bind_credentials.provider_account_id if self._bind_credentials else None,
            error_message=self._bind_error or None,
        )

    async def start_monitor(
        self,
        credentials: OpenILinkCredentials,
        sync_state: SyncState,
        callbacks: OpenILinkMonitorCallbacks,
    ) -> None:
        from nekro_agent.core.logger import get_sub_logger

        sdk_logger = get_sub_logger("adapter.wechat_ilink_multi.sdk")
        cred_path = self._credential_path(credentials.provider_account_id)
        self._write_credentials_file(credentials, cred_path)
        self._bot = self._create_bot(cred_path)
        self._hook_wechatbot_logger(type(self._bot))
        await self._bot.login(force=False)
        sdk_logger.info(f"[wechatbot-sdk] OpenILink monitor login success: {credentials.provider_account_id}")

        @self._bot.on_message
        async def _handler(message: Any) -> None:
            converted = self._convert_message(message)
            await callbacks.on_message(converted)
            if callbacks.on_sync_state is not None:
                await callbacks.on_sync_state(
                    SyncState(cursor=converted.context_token.sync_cursor, last_sync_at=datetime.now(timezone.utc))
                )

        self._monitor_task = asyncio.create_task(self._bot.start(), name=f"wechat-ilink-sdk-monitor-{credentials.provider_account_id}")
        sdk_logger.info("[wechatbot-sdk] OpenILink monitor task created")
        # Wait briefly to confirm the task didn't immediately fail
        await asyncio.sleep(0.5)
        if self._monitor_task.done():
            exc = self._monitor_task.exception()
            if exc is not None:
                raise exc
        sdk_logger.info("[wechatbot-sdk] OpenILink monitor task running")

    async def stop_monitor(self) -> None:
        if self._bot is not None:
            stop = getattr(self._bot, "stop", None)
            if callable(stop):
                stop()
        if self._monitor_task is not None and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self._monitor_task = None

    def _hook_wechatbot_logger(self, bot_cls: Any) -> None:
        from nekro_agent.core.logger import get_sub_logger

        sdk_logger = get_sub_logger("adapter.wechat_ilink_multi.sdk")
        if getattr(bot_cls, "_nekro_log_hooked", False):
            return
        original_log = getattr(bot_cls, "_log", None)
        if not callable(original_log):
            return

        def _nekro_log(instance: Any, msg: str) -> None:  # noqa: ARG001
            sdk_logger.info(f"[wechatbot-sdk] {msg}")

        setattr(bot_cls, "_log", _nekro_log)
        setattr(bot_cls, "_nekro_log_hooked", True)

    async def send_text(
        self,
        recipient: OpenILinkRecipient,
        text: str,
        context_token: ContextToken,
    ) -> SendMessageResult:
        if self._bot is None:
            raise RuntimeError("OpenILink client monitor is not started")
        await self._bot.send(recipient.id, text)
        return SendMessageResult(message_id=f"local-{int(datetime.now(timezone.utc).timestamp() * 1000)}")

    async def send_file(
        self,
        recipient: OpenILinkRecipient,
        file_path: Path,
        context_token: ContextToken,
    ) -> SendMessageResult:
        if self._bot is None:
            raise RuntimeError("OpenILink client monitor is not started")
        data = await asyncio.to_thread(file_path.read_bytes)
        await self._bot.send_media(recipient.id, {"file": data, "file_name": file_path.name or "file.bin"})
        return SendMessageResult(message_id=f"local-{int(datetime.now(timezone.utc).timestamp() * 1000)}")

    async def download_media(self, media: OpenILinkMedia) -> MediaDownloadResult:
        if media.url:
            timeout = aiohttp.ClientTimeout(total=self.config.MEDIA_DOWNLOAD_TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(media.url) as resp:
                    resp.raise_for_status()
                    return await resp.read()
        if self._bot is None:
            raise RuntimeError("OpenILink client monitor is not started")
        message = self._media_messages.get(media.media_id)
        if message is None:
            raise RuntimeError(f"媒体上下文不存在: {media.media_id}")
        downloaded = await self._bot.download(message)
        if downloaded is None:
            raise RuntimeError(f"媒体下载结果为空: {media.media_id}")
        return bytes(downloaded.data)

    async def renew_session(
        self,
        credentials: OpenILinkCredentials,
        sync_state: SyncState,
    ) -> RenewResult:
        return RenewResult(credentials=credentials, sync_state=sync_state, renew_at=None)

    async def _login_for_bind(self) -> None:
        if self._bot is None:
            raise RuntimeError("OpenILink bind client is not initialized")
        try:
            raw_credentials = await self._bot.login(force=True)
        except Exception as exc:
            self._bind_error = str(exc)
            self._bind_status = BindStatus.FAILED
            raise
        # iLink bot_token 无 TTL：SDK 的 Credentials 不含过期字段，token 也无刷新机制；
        # 失效仅由服务器在 API 返回 errcode==-14 时反应式暴露，并由 WeChatBot.start() 长连接
        # 自动重新登录。此处不再伪造 24h 过期，置 None 表示“无已知过期”——使续期调度休眠、
        # 重启不再把仍有效的会话误判为 session_expired。真到期需重新扫码绑定。
        self._bind_credentials = OpenILinkCredentials(
            provider_account_id=str(raw_credentials.account_id),
            access_token=str(raw_credentials.token),
            refresh_token=None,
            expires_at=None,
            device_id=str(raw_credentials.user_id),
            scope=[],
        )
        if self._bind_cred_path is not None:
            final_path = self._credential_path(self._bind_credentials.provider_account_id)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            self._bind_cred_path.replace(final_path)
        self._bind_status = BindStatus.CONFIRMED

    def _create_bot(self, cred_path: Path) -> Any:
        try:
            from wechatbot import WeChatBot
        except Exception as exc:
            raise RuntimeError("未安装 wechatbot-sdk，请先执行 uv run poe sync-dev") from exc

        return WeChatBot(
            base_url=self.config.API_BASE_URL,
            cred_path=str(cred_path),
            on_qr_url=self._on_qr_url,
            on_scanned=self._on_scanned,
            on_expired=self._on_expired,
            on_error=self._on_error,
        )

    def _on_qr_url(self, url: str) -> None:
        self._bind_qr_url = url
        self._bind_status = BindStatus.PENDING

    def _on_scanned(self) -> None:
        self._bind_status = BindStatus.SCANNED

    def _on_expired(self) -> None:
        self._bind_status = BindStatus.EXPIRED

    def _on_error(self, error: Exception) -> None:
        self._bind_error = str(error)
        self._bind_status = BindStatus.FAILED

    def _credential_path(self, key: str) -> Path:
        safe_key = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in key)
        return Path(OsEnv.DATA_DIR) / "configs" / "wechat_ilink_multi" / "credentials" / f"{safe_key}.json"

    def _write_credentials_file(self, credentials: OpenILinkCredentials, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        payload = {
            "token": credentials.access_token,
            "baseUrl": self.config.API_BASE_URL,
            "accountId": credentials.provider_account_id,
            "userId": credentials.device_id or credentials.provider_account_id,
            "savedAt": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        path.chmod(0o600)

    def _convert_message(self, message: Any) -> OpenILinkMessage:
        raw = getattr(message, "raw", None)
        raw_dict = raw if isinstance(raw, dict) else {}
        message_id = self._first_non_empty(message, raw_dict, ("message_id", "msg_id", "id"))
        if not message_id:
            message_id = f"msg-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        sender_id = str(getattr(message, "user_id", "") or raw_dict.get("from_user_id") or raw_dict.get("user_id") or "")
        timestamp = getattr(message, "timestamp", None)
        if not isinstance(timestamp, datetime):
            timestamp = datetime.now(timezone.utc)
        context_token = str(getattr(message, "_context_token", "") or raw_dict.get("context_token") or "")
        media = self._extract_media(message_id, message)
        return OpenILinkMessage(
            message_id=message_id,
            sender_id=sender_id,
            recipient=OpenILinkRecipient(kind=RecipientKind.USER, id=sender_id),
            timestamp=timestamp,
            text=str(getattr(message, "text", "") or "") or None,
            media=media,
            context_token=ContextToken(conversation_id=sender_id, message_id=message_id, sync_cursor=context_token),
            raw_type=str(getattr(message, "type", "") or "") or None,
            raw=raw_dict,
        )

    def _extract_media(self, message_id: str, message: Any) -> list[OpenILinkMedia]:
        media_items: list[OpenILinkMedia] = []
        for attr, kind, default_name in (
            ("images", MediaKind.IMAGE, "image.jpg"),
            ("files", MediaKind.FILE, "file.bin"),
            ("voices", MediaKind.VOICE, "voice.silk"),
        ):
            values = getattr(message, attr, None) or []
            if not values:
                continue
            item = values[0]
            media_id = f"{message_id}:{kind.value}"
            self._media_messages[media_id] = message
            file_name = str(getattr(item, "file_name", "") or default_name)
            size = getattr(item, "size", None)
            # 不暴露 url：iLink CDN 媒体（图片/文件/语音）是 AES 加密内容，CDNMedia.full_url 指向的是密文，
            # 裸 HTTP 下载得到的是加密字节（图片会被识别为 application/octet-stream 而被 LLM 拒收）。
            # 置 url=None 可强制走 download_media -> WeChatBot.download() 的下载+AES 解密路径（按 media_id
            # 从 self._media_messages 取回原始 IncomingMessage 后由 SDK 解密），得到有效文件字节。
            media_items.append(OpenILinkMedia(media_id=media_id, kind=kind, url=None, file_name=file_name, size_bytes=size))
            break
        return media_items

    def _first_non_empty(self, message: Any, raw: dict[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = str(getattr(message, key, "") or raw.get(key) or "").strip()
            if value:
                return value
        return ""
