from enum import Enum
from time import time
from typing import TYPE_CHECKING, List, Optional, Union

from pydantic import BaseModel, Field

from nekro_agent.models.db_chat_channel import DBChatChannel, DefaultPreset
from nekro_agent.models.db_preset import DBPreset
from nekro_agent.schemas.chat_message import ChatMessageSegment, ChatType

from .extra import PlatformMessageExt

if TYPE_CHECKING:
    from nekro_agent.adapters.interface.base import BaseAdapter


class PlatformUser(BaseModel):
    platform_name: str = Field(..., description="平台名称")
    user_id: str = Field(..., description="用户ID")
    user_name: str = Field(..., description="用户名称")
    user_avatar: str = Field(default="", description="用户头像")


class PlatformChannel(BaseModel):
    channel_id: str = Field(..., description="频道ID")
    channel_name: str = Field(..., description="频道名称")
    channel_type: ChatType = Field(default=ChatType.UNKNOWN, description="频道类型")
    channel_avatar: str = Field(default="", description="频道头像")

    async def get_db_chat_channel(self, adapter: "BaseAdapter") -> DBChatChannel:
        return await DBChatChannel.get_or_create(
            adapter_key=adapter.key,
            channel_id=self.channel_id,
            channel_type=self.channel_type,
        )

    async def get_preset(self, adapter: "BaseAdapter") -> Union[DBPreset, DefaultPreset]:
        return await (await self.get_db_chat_channel(adapter)).get_preset()


class PlatformMessage(BaseModel):
    message_id: str = Field(..., description="消息ID")
    sender_id: str = Field(..., description="发送者ID")
    sender_name: str = Field(..., description="发送者名称")
    sender_nickname: str = Field(default="", description="发送者昵称")
    sender_avatar: str = Field(default="", description="发送者头像")
    content_data: List[ChatMessageSegment] = Field(default=[], description="消息内容")
    content_text: str = Field(default="", description="消息内容")
    is_tome: bool = Field(default=False, description="是否为 @ 消息")
    timestamp: int = Field(default_factory=lambda: int(time()), description="消息时间戳")
    is_self: bool = Field(default=False, description="是否为自己发送的消息")
    ext_data: Optional[PlatformMessageExt] = Field(default=PlatformMessageExt(), description="扩展数据")


# ========================================================================================
# |                          协议端消息发送相关数据结构                                      |
# ========================================================================================


class PlatformSendSegmentType(str, Enum):
    """协议端消息段类型"""

    TEXT = "text"
    AT = "at"
    IMAGE = "image"  # 以图片/富文本形式发送
    FILE = "file"  # 以文件上传形式发送


class PlatformAtSegment(BaseModel):
    """@ 消息段"""

    platform_user_id: str = Field(..., description="平台用户ID")
    nickname: Optional[str] = Field(default=None, description="用户昵称")


class PlatformSendSegment(BaseModel):
    """协议端发送消息段

    这是主程序向协议端传递的标准化消息段结构，
    协议端根据 type 字段决定具体的发送方式
    """

    type: PlatformSendSegmentType = Field(..., description="消息段类型")
    content: str = Field(default="", description="消息内容")
    at_info: Optional[PlatformAtSegment] = Field(default=None, description="@ 信息（仅当 type=AT 时有效）")
    file_path: Optional[str] = Field(
        default=None,
        description="文件路径（仅当 type=IMAGE/FILE 时有效，已转换为协议端可访问的路径）",
    )


class PlatformSendRequest(BaseModel):
    """协议端发送请求

    协议端根据 segments 中每个消息段的 type 来决定具体的发送方式：
    - FILE: 文件上传模式
    - IMAGE: 图片/富文本模式
    - TEXT/AT: 普通文本消息
    """

    chat_key: str = Field(..., description="会话标识")
    segments: List[PlatformSendSegment] = Field(default=[], description="消息段列表")
    ref_msg_id: Optional[str] = Field(default=None, description="引用消息ID")


class PlatformSendResponse(BaseModel):
    """协议端发送响应"""

    success: bool = Field(..., description="是否发送成功")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    message_id: Optional[str] = Field(default=None, description="消息ID")
