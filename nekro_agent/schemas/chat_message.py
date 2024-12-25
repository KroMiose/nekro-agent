from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class ChatType(Enum):
    PRIVATE = "private"
    GROUP = "group"

    @classmethod
    def from_chat_key(cls, chat_key: str) -> "ChatType":
        try:
            chat_type, _ = chat_key.split("_")
            return cls(chat_type)
        except ValueError as e:
            raise ValueError(f"Invalid chat key: {chat_key}") from e


class ChatMessageSegmentType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    FILE = "file"
    REFERENCE = "reference"
    AT = "at"


class ChatMessageSegment(BaseModel):
    """聊天消息段基础文本"""

    type: ChatMessageSegmentType
    text: str

    class Config:
        use_enum_values = True


class ChatMessageSegmentAt(ChatMessageSegment):
    """聊天消息段 @"""

    target_qq: str  # 被 @ 的人平台 id
    target_nickname: str  # 被 @ 的人原始昵称


class ChatMessageSegmentFile(ChatMessageSegment):
    """聊天消息段文件"""

    file_name: str
    local_path: Optional[str] = None
    remote_url: Optional[str] = None


class ChatMessageSegmentImage(ChatMessageSegmentFile):
    """聊天消息段图片"""


def segment_from_dict(data: Dict) -> ChatMessageSegment:
    """根据字典数据创建聊天消息段"""
    segment_type = ChatMessageSegmentType(data["type"])
    if segment_type == ChatMessageSegmentType.TEXT:
        return ChatMessageSegment.model_validate(data)
    if segment_type == ChatMessageSegmentType.IMAGE:
        return ChatMessageSegmentImage.model_validate(data)
    if segment_type == ChatMessageSegmentType.FILE:
        return ChatMessageSegmentFile.model_validate(data)
    if segment_type == ChatMessageSegmentType.AT:
        return ChatMessageSegmentAt.model_validate(data)
    raise ValueError(f"Unsupported segment type: {segment_type}")


def segments_from_list(data: List[Dict]) -> List[ChatMessageSegment]:
    """根据列表数据创建聊天消息段列表"""
    return [segment_from_dict(item) for item in data]


class ChatMessage(BaseModel):
    message_id: str  # 消息的平台 ID
    sender_id: int  # 发送者人平台 id
    sender_real_nickname: str  # 发送者原始昵称
    sender_nickname: str  # 发送者会话昵称
    sender_bind_qq: Optional[str]  # 发送者绑定 QQ 号
    is_tome: Optional[int] = 0  # 是否与 Bot 相关消息
    is_recalled: Optional[bool] = False  # 是否为撤回消息

    chat_key: str  # 聊天会话唯一标识
    chat_type: ChatType  # 聊天会话类型
    content_text: str  # 聊天内容文本
    content_data: List[ChatMessageSegment]  # 聊天内容数据

    raw_cq_code: str  # 原始 CQ 码
    ext_data: Dict  # 扩展数据

    send_timestamp: int  # 发送时间戳

    class Config:
        use_enum_values = True
