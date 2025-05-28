import os
import re
from typing import Dict, List, Optional

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
            "YOU CAN NOT USE ANY AT MESSAGES IN MINECRAFT SERVER CHAT!",
            "YOU CAN NOT SEND ANY PICTURES OR FILES IN MINECRAFT SERVER CHAT!",
        ]

    async def init(self) -> None:
        """初始化适配器"""
        try:
            driver = nonebot.get_driver()

            # 直接从 driver.config 获取配置
            minecraft_ws_urls = getattr(driver.config, "minecraft_ws_urls", None)
            minecraft_access_token = getattr(driver.config, "minecraft_access_token", "")
            minecraft_server_rcon = getattr(driver.config, "minecraft_server_rcon", None)

            # 检查配置项类型是否正确
            ws_urls_valid = isinstance(minecraft_ws_urls, dict) and minecraft_ws_urls
            token_valid = isinstance(minecraft_access_token, str) and minecraft_access_token
            rcon_valid = isinstance(minecraft_server_rcon, dict) and minecraft_server_rcon

            if ws_urls_valid or (token_valid and rcon_valid):
                from nonebot.adapters.minecraft import Adapter as MinecraftAdapter

                from .matchers.message import register_matcher
                from .matchers.notice import notice_manager

                driver.register_adapter(MinecraftAdapter)
                logger.info(f"Minecraft 适配器 [{self.key}] 已加载")
                register_matcher(self)
            else:
                logger.warning("Minecraft 适配器 由于以下几个配置项错误未能加载")
                if not ws_urls_valid:
                    logger.warning("- minecraft_ws_urls 应该是一个字典")
                if not token_valid:
                    logger.warning("- minecraft_access_token 应该是一个字符串")
                if not rcon_valid:
                    logger.warning("- minecraft_server_rcon 应该是一个字典")
        except Exception as e:
            logger.error(f"Minecraft 适配器初始化失败: {e}", exc_info=True)
            logger.warning("Minecraft 适配器未能加载")

    async def cleanup(self) -> None:
        """清理适配器"""
        return

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
        return PlatformUser(user_id="MinecraftBot", user_name="MinecraftBot")

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        """获取用户(或者群聊用户)信息"""
        raise NotImplementedError

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        return PlatformChannel(channel_id=channel_id, channel_name=channel_id, channel_type=ChatType.GROUP)

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:  # noqa: ARG002
        """设置消息反应（可选实现）"""
        return True
