from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import ChatType

from .client import QQBotOpenClawClient
from .config import QQBotOpenClawConfig
from .group_policy import GroupPolicyResolver
from .message_processor import QQBotOpenClawMessageProcessor
from .outbound import QQBotOpenClawOutbound, RecentInbound
from .ref_index_store import RefIndexStore
from .routers import create_router

logger = get_sub_logger("adapter.qqbot_openclaw")


class QQBotOpenClawAdapter(BaseAdapter[QQBotOpenClawConfig]):
    def __init__(self, config_cls: type[QQBotOpenClawConfig] = QQBotOpenClawConfig) -> None:
        super().__init__(config_cls)
        self.ref_store = RefIndexStore()
        self.group_policy = GroupPolicyResolver(self.config, self.config.APP_ID)
        self.processor = QQBotOpenClawMessageProcessor(
            config=self.config,
            adapter_key=self.key,
            ref_store=self.ref_store,
            group_policy=self.group_policy,
            self_user_id=self.config.APP_ID,
        )
        self.client: QQBotOpenClawClient | None = None
        self.outbound: QQBotOpenClawOutbound | None = None
        self._recent_inbound: dict[str, RecentInbound] = {}

    @property
    def key(self) -> str:
        return "qqbot_openclaw"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="QQBot OpenClaw",
            description="基于 OpenClaw QQBot 渠道行为实现的 QQ 私聊与群聊适配器",
            version="0.1.0",
            author="NekroAI",
            tags=["qq", "openclaw", "qqbot", "official-channel"],
        )

    @property
    def chat_key_rules(self) -> list[str]:
        return [
            "私聊: `qqoc-c2c:{user_openid}`",
            "群聊: `qqoc-group:{group_openid}`",
        ]

    @property
    def supports_webui_send(self) -> bool:
        return self.config.PROACTIVE_SEND_ENABLED

    def get_default_channel_status(self, channel_type: ChatType) -> str:
        if channel_type == ChatType.PRIVATE:
            return "active"
        if channel_type == ChatType.GROUP:
            return "disabled" if self.config.GROUP_POLICY == "disabled" else "active"
        return "active"

    def build_chat_key(self, channel_id: str) -> str:
        return f"qqoc-{channel_id}"

    def parse_chat_key(self, chat_key: str) -> tuple[str, str]:
        if not chat_key.startswith("qqoc-"):
            raise ValueError(f"无效的 OpenClaw QQBot chat_key: {chat_key}")
        return self.key, chat_key.removeprefix("qqoc-")

    async def init(self) -> None:
        await self.ref_store.load()
        if not self.config.APP_ID or not self.config.CLIENT_SECRET:
            logger.warning("QQBot OpenClaw APP_ID/CLIENT_SECRET 未配置，跳过 Gateway 初始化")
            return
        self.client = QQBotOpenClawClient(self.config, self._handle_event)
        self.outbound = QQBotOpenClawOutbound(
            config=self.config,
            client=self.client,
            ref_store=self.ref_store,
            recent_inbound=self._recent_inbound,
        )
        await self.client.start()
        logger.info("QQBot OpenClaw 适配器已启动 Gateway 后台连接")

    async def cleanup(self) -> None:
        if self.client:
            await self.client.stop()
            self.client = None
            self.outbound = None
        logger.info("QQBot OpenClaw 适配器已清理")

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        if not self.outbound:
            return PlatformSendResponse(success=False, error_message="QQBot OpenClaw 适配器未初始化或未配置凭据")
        return await self.outbound.send(request)

    async def get_self_info(self) -> PlatformUser:
        user_id = self.client.self_user_id if self.client and self.client.self_user_id else self.config.APP_ID
        return PlatformUser(platform_name=self.key, user_id=user_id, user_name=f"QQBot {user_id}")

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        return PlatformUser(platform_name=self.key, user_id=user_id, user_name=user_id)

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        if channel_id.startswith("c2c:"):
            return PlatformChannel(channel_id=channel_id, channel_name=f"QQ 私聊 {channel_id[4:]}", channel_type=ChatType.PRIVATE)
        if channel_id.startswith("group:"):
            return PlatformChannel(channel_id=channel_id, channel_name=f"QQ群 {channel_id[6:]}", channel_type=ChatType.GROUP)
        return PlatformChannel(channel_id=channel_id, channel_name=channel_id, channel_type=ChatType.UNKNOWN)

    async def render_runtime_prompt(self) -> str:
        return (
            "当前 QQ 渠道为 qqbot_openclaw，身份 ID 均为 OpenClaw/QQBot openid，"
            "不是传统 QQ 号。群普通消息默认只作为上下文，@ 机器人或引用机器人消息才会触发回复。"
        )

    def get_adapter_router(self) -> APIRouter:
        return create_router(
            get_status=self._maintenance_status,
            restart_gateway=self._restart_gateway,
            clear_ref_index=self._clear_ref_index,
            clear_session=self._clear_session,
            test_token=self._test_token,
        )

    async def _handle_event(self, event_type: str, raw: dict[str, Any]) -> None:
        try:
            if self.client and self.client.self_user_id:
                self.processor.set_self_user_id(self.client.self_user_id)
            parsed = await self.processor.parse_event(event_type, raw)
            if not parsed:
                return
            chat_key = self.build_chat_key(parsed.channel.channel_id)
            self._recent_inbound[chat_key] = RecentInbound(
                message_id=parsed.reply_msg_id or parsed.message.message_id,
                msg_idx=parsed.msg_idx,
                timestamp=time.time(),
            )
            logger.info(
                "OpenClaw QQBot 消息已投递: "
                f"type={event_type}, chat_key={chat_key}, sender={parsed.message.sender_id}, "
                f"is_tome={parsed.message.is_tome}, msg_idx={parsed.msg_idx}",
            )
            await collect_message(self, parsed.channel, parsed.user, parsed.message)
        except Exception:
            logger.exception(f"OpenClaw QQBot 消息处理失败: type={event_type}, raw_keys={list(raw.keys())}")

    async def _maintenance_status(self) -> dict[str, Any]:
        ref_stats = await self.ref_store.stats()
        return {
            "configured": bool(self.config.APP_ID and self.config.CLIENT_SECRET),
            "running": bool(self.client and self.client.running),
            "connected": bool(self.client and self.client.last_connected_at and not self.client.last_error),
            "app_id": self.config.APP_ID,
            "session_id": self.client.session_id if self.client else None,
            "last_seq": self.client.last_seq if self.client else None,
            "self_user_id": self.client.self_user_id if self.client else None,
            "last_connected_at": self.client.last_connected_at if self.client else None,
            "last_error": self.client.last_error if self.client else None,
            "ref_index_entries": ref_stats["entries"],
            "onboarding_url": "https://q.qq.com/qqbot/openclaw/index.html",
            "onboarding_qr_url": "https://q.qq.com/qqbot/openclaw/index.html",
        }

    async def _restart_gateway(self) -> dict[str, Any]:
        if not self.config.APP_ID or not self.config.CLIENT_SECRET:
            return {"success": False, "message": "APP_ID/CLIENT_SECRET 未配置"}
        if self.client:
            await self.client.stop()
        self.client = QQBotOpenClawClient(self.config, self._handle_event)
        self.outbound = QQBotOpenClawOutbound(
            config=self.config,
            client=self.client,
            ref_store=self.ref_store,
            recent_inbound=self._recent_inbound,
        )
        await self.client.start()
        return {"success": True, "message": "OpenClaw QQBot Gateway 已重新启动"}

    async def _clear_ref_index(self) -> dict[str, Any]:
        count = await self.ref_store.clear()
        return {"success": True, "message": f"已清理 {count} 条 ref index", "detail": {"count": count}}

    async def _clear_session(self) -> dict[str, Any]:
        if self.client:
            await self.client.clear_session()
        self._recent_inbound.clear()
        return {"success": True, "message": "已清理 Gateway session 与最近入站上下文"}

    async def _test_token(self) -> dict[str, Any]:
        if not self.client:
            client = QQBotOpenClawClient(self.config, self._handle_event)
            try:
                ok = await client.test_token()
            finally:
                await client.stop()
        else:
            ok = await self.client.test_token()
        return {"success": ok, "message": "AccessToken 获取成功" if ok else "AccessToken 获取失败"}
