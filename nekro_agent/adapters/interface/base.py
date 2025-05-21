from abc import ABC, abstractmethod
from typing import List

from fastapi import APIRouter

from nekro_agent.schemas.agent_message import AgentMessageSegment
from nekro_agent.schemas.chat_message import ChatMessage

from .schemas.platform import (
    PlatformChannel,
    PlatformUser,
)


class BaseAdapter(ABC):
    """适配器基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def init(self) -> None:
        """初始化适配器"""
        raise NotImplementedError

    @abstractmethod
    async def parse_user(self, user_id: str) -> PlatformUser:
        """转换协议端用户"""
        raise NotImplementedError

    @abstractmethod
    async def forward_message(self, message: List[AgentMessageSegment]) -> bool:
        """推送消息"""
        raise NotImplementedError

    @abstractmethod
    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        raise NotImplementedError

    @abstractmethod
    async def get_user_info(self, user_id: str) -> PlatformUser:
        """获取用户信息"""
        raise NotImplementedError

    @abstractmethod
    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        raise NotImplementedError

    async def receive_message(self, chat_message: ChatMessage, user: PlatformUser) -> ChatMessage:
        """接收消息"""
        raise NotImplementedError

    async def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        return APIRouter(prefix=f"/adapter/{self.name}")
