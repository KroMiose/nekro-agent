import os
import re
from typing import List, Optional

import nonebot
from fastapi import APIRouter
from nonebot.adapters.minecraft import Bot, Message, MessageSegment
from nonebot.adapters.minecraft.model import ClickEvent, HoverEvent, TextColor

from nekro_agent.adapters.interface.base import BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType


class MinecraftAdapter(BaseAdapter):
    """Minecraft 适配器"""

    @property
    def key(self) -> str:
        return "minecraft"

    @property
    def chat_key_rules(self) -> List[str]:
        # TODO: 根据 Minecraft 的实际情况修改
        return [
            "Server chat: `minecraft-servername` (where servername is the name of the Minecraft server)",
            "YOU CAN NOT USE ANY AT IN MINECRAFT SERVER CHAT!",
        ]

    async def init(self) -> None:
        """初始化适配器"""
        if (
            os.environ.get("minecraft_ws_urls")  # noqa: SIM112
            and os.environ.get("minecraft_access_token")  # noqa: SIM112
            and os.environ.get("minecraft_server_rcon")  # noqa: SIM112
        ):
            from nonebot.adapters.minecraft import Adapter as MinecraftAdapter

            from .matchers.message import register_matcher
            from .matchers.notice import notice_manager

            driver = nonebot.get_driver()
            driver.register_adapter(MinecraftAdapter)
            logger.info(f"Minecraft adapter [{self.key}] initialized.")
            register_matcher(self)

    def _remove_at_mentions(self, text: str) -> str:
        """移除文本中的特定格式的 @ 提及 (例如 [@id:123;nickname:test@] 或 [@id:123@])"""
        processed_text = re.sub(r"\[@(?:id:[^;@]+(?:;nickname:[^@]+)?|[^@\]]+)@\]", "", text)
        # 将多个空格替换为单个空格，并去除首尾空格
        return re.sub(r"\\s+", " ", processed_text).strip()

    async def _send_text(self, text: str, chat_key: str):
        """将文本消息通过 Bot 发送到 Minecraft 服务器"""
        from .core.bot import get_bot

        try:
            bot_instance: Optional[Bot] = get_bot(chat_key)
            if not bot_instance:
                logger.error(f"没有找到对应的 Minecraft 服务器: {chat_key}")
                return

            cleaned_text = self._remove_at_mentions(text)
            channel = await DBChatChannel.get_channel(chat_key)
            preset = await channel.get_preset()

            message_to_send = Message(
                [
                    MessageSegment.text(f"<{preset.name}>", color=TextColor.GREEN),
                    MessageSegment.text(
                        cleaned_text,
                    ),
                ],
            )
            await bot_instance.send_msg(message=message_to_send)

        except Exception as e:
            logger.error(f"发送消息时错误 ({chat_key}): {e}", exc_info=True)

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到 Minecraft 协议端"""
        for seg in request.segments:
            if seg.type == PlatformSendSegmentType.TEXT:
                await self._send_text(seg.content, request.chat_key)
        return PlatformSendResponse(success=True)

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        return PlatformUser(user_id="Minecraft Server Bot", user_name="Minecraft Server Bot")

    async def get_user_info(self, user_id: str) -> PlatformUser:
        """获取用户信息"""
        # TODO: 实现获取 Minecraft 用户信息的逻辑
        raise NotImplementedError

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        return PlatformChannel(channel_id=channel_id, channel_name=channel_id, channel_type=ChatType.GROUP)

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:  # noqa: ARG002
        """设置消息反应（可选实现）"""
        return True

    async def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        # TODO: 如果 Minecraft 适配器需要特定的 API 路由，在此实现
        # 默认为基础路由
        return await super().get_adapter_router()
