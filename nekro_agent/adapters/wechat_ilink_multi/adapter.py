from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import ChatType

from .bot_connection import BotConnection
from .bot_manager import BotManager
from .client import OpenILinkMultiClient
from .config import WeChatILinkMultiConfig
from .schemas import BindPollResult, BindStartResult, OpenILinkRecipient, RecipientKind
from .sdk_client import WeChatBotSDKOpenILinkMultiClient

logger = get_sub_logger("adapter.wechat_ilink_multi")


class WeChatILinkMultiAdapter(BaseAdapter[WeChatILinkMultiConfig]):
    """微信 OpenILink 多实例适配器。"""

    def __init__(self, config_cls: type[WeChatILinkMultiConfig] = WeChatILinkMultiConfig):
        super().__init__(config_cls)
        self.bot_manager = BotManager(
            adapter_key=self.key,
            config=self.config,
            adapter_getter=lambda: self,
            client_factory=self._create_client,
        )

    @property
    def key(self) -> str:
        return "wechat_ilink_multi"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="WeChat iLink Multi",
            description="基于 OpenILink 的微信多账号实例适配器",
            version="0.1.0",
            author="NekroAI",
            tags=["wechat", "openilink", "multi-instance"],
        )

    @property
    def chat_key_rules(self) -> list[str]:
        return [
            "群聊: `wxim-{instance_key}:group:{group_id}`",
            "私聊: `wxim-{instance_key}:private:{user_id}`",
        ]

    def build_chat_key(self, channel_id: str) -> str:
        """构建聊天标识，使用短前缀避免超过 64 字符限制。"""
        return f"wxim-{channel_id}"

    def parse_chat_key(self, chat_key: str) -> tuple[str, str]:
        """解析聊天标识，适配短前缀。"""
        if chat_key.startswith("wxim-"):
            return self.key, chat_key[5:]
        # Fallback to base implementation for legacy keys
        parts = chat_key.split("-", 1)
        if len(parts) != 2:
            raise ValueError(f"无效的聊天标识: {chat_key}")
        return parts[0], parts[1]

    @property
    def supports_webui_send(self) -> bool:
        return True

    def get_adapter_router(self) -> APIRouter:
        from .routers import create_router

        return create_router()

    async def init(self) -> None:
        await self.bot_manager.start()
        logger.info("WeChat iLink Multi 适配器已启动")

    async def cleanup(self) -> None:
        await self.bot_manager.stop_all()
        logger.info("WeChat iLink Multi 适配器已关闭")

    async def start_bind(self, instance_key: str) -> BindStartResult:
        return await self.bot_manager.start_bind(instance_key)

    async def poll_bind(self, instance_key: str, session_id: str) -> BindPollResult:
        return await self.bot_manager.poll_bind(instance_key, session_id)

    async def renew_instance(self, instance_key: str) -> None:
        await self.bot_manager.renew_instance(instance_key)

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        try:
            adapter_key, channel_id = self.parse_chat_key(request.chat_key)
            if adapter_key != self.key:
                raise ValueError(f"聊天标识适配器不匹配: {adapter_key}")
            scoped_channel = self._parse_scoped_channel_id(channel_id)
        except ValueError as e:
            return PlatformSendResponse(success=False, error_message=str(e))

        connection = self.bot_manager.get_connection(scoped_channel.instance_key)
        if connection is None or not connection.is_online:
            return PlatformSendResponse(
                success=False,
                error_message=f"实例离线或不存在: {scoped_channel.instance_key}",
            )

        recipient = OpenILinkRecipient(
            kind=RecipientKind.GROUP if scoped_channel.chat_type == ChatType.GROUP else RecipientKind.USER,
            id=scoped_channel.target_id,
        )
        message_ids: list[str] = []
        failed_segments: list[str] = []
        text_parts: list[str] = []

        for segment in request.segments:
            if segment.type == PlatformSendSegmentType.TEXT:
                if segment.content:
                    text_parts.append(segment.content)
                continue
            if segment.type == PlatformSendSegmentType.AT:
                if segment.at_info is not None:
                    text_parts.append(f"@{segment.at_info.nickname or segment.at_info.platform_user_id}")
                elif segment.content:
                    text_parts.append(f"@{segment.content}")
                continue

            await self._flush_text(connection, recipient, request.ref_msg_id, text_parts, message_ids, failed_segments)
            if segment.type in (PlatformSendSegmentType.IMAGE, PlatformSendSegmentType.FILE):
                if not segment.file_path:
                    failed_segments.append(f"{segment.type.value}:file_path 为空")
                    continue
                try:
                    message_id = await connection.send_file(
                        recipient=recipient,
                        file_path=Path(segment.file_path),
                        ref_msg_id=request.ref_msg_id,
                    )
                    message_ids.append(message_id)
                except Exception as e:
                    # 宽捕获：发送文件可能因网络/文件IO/协议等不可预见的异常失败，
                    # 需要在收集段错误的循环中容错，避免单段发送失败中断后续段发送
                    failed_segments.append(f"{segment.type.value}:{e}")
                continue

            failed_segments.append(f"{segment.type.value}:暂不支持")

        await self._flush_text(connection, recipient, request.ref_msg_id, text_parts, message_ids, failed_segments)

        if message_ids:
            error_message = f"部分消息发送失败: {'; '.join(failed_segments)}" if failed_segments else None
            return PlatformSendResponse(success=True, message_id=",".join(message_ids), error_message=error_message)
        if failed_segments:
            return PlatformSendResponse(success=False, error_message="; ".join(failed_segments))
        return PlatformSendResponse(success=True, message_id="")

    async def get_self_info(self) -> PlatformUser:
        online_keys = [key for key, connection in self.bot_manager.connections.items() if connection.is_online]
        if not online_keys:
            return PlatformUser(platform_name=self.key, user_id="", user_name="WeChat iLink Multi (unavailable)")
        first_key = online_keys[0]
        return PlatformUser(
            platform_name=self.key,
            user_id=first_key,
            user_name=f"WeChat iLink Multi ({len(online_keys)} online)",
        )

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        self._parse_scoped_channel_id(channel_id)
        return PlatformUser(
            platform_name=self.key,
            user_id=user_id,
            user_name=user_id,
            user_avatar="",
        )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        scoped_channel = self._parse_scoped_channel_id(channel_id)
        return PlatformChannel(
            channel_id=channel_id,
            channel_name=f"{scoped_channel.instance_key}:{scoped_channel.target_id}",
            channel_type=scoped_channel.chat_type,
            channel_avatar="",
        )

    async def _flush_text(
        self,
        connection: BotConnection,
        recipient: OpenILinkRecipient,
        ref_msg_id: str | None,
        text_parts: list[str],
        message_ids: list[str],
        failed_segments: list[str],
    ) -> None:
        text = "".join(text_parts).strip()
        text_parts.clear()
        if not text:
            return
        try:
            message_id = await connection.send_text(recipient=recipient, text=text, ref_msg_id=ref_msg_id)
            message_ids.append(message_id)
        except Exception as e:
            # 宽捕获：发送文本可能因网络/协议等不可预见的异常失败，
            # 需要在收集段错误的循环中容错，避免单段发送失败中断流程
            failed_segments.append(f"text:{e}")

    def _create_client(self, config: WeChatILinkMultiConfig) -> OpenILinkMultiClient:
        return WeChatBotSDKOpenILinkMultiClient(config)

    def _parse_scoped_channel_id(self, channel_id: str) -> "ScopedChannelId":
        parts = channel_id.split(":", 2)
        if len(parts) != 3:
            raise ValueError(f"无效的频道标识: {channel_id}")
        instance_key, channel_type, target_id = parts
        if not instance_key or not target_id:
            raise ValueError(f"无效的频道标识: {channel_id}")
        if channel_type == "private":
            chat_type = ChatType.PRIVATE
        elif channel_type == "group":
            chat_type = ChatType.GROUP
        else:
            raise ValueError(f"不支持的频道类型: {channel_type}")
        return ScopedChannelId(instance_key=instance_key, chat_type=chat_type, target_id=target_id)


@dataclass(slots=True)
class ScopedChannelId:
    instance_key: str
    chat_type: ChatType
    target_id: str
