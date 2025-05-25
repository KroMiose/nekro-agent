from dataclasses import dataclass
from typing import Any, Dict, Optional, TypedDict

from nonebot.adapters.onebot.v11 import Bot, NoticeEvent

from nekro_agent.core.config import config
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType


@dataclass
class NoticeConfig:
    """通知配置"""

    force_tome: bool = False  # 是否强制设置为 tome
    use_system_sender: bool = False  # 是否使用系统发送者 (platform_userid='0')
    use_operator_as_sender: bool = False  # 是否使用操作者作为发送者


class BaseNoticeHandler:
    """通知处理器基类"""

    def __init__(self):
        self.config = self.get_notice_config()

    def get_notice_config(self) -> NoticeConfig:
        """获取通知配置"""
        return NoticeConfig()

    def match(self, _db_chat_channel: DBChatChannel, event_dict: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """匹配通知事件并提取信息

        Args:
            event_dict (Dict[str, Any]): 通知事件字典

        Returns:
            Optional[Dict[str, str]]: 通知信息，如果不匹配则返回 None
        """
        raise NotImplementedError

    async def format_message(self, _db_chat_channel: DBChatChannel, info: Dict[str, str]) -> str:
        """格式化消息

        Args:
            info (Dict[str, str]): 通知信息

        Returns:
            str: 格式化后的消息
        """
        raise NotImplementedError

    def get_sender_platform_userid(self, info: Dict[str, str]) -> str:
        """获取发送者平台用户ID

        Args:
            info (Dict[str, str]): 通知信息

        Returns:
            str: 发送者平台用户ID
        """
        if self.config.use_system_sender:
            return "0"
        if self.config.use_operator_as_sender and "operator_id" in info:
            return str(info["operator_id"])
        return str(info["user_id"])


class NoticeResult(TypedDict):
    """通知处理结果"""

    handler: BaseNoticeHandler
    info: Dict[str, str]
