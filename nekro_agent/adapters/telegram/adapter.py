"""
Telegram 适配器实现
"""

from typing import List, Optional, Type, Tuple
import asyncio

from fastapi import APIRouter

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core.logger import logger
from nekro_agent.schemas.chat_message import ChatType

from .client import TelegramClient
from .bot_api import TelegramBotAPIClient
from .config import TelegramConfig
from .tools import parse_at_from_text, build_mention_html


class TelegramAdapter(BaseAdapter[TelegramConfig]):
    """Telegram 适配器，支持 MTProto 和 Bot API 两种模式"""

    def __init__(self, config_cls: Type[TelegramConfig] = TelegramConfig):
        super().__init__(config_cls)
        self._task: Optional[asyncio.Task] = None
        if self.config.USE_BOT_API:
            self.client = TelegramBotAPIClient(token=self.config.BOT_TOKEN, proxy_url=self.config.PROXY_URL or "")
        else:
            self.client = TelegramClient(self)

    async def init(self) -> None:
        """初始化适配器"""
        if self.client:
            if isinstance(self.client, TelegramBotAPIClient):
                async def on_message(platform_channel, platform_user, platform_message):
                    from nekro_agent.adapters.interface.collector import collect_message
                    await collect_message(self, platform_channel, platform_user, platform_message)
                # 在后台启动，避免阻塞应用启动流程
                self._task = asyncio.create_task(self.client.start(on_message))
                logger.info("Telegram Bot API client started in background")
            else:
                # 在后台启动 MTProto 客户端
                self._task = asyncio.create_task(self.client.start())
                logger.info("Telegram MTProto client started in background")

    async def cleanup(self) -> None:
        """清理适配器"""
        if self.client:
            if hasattr(self.client, "stop"):
                try:
                    await self.client.stop()
                except Exception as e:
                    logger.warning(f"Telegram client stop warning: {e}")
        # 取消后台任务
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    @property
    def key(self) -> str:
        """适配器唯一标识"""
        return "telegram"

    @property
    def metadata(self) -> AdapterMetadata:
        """适配器元数据"""
        return AdapterMetadata(
            name="Telegram",
            description="连接到 Telegram 平台的适配器，允许通过 Bot 与频道和用户进行交互。",
            version="1.0.0",
            author="johntime",
            homepage="https://github.com/KroMiose/nekro-agent",
            tags=["telegram", "chat", "im"],
        )

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """转发消息到 Telegram 平台"""
        if self.client is None:
            error_msg = "Telegram client is not initialized. Check BOT_TOKEN configuration."
            logger.warning(error_msg)
            return PlatformSendResponse(success=False, error_message=error_msg)

        try:
            # 解析聊天键获取频道ID（OneBot 风格：group_123 / private_123）
            _, channel_id = self.parse_chat_key(request.chat_key)
            chat_id = channel_id.split("_", 1)[1] if "_" in channel_id else channel_id

            content_parts: List[str] = []
            # 收集文件段，保留类型信息，形如: [(path, 'image'|'file')]
            files_to_send: List[Tuple[str, str]] = []

            # 处理消息段
            use_html = False
            for seg in request.segments:
                if seg.type == PlatformSendSegmentType.TEXT:
                    # 处理文本内容和@信息
                    parsed_segments = parse_at_from_text(seg.content)
                    for parsed_seg in parsed_segments:
                        if isinstance(parsed_seg, str):
                            content_parts.append(parsed_seg)
                        else:
                            # 这是一个@对象
                            content_parts.append(build_mention_html(parsed_seg.platform_user_id, parsed_seg.nickname))
                            use_html = True
                elif seg.type == PlatformSendSegmentType.AT:
                    if seg.at_info:
                        content_parts.append(build_mention_html(seg.at_info.platform_user_id, seg.at_info.nickname))
                        use_html = True
                elif seg.type in [PlatformSendSegmentType.IMAGE, PlatformSendSegmentType.FILE]:
                    if seg.file_path:
                        files_to_send.append((seg.file_path, 'image' if seg.type == PlatformSendSegmentType.IMAGE else 'file'))

            final_content = "".join(content_parts)

            # 如果消息为空，跳过发送
            if not final_content.strip() and not files_to_send:
                logger.info("Empty message, skipping send.")
                return PlatformSendResponse(success=True)

            # 发送消息
            message_id: Optional[str] = None
            if isinstance(self.client, TelegramBotAPIClient):
                success, message_id = await self.client.send_message(
                    chat_id=chat_id,
                    text=final_content,
                    files=files_to_send,
                    reply_to=request.ref_msg_id,
                )
            elif hasattr(self.client, "send_message"):
                success = await self.client.send_message(
                    chat_id=chat_id,
                    text=final_content,
                    files=[p for p, _t in files_to_send]
                )
            else:
                logger.error("Telegram 客户端不支持 send_message 方法")
                return PlatformSendResponse(success=False, error_message="No send_message method")

            if success:
                return PlatformSendResponse(success=True, message_id=message_id)
            else:
                return PlatformSendResponse(
                    success=False,
                    error_message="Failed to send message to Telegram"
                )

        except Exception as e:
            error_msg = f"Error sending message to Telegram: {str(e)}"
            logger.error(error_msg)
            return PlatformSendResponse(success=False, error_message=error_msg)

    def build_chat_key(self, channel_id: str) -> str:
        """构建聊天键"""
        return f"{self.key}-{channel_id}"

    def parse_chat_key(self, chat_key: str) -> Tuple[str, str]:
        """解析聊天键"""
        parts = chat_key.split('-', 1)
        if len(parts) != 2:
            return self.key, chat_key  # 如果解析失败，返回默认值
        return parts[0], parts[1]

    def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        router = APIRouter(prefix=f"/adapters/{self.key}", tags=["adapters", self.key])

        # 这里可以添加适配器特有的API路由
        # 例如：获取机器人信息、管理群组等

        @router.get("/info")
        async def get_telegram_info():
            """获取 Telegram 适配器信息"""
            return {
                "adapter": self.key,
                "metadata": self.metadata.model_dump(),
                # is_connected 在未安装 pyrogram 或未 start 时应容错
                "status": (
                    "connected"
                    if getattr(getattr(self.client, "_client", None), "is_connected", False)
                    else "disconnected"
                ),
            }

        return router

    async def get_platform_user(self, user_id: str) -> Optional[PlatformUser]:
        """获取平台用户信息"""
        # 在实际实现中，这里应该调用 Telegram API 获取用户信息
        return PlatformUser(
            platform_name=self.key,
            user_id=user_id,
            user_name=f"User_{user_id}",
            user_avatar=""
        )

    async def get_platform_channel(self, channel_id: str) -> Optional[PlatformChannel]:
        """获取平台频道信息"""
        # 在实际实现中，这里应该调用 Telegram API 获取频道信息
        channel_type = ChatType.PRIVATE if channel_id.startswith("private_") else ChatType.GROUP
        return PlatformChannel(
            channel_id=channel_id,
            channel_name=f"Channel_{channel_id}",
            channel_type=channel_type,
            channel_avatar=""
        )
    
    async def get_self_info(self) -> PlatformUser:
        """获取自身信息（实现抽象方法）"""
        # 在实际实现中，这里应该调用 Telegram API 获取机器人自身信息
        return PlatformUser(
            platform_name=self.key,
            user_id="telegram_bot",
            user_name="Telegram Bot",
            user_avatar=""
        )
    
    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        """获取用户(或者群聊用户)信息（实现抽象方法）"""
        # 在实际实现中，这里应该调用 Telegram API 获取用户信息
        # channel_id 参数在这里可以用于获取群聊中的用户特定信息
        return await self.get_platform_user(user_id) or PlatformUser(
            platform_name=self.key,
            user_id=user_id,
            user_name=f"User_{user_id}",
            user_avatar=""
        )
    
    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息（实现抽象方法）"""
        # 在实际实现中，这里应该调用 Telegram API 获取频道信息
        return await self.get_platform_channel(channel_id) or PlatformChannel(
            channel_id=channel_id,
            channel_name=f"Channel_{channel_id}",
            channel_type=ChatType.PRIVATE if channel_id.startswith('-100') else ChatType.GROUP,
            channel_avatar=""
        )