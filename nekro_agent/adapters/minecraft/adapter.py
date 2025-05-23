from typing import List

from fastapi import APIRouter

from nekro_agent.adapters.interface.base import BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformUser,
)
from nekro_agent.core import logger
from .matchers.message import recv_minecraft_message

class MinecraftAdapter(BaseAdapter):
    """Minecraft 适配器"""

    @property
    def key(self) -> str:
        return "minecraft"

    @property
    def chat_key_rules(self) -> List[str]:
        # TODO: 根据 Minecraft 的实际情况修改
        return [
            "Server chat: `minecraft-server_servername` (where servername is the name of the Minecraft server)",
        ]

    async def init(self) -> None:
        """初始化适配器"""
        logger.info(f"Minecraft adapter [{self.key}] initialized.")
        # TODO: 实现 Minecraft 适配器的初始化逻辑
        # 例如：连接到 Minecraft 服务器，注册事件监听器等
        pass

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到 Minecraft 协议端"""
        # TODO: 实现将消息推送到 Minecraft 服务器的逻辑
        logger.info(f"Forwarding message to Minecraft: {request}")
        raise NotImplementedError

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        # TODO: 实现获取 Minecraft 机器人自身信息的逻辑
        raise NotImplementedError

    async def get_user_info(self, user_id: str) -> PlatformUser:
        """获取用户信息"""
        # TODO: 实现获取 Minecraft 用户信息的逻辑
        raise NotImplementedError

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        # TODO: 实现获取 Minecraft 频道/服务器信息的逻辑
        raise NotImplementedError

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:
        """设置消息反应（可选实现）"""
        # Minecraft 通常不支持消息反应，因此返回 False
        logger.warning("Minecraft adapter does not support message reactions.")
        return False

    async def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        # TODO: 如果 Minecraft 适配器需要特定的 API 路由，在此实现
        # 默认为基础路由
        return await super().get_adapter_router()

