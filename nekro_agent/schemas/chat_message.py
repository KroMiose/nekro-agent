import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from nekro_agent.tools.common_util import (
    copy_to_upload_dir,
    download_file,
    download_file_from_base64,
    download_file_from_bytes,
)


class ChatType(Enum):
    PRIVATE = "private"
    GROUP = "group"
    UNKNOWN = "unknown"


class ChatMessageSegmentType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    VIDEO = "video"
    FILE = "file"
    REFERENCE = "reference"
    AT = "at"
    JSON_CARD = "json_card"


class ChatMessageSegment(BaseModel):
    """聊天消息段基础文本"""

    type: ChatMessageSegmentType
    text: str

    class Config:
        use_enum_values = True


class ChatMessageSegmentAt(ChatMessageSegment):
    """聊天消息段 @"""

    target_platform_userid: str  # 被 @ 的人平台用户ID
    target_nickname: str  # 被 @ 的人原始昵称


class ChatMessageSegmentFile(ChatMessageSegment):
    """聊天消息段文件"""

    file_name: str
    local_path: Optional[str] = None
    remote_url: Optional[str] = None

    @classmethod
    def get_segment_type(cls) -> ChatMessageSegmentType:
        return ChatMessageSegmentType.FILE

    @classmethod
    async def create_from_url(cls, url: str, from_chat_key: str, file_name: str = "", use_suffix: str = ""):
        """从 URL 创建文件消息段"""
        if url.startswith("data:"):
            return await cls.create_from_base64(url, from_chat_key, file_name, use_suffix)

        local_path, _file_name = await download_file(url, use_suffix=use_suffix, from_chat_key=from_chat_key)

        return cls(
            type=cls.get_segment_type(),
            text=f"[{cls.get_segment_type().value.capitalize()}: {file_name or _file_name}]",
            file_name=file_name or _file_name,
            local_path=local_path,
            remote_url=url,
        )

    @classmethod
    async def create_form_local_path(cls, local_path: str, from_chat_key: str, file_name: str = "", use_suffix: str = ""):
        """从本地路径创建文件消息段"""
        local_path, _file_name = await copy_to_upload_dir(
            file_path=local_path,
            file_name=file_name,
            use_suffix=use_suffix,
            from_chat_key=from_chat_key,
        )

        return cls(
            type=cls.get_segment_type(),
            text=f"[{cls.get_segment_type().value.capitalize()}: {file_name or _file_name}]",
            file_name=file_name or _file_name,
            local_path=local_path,
        )

    @classmethod
    async def create_from_bytes(cls, _bytes: bytes, from_chat_key: str, file_name: str = "", use_suffix: str = ""):
        """从字节数据创建文件消息段"""
        local_path, _file_name = await download_file_from_bytes(
            bytes_data=_bytes,
            file_name=file_name,
            use_suffix=use_suffix,
            from_chat_key=from_chat_key,
        )

        return cls(
            type=cls.get_segment_type(),
            text=f"[{cls.get_segment_type().value.capitalize()}: {file_name or _file_name}]",
            file_name=file_name or _file_name,
            local_path=local_path,
        )

    @classmethod
    async def create_from_base64(cls, base64_str: str, from_chat_key: str, file_name: str = "", use_suffix: str = ""):
        """从 Base64 数据创建文件消息段"""
        local_path, _file_name = await download_file_from_base64(
            base64_str=base64_str,
            file_name=file_name,
            use_suffix=use_suffix,
            from_chat_key=from_chat_key,
        )

        return cls(
            type=cls.get_segment_type(),
            text=f"[{cls.get_segment_type().value.capitalize()}: {file_name or _file_name}]",
            file_name=file_name or _file_name,
            local_path=local_path,
        )


class ChatMessageSegmentImage(ChatMessageSegmentFile):
    """聊天消息段图片"""

    @classmethod
    def get_segment_type(cls) -> ChatMessageSegmentType:
        return ChatMessageSegmentType.IMAGE


class JsonCardHost(BaseModel):
    """JSON卡片分享者信息"""

    uin: Optional[int] = None
    nick: Optional[str] = None


class JsonCardDetail(BaseModel):
    """JSON卡片详细信息（支持detail_1, detail_2等多种格式）"""

    appid: Optional[str] = None
    appType: Optional[int] = None
    title: Optional[str] = None
    desc: Optional[str] = None
    icon: Optional[str] = None
    preview: Optional[str] = None
    url: Optional[str] = None
    scene: Optional[int] = None
    host: Optional[JsonCardHost] = None
    shareTemplateId: Optional[str] = None
    shareTemplateData: Optional[Dict[str, Any]] = None
    qqdocurl: Optional[str] = None
    showLittleTail: Optional[str] = None
    gamePoints: Optional[str] = None
    gamePointsUrl: Optional[str] = None
    shareOrigin: Optional[int] = None


class JsonCardMeta(BaseModel):
    """JSON卡片Meta信息"""

    detail_1: Optional[JsonCardDetail] = None
    detail_2: Optional[JsonCardDetail] = None
    detail_3: Optional[JsonCardDetail] = None

    class Config:
        extra = "allow"  # 允许其他字段


class ChatMessageSegmentJsonCard(ChatMessageSegment):
    """聊天消息段 JSON卡片"""

    json_data: Dict[str, Any]  # 存储解析后的JSON卡片数据
    card_title: Optional[str] = None  # 卡片标题
    card_desc: Optional[str] = None  # 卡片描述
    card_icon: Optional[str] = None  # 卡片图标URL
    card_preview: Optional[str] = None  # 卡片预览图URL
    card_url: Optional[str] = None  # 卡片链接URL
    share_from_nick: Optional[str] = None  # 分享者昵称

    @classmethod
    def get_segment_type(cls) -> ChatMessageSegmentType:
        """获取消息段类型"""
        return ChatMessageSegmentType.JSON_CARD


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
    if segment_type == ChatMessageSegmentType.JSON_CARD:
        return ChatMessageSegmentJsonCard.model_validate(data)
    raise ValueError(f"Unsupported segment type: {segment_type}")


def segments_from_list(data: List[Dict]) -> List[ChatMessageSegment]:
    """根据列表数据创建聊天消息段列表"""
    return [segment_from_dict(item) for item in data]


class ChatMessage(BaseModel):
    """聊天消息"""

    message_id: str  # 消息的平台 ID
    sender_id: str  # 发送者人平台 id
    sender_name: str  # 发送者原始昵称
    sender_nickname: str  # 发送者频道显示昵称
    adapter_key: str  # 适配器标识
    platform_userid: Optional[str]  # 发送者平台用户ID
    is_tome: Optional[int] = 0  # 是否与 Bot 相关消息
    is_recalled: Optional[bool] = False  # 是否为撤回消息

    chat_key: str  # 聊天频道唯一标识
    chat_type: ChatType  # 聊天频道类型
    content_text: str  # 聊天内容文本
    content_data: List[ChatMessageSegment]  # 聊天内容数据

    raw_cq_code: str  # 原始 CQ 码
    ext_data: Dict[str, Any]  # 扩展数据

    send_timestamp: int  # 发送时间戳

    class Config:
        use_enum_values = True

    @classmethod
    def create_empty(cls, chat_key: str) -> "ChatMessage":
        """创建空消息"""
        return cls(
            message_id="",
            sender_id="",
            sender_name="",
            sender_nickname="",
            adapter_key="",
            platform_userid="",
            is_tome=0,
            is_recalled=False,
            chat_key=chat_key,
            chat_type=ChatType.UNKNOWN,
            content_text="",
            content_data=[],
            raw_cq_code="",
            ext_data={},
            send_timestamp=int(time.time()),
        )

    def is_empty(self) -> bool:
        """判断消息是否为空"""
        return (
            not self.message_id
            and not self.sender_id
            and not self.sender_name
            and not self.sender_nickname
            and not self.adapter_key
            and not self.platform_userid
            and not self.content_text
            and not self.content_data
            and not self.raw_cq_code
        )
