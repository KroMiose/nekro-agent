import asyncio
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_adapter_instance import DBAdapterInstance
from nekro_agent.models.db_adapter_instance_session import DBAdapterInstanceSession
from nekro_agent.schemas.errors import ConflictError, NotFoundError, ValidationError
from nekro_agent.services.adapter_instance_service import adapter_instance_service

from .bot_connection import BotConnection, ClientFactory
from .client import OpenILinkMultiClient, UnsupportedOpenILinkMultiClient
from .config import WeChatILinkMultiConfig
from .schemas import BindPollResult, BindStartResult, BindStatus, SyncState

if TYPE_CHECKING:
    from .adapter import WeChatILinkMultiAdapter

logger = get_sub_logger("adapter.wechat_ilink_multi.manager")


class BotManager:
    """微信 OpenILink 多实例生命周期管理器。"""

    def __init__(
        self,
        *,
        adapter_key: str,
        config: WeChatILinkMultiConfig,
        adapter_getter: Callable[[], object],
        client_factory: ClientFactory | None = None,
    ):
        self.adapter_key = adapter_key
        self.config = config
        self._adapter_getter = adapter_getter
        self._client_factory = client_factory or UnsupportedOpenILinkMultiClient
        self._connections: dict[str, BotConnection] = {}
        self._bind_clients: dict[str, OpenILinkMultiClient] = {}

    @property
    def connections(self) -> dict[str, BotConnection]:
        return dict(self._connections)

    async def start(self) -> None:
        instances = await adapter_instance_service.list_instances(adapter_key=self.adapter_key)
        for instance in instances:
            if not self._should_autostart(instance):
                continue
            await self.start_instance(instance.instance_key, manual=False)

    async def stop_all(self) -> None:
        for instance_key in list(self._connections):
            await self.stop_instance(instance_key)

    def get_connection(self, instance_key: str) -> BotConnection | None:
        return self._connections.get(instance_key)

    async def start_bind(self, instance_key: str) -> BindStartResult:
        instance = await self._get_active_instance(instance_key)
        await self.stop_instance(instance_key, update_status=False)
        client = self._client_factory(self.config)
        try:
            # 绑定动作会发起真实网络调用（生成二维码等），加超时避免 API 请求无限挂起
            result = await asyncio.wait_for(client.start_bind(), timeout=self.config.BIND_TIMEOUT_SECONDS)
        except (TimeoutError, asyncio.TimeoutError) as e:
            raise ValidationError(reason=f"实例 {instance_key} 绑定二维码生成超时") from e
        self._bind_clients[instance_key] = client

        instance = await adapter_instance_service.set_status(
            instance,
            "binding",
            "绑定二维码已生成",
            payload={"bind_session_id": result.session_id, "expires_at": result.expires_at.isoformat()},
        )
        await self._set_bind_state(
            instance,
            "qr_generated",
            "绑定二维码已生成",
            payload={"bind_session_id": result.session_id, "qr_url": result.qr_url},
        )
        return result

    async def poll_bind(self, instance_key: str, session_id: str) -> BindPollResult:
        instance = await self._get_active_instance(instance_key)
        client = self._bind_clients.get(instance_key)
        if client is None:
            client = self._client_factory(self.config)
            self._bind_clients[instance_key] = client

        result = await client.poll_bind(session_id)
        if result.status == BindStatus.PENDING:
            await self._set_bind_state(instance, "qr_generated", "等待扫码确认")
            return result
        if result.status == BindStatus.SCANNED:
            await self._set_bind_state(instance, "qr_scanned", "二维码已扫描")
            return result
        if result.status == BindStatus.CONFIRMED:
            await self._complete_bind(instance, result)
            self._bind_clients.pop(instance_key, None)
            return result
        if result.status == BindStatus.EXPIRED:
            await self._set_bind_state(instance, "expired", "绑定会话已过期")
            await adapter_instance_service.set_status(instance, "session_expired", "绑定会话已过期")
            self._bind_clients.pop(instance_key, None)
            return result

        message = result.error_message or "绑定失败"
        await self._set_bind_state(instance, "failed", message)
        await adapter_instance_service.set_status(instance, "error", message)
        self._bind_clients.pop(instance_key, None)
        return result

    async def renew_instance(self, instance_key: str) -> DBAdapterInstance:
        connection = self._connections.get(instance_key)
        if connection is None:
            await self.start_instance(instance_key, manual=True)
            connection = self._connections.get(instance_key)
        if connection is None:
            raise ValidationError(reason=f"实例 {instance_key} 缺少有效会话，无法续期")
        await connection.renew_once()
        return connection.instance

    async def start_instance(self, instance_key: str, *, manual: bool = True) -> BotConnection | None:
        existing = self._connections.get(instance_key)
        if existing is not None and existing.is_online:
            return existing

        instance = await adapter_instance_service.get_instance(self.adapter_key, instance_key)
        if instance is None:
            logger.warning(f"OpenILink 多实例不存在，无法启动: instance={instance_key}")
            return None
        if instance.status == "deleted":
            logger.warning(f"OpenILink 多实例已删除，无法启动: instance={instance_key}")
            return None
        if not instance.enabled and not manual:
            return None

        session = await DBAdapterInstanceSession.get_or_none(instance_id=instance.id)
        if session is None or not session.credentials_json:
            if manual:
                await adapter_instance_service.set_status(instance, "session_expired", "实例缺少有效会话凭据")
            return None
        if self._is_session_expired(session) and not manual:
            await adapter_instance_service.set_status(instance, "session_expired", "实例会话已过期")
            return None

        await self.stop_instance(instance_key)
        adapter_obj = cast("WeChatILinkMultiAdapter", self._adapter_getter())

        connection = BotConnection(
            adapter=adapter_obj,
            instance=instance,
            session=session,
            config=self.config,
            client_factory=self._client_factory,
        )
        self._connections[instance_key] = connection
        # 不写入设计状态机之外的 "starting" 子状态；monitor 成功后由 BotConnection 落地 "online"，
        # 失败则落地 "error"，避免引入未文档化的中间态。
        await connection.start()
        return connection

    async def stop_instance(self, instance_key: str, *, update_status: bool = True) -> None:
        connection = self._connections.pop(instance_key, None)
        if connection is not None:
            await connection.stop()

        instance = await adapter_instance_service.get_instance(self.adapter_key, instance_key)
        if update_status and instance is not None and instance.status not in ("deleted", "session_expired"):
            await adapter_instance_service.set_status(instance, "offline", "实例已停止")

    async def restart_instance(self, instance_key: str) -> BotConnection | None:
        await self.stop_instance(instance_key)
        return await self.start_instance(instance_key, manual=True)

    def _should_autostart(self, instance: DBAdapterInstance) -> bool:
        return instance.enabled and instance.status not in ("deleted", "session_expired")

    def _is_session_expired(self, session: DBAdapterInstanceSession) -> bool:
        expires_at = session.expires_at
        if expires_at is None:
            return False
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= datetime.now(timezone.utc)

    async def _get_active_instance(self, instance_key: str) -> DBAdapterInstance:
        instance = await adapter_instance_service.get_instance(self.adapter_key, instance_key)
        if instance is None:
            raise NotFoundError(resource=f"OpenILink 实例 {instance_key}")
        if instance.status == "deleted":
            raise ValidationError(reason=f"实例 {instance_key} 已删除")
        return instance

    async def _complete_bind(self, instance: DBAdapterInstance, result: BindPollResult) -> None:
        if result.credentials is None:
            raise ValidationError(reason="绑定确认结果缺少会话凭据")
        provider_account_id = result.provider_account_id or result.credentials.provider_account_id
        await self._ensure_provider_account_available(instance, provider_account_id)

        await self._set_bind_state(instance, "login_confirmed", "绑定登录已确认")
        instance.provider_account_id = provider_account_id
        await instance.save()
        sync_state = SyncState()
        session = await adapter_instance_service.upsert_session(
            instance=instance,
            credentials_json=result.credentials.model_dump_json(),
            sync_state_json=sync_state.model_dump_json(),
            expires_at=result.credentials.expires_at,
            last_cursor="",
        )
        if result.credentials.expires_at is not None:
            instance = await adapter_instance_service.schedule_renew(
                instance=instance,
                expires_at=result.credentials.expires_at,
                renew_before_minutes=instance.renew_before_minutes or self.config.DEFAULT_RENEW_BEFORE_MINUTES,
            )
        await self._set_bind_state(instance, "session_persisted", "绑定会话已持久化")

        await self.stop_instance(instance.instance_key, update_status=False)
        adapter_obj = cast("WeChatILinkMultiAdapter", self._adapter_getter())
        connection = BotConnection(
            adapter=adapter_obj,
            instance=instance,
            session=session,
            config=self.config,
            client_factory=self._client_factory,
        )
        self._connections[instance.instance_key] = connection
        await connection.start()
        try:
            await connection.wait_until_online(timeout_seconds=30.0)
        except (RuntimeError, TimeoutError):
            self._connections.pop(instance.instance_key, None)
            await connection.stop()
            raise

    async def _ensure_provider_account_available(self, instance: DBAdapterInstance, provider_account_id: str) -> None:
        if not provider_account_id:
            raise ValidationError(reason="绑定确认结果缺少 provider_account_id")
        conflict = await DBAdapterInstance.filter(
            adapter_key=self.adapter_key,
            provider_account_id=provider_account_id,
        ).exclude(instance_key=instance.instance_key).exclude(status="deleted").first()
        if conflict is not None:
            raise ConflictError(resource=f"OpenILink 账号 {provider_account_id}")

    async def _set_bind_state(
        self,
        instance: DBAdapterInstance,
        bind_status: str,
        message: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        previous_session = await DBAdapterInstanceSession.get_or_none(instance_id=instance.id)
        previous_state = previous_session.session_state if previous_session is not None else ""
        await adapter_instance_service.set_session_state(instance, bind_status, payload=payload)
        if previous_state == bind_status:
            return
        await adapter_instance_service.record_event(
            instance=instance,
            event_type="bind_state_change",
            status_from=previous_state,
            status_to=bind_status,
            message=message,
            payload_json=json.dumps(payload, ensure_ascii=False) if payload else "",
        )
