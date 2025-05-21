from typing import List

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformUser,
)
from nekro_agent.schemas.agent_message import AgentMessageSegment

from ..interface.base import BaseAdapter


class NoneBotAdapter(BaseAdapter):
    """NoneBot 适配器"""

    @property
    def name(self) -> str:
        return "nonebot"

    async def init(self) -> None:
        """初始化适配器"""
        from . import matchers

    async def parse_user(self, user_id: str) -> PlatformUser:
        """转换协议端用户"""
        raise NotImplementedError

    async def forward_message(self, message: List[AgentMessageSegment]) -> bool:
        """推送消息"""
        raise NotImplementedError

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        raise NotImplementedError

    async def get_user_info(self, user_id: str) -> PlatformUser:
        """获取用户信息"""
        raise NotImplementedError

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        raise NotImplementedError
