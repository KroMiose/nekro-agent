from typing import List

from fastapi import APIRouter
from nonebot.adapters.minecraft import Bot, Message

from nekro_agent.adapters.interface.base import BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core import logger
from nekro_agent.schemas.chat_message import ChatType

from .core.bot import get_bot
from .matchers.message import register_matcher,send_message


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
        ]

    async def init(self) -> None:
        """初始化适配器"""
        logger.info(f"Minecraft adapter [{self.key}] initialized.")
        register_matcher(self)

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到 Minecraft 协议端"""
        logger.info(f"Forwarding message to Minecraft: {request}")
        other_segments = [seg for seg in request.segments if seg.type == PlatformSendSegmentType.TEXT]
        for seg in other_segments:
            await send_message(seg.content)
        return PlatformSendResponse(success=True)

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        logger.info(f"Self_id:{get_bot().self_id} user_name:{get_bot().self_id}")
        return PlatformUser(user_id=str(get_bot().self_id), user_name=get_bot().self_id)

    async def get_user_info(self, user_id: str) -> PlatformUser:
        """获取用户信息"""
        # TODO: 实现获取 Minecraft 用户信息的逻辑
        raise NotImplementedError

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        # TODO: 实现获取 Minecraft 服务器信息的逻辑
        return PlatformChannel(channel_id=channel_id, channel_name=channel_id, channel_type=ChatType.GROUP)

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:
        """设置消息反应（可选实现）"""
        logger.warning("Minecraft adapter does not support message reactions.")
        return True

    async def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        # TODO: 如果 Minecraft 适配器需要特定的 API 路由，在此实现
        # 默认为基础路由
        return await super().get_adapter_router()

