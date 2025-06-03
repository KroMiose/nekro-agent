"""
SSE 适配器模型定义
===============

定义了SSE适配器使用的各种数据模型，包括:
1. 消息段模型 (SseSegment)
2. 消息模型 (SseMessage)
3. 用户模型 (SseUserInfo)
4. 频道模型 (SseChannelInfo)
5. 命令模型 (SseCommand)
6. 客户端模型 (SseClientInfo)
7. 请求响应模型 (SseRequest, SseResponse)

基本概念:
- platform: 平台标识，如 'wechat', 'telegram'
- channel_id: 频道标识，如 'group_123456', 'private_user123'
- chat_key: 内部使用的会话标识，格式为 'sse-{platform}-{channel_id}'
"""

import time
import uuid
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, Field


# 消息段类型
class SseSegmentType(str, Enum):
    """SSE消息段类型"""

    TEXT = "text"  # 文本消息
    IMAGE = "image"  # 图片消息
    FILE = "file"  # 文件消息
    AT = "at"  # @用户消息
    STICKER = "sticker"  # 表情消息
    LOCATION = "location"  # 位置消息


# 消息段基础模型
class SseSegment(BaseModel):
    """SSE消息段基础模型"""

    type: SseSegmentType = Field(..., description="消息段类型")


class SseTextSegment(SseSegment):
    """文本消息段"""

    content: str = Field(..., description="文本内容")


class SseAtSegment(SseSegment):
    """@消息段"""

    user_id: str = Field(..., description="被@用户ID")
    nickname: Optional[str] = Field(None, description="被@用户昵称")


class SseMediaSegment(SseSegment):
    """媒体消息段基类"""

    url: Optional[str] = Field(None, description="媒体文件URL")
    name: Optional[str] = Field(None, description="媒体文件名")
    size: Optional[int] = Field(None, description="媒体文件大小(字节)")
    mime_type: Optional[str] = Field(None, description="媒体文件MIME类型")
    base64_url: Optional[str] = Field(None, description="媒体文件的base64编码数据URL")
    
    # 扩展校验：url和base64_url至少一个不为空
    def __init__(self, **data):
        super().__init__(**data)
        if not self.url and not self.base64_url:
            raise ValueError("url和base64_url至少有一个必须提供")


class SseImageSegment(SseMediaSegment):
    """图片消息段"""

    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    is_origin: bool = Field(False, description="是否原图")


class SseFileSegment(SseMediaSegment):
    """文件消息段"""


class SseStickerSegment(SseMediaSegment):
    """表情消息段"""


class SseLocationSegment(SseSegment):
    """位置消息段"""

    latitude: float = Field(..., description="纬度")
    longitude: float = Field(..., description="经度")
    title: Optional[str] = Field(None, description="位置标题")
    address: Optional[str] = Field(None, description="位置地址")


# 统一消息段类型
SseSegmentUnion = Union[
    SseTextSegment,
    SseAtSegment,
    SseImageSegment,
    SseFileSegment,
    SseStickerSegment,
    SseLocationSegment,
]


# 消息相关模型
class SseMessageBase(BaseModel):
    """SSE消息基础模型"""

    segments: List[SseSegmentUnion] = Field(default_factory=list, description="消息段列表")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="消息时间戳")


class SseReceiveMessage(SseMessageBase):
    """SSE接收消息"""

    msg_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="消息ID")
    from_id: str = Field(..., description="发送者ID")
    from_name: str = Field(..., description="发送者名称")
    from_nickname: Optional[str] = Field(None, description="发送者昵称")
    is_to_me: bool = Field(False, description="是否@机器人")
    is_self: bool = Field(False, description="是否自己发送的消息")
    raw_content: Optional[str] = Field(None, description="原始消息内容")
    channel_id: str = Field(..., description="频道ID")
    channel_name: str = Field(default="", description="频道名称")


class SseMessage(SseMessageBase):
    """SSE发送消息"""

    channel_id: str = Field(..., description="频道ID")


# 客户端相关模型
class SseClientInfo(BaseModel):
    """客户端信息"""

    client_id: str = Field(..., description="客户端ID")
    platform: str = Field(..., description="平台标识")
    client_name: str = Field(..., description="客户端名称")
    client_version: str = Field(..., description="客户端版本")


# 客户端注册相关模型
class SseRegisterRequest(BaseModel):
    """客户端注册请求"""

    platform: str = Field(..., description="平台标识")
    client_name: str = Field(..., description="客户端名称")
    client_version: str = Field(..., description="客户端版本")


class SseRegisterResponse(BaseModel):
    """客户端注册响应"""

    client_id: str = Field(..., description="客户端ID")
    message: str = Field(..., description="注册结果消息")


# 频道相关模型
class SseChannelSubscribeRequest(BaseModel):
    """频道订阅请求"""

    channel_id: str = Field(..., description="频道ID")
    platform: Optional[str] = Field(None, description="平台标识，如果不提供则使用客户端的平台")


class SseChannelSubscribeResponse(BaseModel):
    """频道订阅响应"""

    message: str = Field(..., description="订阅结果消息")


# 用户信息相关模型
class SseUserInfo(BaseModel):
    """用户信息"""

    user_id: str = Field(..., description="用户ID")
    user_name: str = Field(..., description="用户名称")
    user_avatar: Optional[str] = Field(None, description="用户头像URL")
    user_remark: Optional[str] = Field(None, description="用户备注名")
    is_friend: bool = Field(False, description="是否为好友")


# 频道信息相关模型
class SseChannelInfo(BaseModel):
    """频道信息"""

    channel_id: str = Field(..., description="频道ID")
    channel_name: str = Field(..., description="频道名称")
    channel_avatar: Optional[str] = Field(None, description="频道头像URL")
    member_count: Optional[int] = Field(None, description="成员数量")
    owner_id: Optional[str] = Field(None, description="群主ID")
    is_admin: bool = Field(False, description="机器人是否为管理员")


# 客户端请求响应相关模型
class SseRequest(BaseModel):
    """服务端向客户端的请求"""

    request_id: str = Field(..., description="请求ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="请求数据")


class SseResponse(BaseModel):
    """客户端向服务端的响应"""

    request_id: str = Field(..., description="请求ID")
    success: bool = Field(..., description="是否处理成功")
    data: Dict[str, Any] = Field(default_factory=dict, description="响应数据")


# 通用事件data模型
class SseHeartbeatData(BaseModel):
    timestamp: int


class SseConnectedData(BaseModel):
    client_id: str
    timestamp: int


# 泛型事件模型，data必须是BaseModel
T = TypeVar("T", bound=BaseModel)


class SseEvent(Generic[T], BaseModel):
    event: str = Field(..., description="事件类型")
    data: T = Field(..., description="事件数据(Pydantic模型)")

    def to_sse_format(self) -> dict:
        return {"event": self.event, "data": self.data.json()}

    @classmethod
    def from_sse_format(cls: Type["SseEvent[T]"], event: str, data_json: str, data_model: Type[T]) -> "SseEvent[T]":
        return cls(event=event, data=data_model.parse_raw(data_json))


# 消息段辅助函数
def text(content: str) -> SseTextSegment:
    """创建文本消息段"""
    return SseTextSegment(type=SseSegmentType.TEXT, content=content)


def at(user_id: str, nickname: Optional[str] = None) -> SseAtSegment:
    """创建@消息段"""
    return SseAtSegment(type=SseSegmentType.AT, user_id=user_id, nickname=nickname)


def image(
    url: Optional[str] = None,
    base64_url: Optional[str] = None,
    name: Optional[str] = None,
    size: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    mime_type: str = "image/jpeg",
    is_origin: bool = False,
) -> SseImageSegment:
    """创建图片消息段"""
    return SseImageSegment(
        type=SseSegmentType.IMAGE,
        url=url,
        base64_url=base64_url,
        name=name,
        size=size,
        mime_type=mime_type,
        width=width,
        height=height,
        is_origin=is_origin,
    )


def file(
    url: Optional[str] = None,
    base64_url: Optional[str] = None,
    name: Optional[str] = None,
    size: Optional[int] = None,
    mime_type: Optional[str] = None,
) -> SseFileSegment:
    """创建文件消息段"""
    return SseFileSegment(
        type=SseSegmentType.FILE, 
        url=url, 
        base64_url=base64_url,
        name=name, 
        size=size, 
        mime_type=mime_type,
    )
