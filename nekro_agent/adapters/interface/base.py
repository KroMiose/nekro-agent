from abc import ABC, abstractmethod
from typing import List

from fastapi import APIRouter

from nekro_agent.schemas.agent_message import AgentMessageSegment
from nekro_agent.schemas.chat_message import ChatMessage

from .schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformUser,
)


class BaseAdapter(ABC):
    """适配器基类"""

    @property
    def key(self) -> str:
        raise NotImplementedError

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "Group chat: `platform-group_123456` (where 123456 is the group number)",
            "Private chat: `platform-private_123456` (where 123456 is the user's QQ number)",
        ]

    @abstractmethod
    async def init(self) -> None:
        """初始化适配器"""
        raise NotImplementedError

    @abstractmethod
    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到协议端

        Args:
            request: 协议端发送请求，包含已经预处理好的消息数据

        Returns:
            PlatformSendResponse: 发送结果
        """
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

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:  # noqa: ARG002
        """设置消息反应（可选实现）

        Args:
            message_id (str): 消息ID
            status (bool): True为设置反应，False为取消反应

        Returns:
            bool: 是否成功设置
        """
        # 默认实现：不支持消息反应功能
        return False

    async def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        return APIRouter(prefix=f"/adapter/{self.key}")
