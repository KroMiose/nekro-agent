"""
SSE 适配器统一通信模型
==================

定义SSE适配器客户端和服务端共用的通信模型。
这些模型被SDK客户端和NekroAgent服务端共同使用，确保类型一致性和良好的开发体验。

基本概念:
- platform: 平台标识，如 'wechat', 'telegram'
- channel_id: 频道标识，如 'group_123456', 'private_user123'
- message_id: 消息唯一标识
"""

import time
import uuid
from enum import Enum
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
)

from pydantic import BaseModel, Field

# =============================================================================
# 基础枚举类型
# =============================================================================


class MessageSegmentType(str, Enum):
    """消息段类型枚举"""

    TEXT = "text"  # 文本消息
    IMAGE = "image"  # 图片消息
    FILE = "file"  # 文件消息
    AT = "at"  # @用户消息
    STICKER = "sticker"  # 表情消息
    LOCATION = "location"  # 位置消息


# =============================================================================
# 消息段模型
# =============================================================================


class MessageSegment(BaseModel):
    """消息段基础模型"""

    type: MessageSegmentType = Field(..., description="消息段类型")

    class Config:
        validate_assignment = True


class TextSegment(MessageSegment):
    """文本消息段"""

    type: Literal[MessageSegmentType.TEXT] = Field(MessageSegmentType.TEXT, description="消息段类型")
    content: str = Field(..., description="文本内容")


class AtSegment(MessageSegment):
    """@消息段"""

    type: Literal[MessageSegmentType.AT] = MessageSegmentType.AT
    user_id: str = Field(..., description="被@用户ID")
    nickname: Optional[str] = Field(None, description="被@用户昵称")


class MediaSegment(MessageSegment):
    """媒体消息段基类"""

    url: Optional[str] = Field(None, description="媒体文件URL")
    name: Optional[str] = Field(None, description="媒体文件名")
    size: Optional[int] = Field(None, description="媒体文件大小(字节)")
    mime_type: Optional[str] = Field(None, description="媒体文件MIME类型")
    base64_url: Optional[str] = Field(None, description="媒体文件的base64编码数据URL")
    suffix: Optional[str] = Field(None, description="文件后缀")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.url and not self.base64_url:
            raise ValueError("url和base64_url至少有一个必须提供")


class ImageSegment(MediaSegment):
    """图片消息段"""

    type: Literal[MessageSegmentType.IMAGE] = MessageSegmentType.IMAGE
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    is_origin: bool = Field(False, description="是否原图")


class FileSegment(MediaSegment):
    """文件消息段"""

    type: Literal[MessageSegmentType.FILE] = Field(MessageSegmentType.FILE, description="消息段类型")


# =============================================================================
# 消息段联合类型
# =============================================================================
MessageSegmentUnion = Annotated[
    Union[TextSegment, ImageSegment, FileSegment, AtSegment],
    Field(discriminator="type"),
]


# =============================================================================
# 消息模型
# =============================================================================


class MessageBase(BaseModel):
    """消息基础模型"""

    segments: List[MessageSegmentUnion] = Field(default_factory=list, description="消息段列表")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="消息时间戳")

    class Config:
        validate_assignment = True


class ReceiveMessage(MessageBase):
    """接收到的消息（客户端发给服务端）"""

    msg_id: str = Field(default="", description="消息ID")
    from_id: str = Field(..., description="发送者ID")
    from_name: str = Field(..., description="发送者名称")
    from_nickname: Optional[str] = Field(None, description="发送者昵称")
    is_to_me: bool = Field(False, description="是否@机器人")
    is_self: bool = Field(False, description="是否自己发送的消息")
    raw_content: Optional[str] = Field(None, description="原始消息内容")
    channel_id: str = Field(..., description="频道ID")
    channel_name: str = Field(default="", description="频道名称")
    platform_name: str = Field(..., description="平台名称")


class SendMessage(MessageBase):
    """要发送的消息（服务端发给客户端）"""

    channel_id: str = Field(..., description="频道ID")


# =============================================================================
# 用户和频道信息模型
# =============================================================================


class UserInfo(BaseModel):
    """用户信息"""

    user_id: str = Field(..., description="用户ID")
    user_name: str = Field(..., description="用户名称")
    user_avatar: Optional[str] = Field(None, description="用户头像URL")
    user_nickname: Optional[str] = Field(None, description="用户备注名")
    platform_name: str = Field(..., description="平台名称")


class ChannelInfo(BaseModel):
    """频道信息"""

    channel_id: str = Field(..., description="频道ID")
    channel_name: str = Field(..., description="频道名称")
    channel_avatar: Optional[str] = Field(None, description="频道头像URL")
    member_count: Optional[int] = Field(None, description="成员数量")
    owner_id: Optional[str] = Field(None, description="群主ID")
    is_admin: bool = Field(False, description="机器人是否为管理员")


# =============================================================================
# 客户端管理模型
# =============================================================================


class ClientInfo(BaseModel):
    """客户端信息"""

    client_id: str = Field(..., description="客户端ID")
    platform: str = Field(..., description="平台标识")
    client_name: str = Field(..., description="客户端名称")
    client_version: str = Field(..., description="客户端版本")


class RegisterRequest(BaseModel):
    """客户端注册请求"""

    platform: str = Field(..., description="平台标识")
    client_name: str = Field(..., description="客户端名称")
    client_version: str = Field(..., description="客户端版本")


class RegisterResponse(BaseModel):
    """客户端注册响应"""

    client_id: str = Field(..., description="客户端ID")
    message: str = Field(..., description="注册结果消息")


# =============================================================================
# 频道订阅模型
# =============================================================================


class ChannelSubscribeRequest(BaseModel):
    """频道订阅请求"""

    channel_ids: List[str] = Field(default_factory=list, description="频道ID列表")
    platform: Optional[str] = Field(None, description="平台标识，如果不提供则使用客户端的平台")


class ChannelSubscribeResponse(BaseModel):
    """频道订阅响应"""

    message: str = Field(..., description="订阅结果消息")


# =============================================================================
# 请求响应模型
# =============================================================================


class Request(BaseModel):
    """服务端向客户端的请求"""

    request_id: str = Field(..., description="请求ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="请求数据")


class Response(BaseModel):
    """客户端向服务端的响应"""

    request_id: str = Field(..., description="请求ID")
    success: bool = Field(..., description="是否处理成功")
    data: Dict[str, Any] = Field(default_factory=dict, description="响应数据")


# =============================================================================
# 分块传输模型
# =============================================================================


class ChunkData(BaseModel):
    """分块数据模型"""

    chunk_id: str = Field(..., description="分块ID（所有分块共享同一个）")
    chunk_index: int = Field(..., description="分块序号（从0开始）")
    total_chunks: int = Field(..., description="总分块数")
    chunk_data: str = Field(..., description="分块的base64数据")
    chunk_size: int = Field(..., description="当前分块大小")
    total_size: int = Field(..., description="原始数据总大小")
    mime_type: Optional[str] = Field(None, description="数据MIME类型")
    filename: Optional[str] = Field(None, description="文件名")
    file_type: str = Field(..., description="文件类型：image/file")


class ChunkComplete(BaseModel):
    """分块传输完成事件"""

    chunk_id: str = Field(..., description="分块ID")
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")


# =============================================================================
# 事件模型
# =============================================================================


class HeartbeatData(BaseModel):
    """心跳数据"""

    timestamp: int = Field(default_factory=lambda: int(time.time()), description="时间戳")


class ConnectedData(BaseModel):
    """连接成功数据"""

    client_id: str = Field(..., description="客户端ID")
    timestamp: int = Field(default_factory=lambda: int(time.time()), description="时间戳")


# 泛型事件模型
T = TypeVar("T", bound=BaseModel)


class Event(Generic[T], BaseModel):
    """通用事件模型"""

    event: str = Field(..., description="事件类型")
    data: T = Field(..., description="事件数据(Pydantic模型)")

    def to_sse_format(self) -> dict:
        """转换为SSE格式"""
        return {"event": self.event, "data": self.data.model_dump_json()}

    @classmethod
    def from_sse_format(cls: Type["Event[T]"], event: str, data_json: str, data_model: Type[T]) -> "Event[T]":
        """从SSE格式创建事件"""
        return cls(event=event, data=data_model.model_validate_json(data_json))


# =============================================================================
# 请求类型枚举
# =============================================================================


class RequestType(str, Enum):
    """客户端请求类型枚举"""

    SEND_MESSAGE = "send_message"
    GET_USER_INFO = "get_user_info"
    GET_CHANNEL_INFO = "get_channel_info"
    GET_SELF_INFO = "get_self_info"
    SET_MESSAGE_REACTION = "set_message_reaction"
    FILE_CHUNK = "file_chunk"
    FILE_CHUNK_COMPLETE = "file_chunk_complete"


class ClientCommand(str, Enum):
    """客户端发往服务端的命令类型"""

    REGISTER = "register"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    MESSAGE = "message"
    RESPONSE = "response"


# =============================================================================
# 客户端事件处理模型
# =============================================================================


class SendMessageRequest(BaseModel):
    """发送消息请求"""

    channel_id: str = Field(..., description="频道ID")
    segments: List[MessageSegmentUnion] = Field(..., description="消息段列表")


class SendMessageResponse(BaseModel):
    """发送消息响应"""

    message_id: str = Field(..., description="发送成功的消息ID")
    success: bool = Field(..., description="是否发送成功")


class GetUserInfoRequest(BaseModel):
    """获取用户信息请求"""

    user_id: str = Field(..., description="用户ID")


class GetChannelInfoRequest(BaseModel):
    """获取频道信息请求"""

    channel_id: str = Field(..., description="频道ID")


class GetSelfInfoRequest(BaseModel):
    """获取自身信息请求"""

    # 无需参数


class FileChunkResponse(BaseModel):
    """文件分块处理响应"""

    success: bool = Field(..., description="是否处理成功")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    message: Optional[str] = Field(None, description="成功消息（如果成功）")


class SetMessageReactionRequest(BaseModel):
    """设置消息反应请求"""

    message_id: str = Field(..., description="消息ID")
    status: bool = Field(True, description="反应状态")


class SetMessageReactionResponse(BaseModel):
    """设置消息反应响应"""

    success: bool = Field(..., description="是否设置成功")
    message: Optional[str] = Field(None, description="结果消息")


# =============================================================================
# 消息段构造函数
# =============================================================================


def text(content: str) -> TextSegment:
    """创建文本消息段"""
    return TextSegment(type=MessageSegmentType.TEXT, content=content)


def at(user_id: str, nickname: Optional[str] = None) -> AtSegment:
    """创建@消息段"""
    return AtSegment(type=MessageSegmentType.AT, user_id=user_id, nickname=nickname)


def image(
    url: Optional[str] = None,
    file_path: Optional[str] = None,
    base64_url: Optional[str] = None,
    bytes_data: Optional[bytes] = None,
    name: Optional[str] = None,
    size: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    mime_type: Optional[str] = None,
    is_origin: bool = False,
    suffix: Optional[str] = None,
) -> ImageSegment:
    """创建图片消息段

    支持多种方式提供图片：URL、文件路径、base64数据或字节数据

    Args:
        url: 图片URL
        file_path: 图片文件路径
        base64_url: 图片base64编码数据
        bytes_data: 图片字节数据
        name: 图片文件名
        size: 图片大小(字节)
        width: 图片宽度
        height: 图片高度
        mime_type: 图片MIME类型
        is_origin: 是否原图
        suffix: 图片后缀

    Returns:
        ImageSegment: 图片消息段
    """
    import base64
    import hashlib
    import mimetypes

    # 确保至少提供了一种图片数据
    if not any([url, file_path, base64_url, bytes_data]):
        raise ValueError("必须提供图片URL、文件路径、base64数据或字节数据中的一种")

    # 从文件路径处理
    if file_path:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"图片文件不存在：{file_path}")

        if not name:
            name = file_path_obj.name

        if not base64_url:
            img_bytes = file_path_obj.read_bytes()
            base64_data = base64.b64encode(img_bytes).decode("utf-8")

            if not size:
                size = len(img_bytes)

            if not mime_type:
                mime_type = mimetypes.guess_type(file_path)[0] or "image/jpeg"

            base64_url = f"data:{mime_type};base64,{base64_data}"

    # 从字节数据处理
    elif bytes_data:
        if not base64_url:
            base64_data = base64.b64encode(bytes_data).decode("utf-8")

            if not size:
                size = len(bytes_data)

            if not name:
                name = f"image_{hashlib.md5(bytes_data).hexdigest()[:8]}.jpg"

            if not mime_type:
                mime_type = "image/jpeg"

            base64_url = f"data:{mime_type};base64,{base64_data}"

    return ImageSegment(
        type=MessageSegmentType.IMAGE,
        url=url,
        base64_url=base64_url,
        name=name,
        size=size,
        mime_type=mime_type,
        width=width,
        height=height,
        is_origin=is_origin,
        suffix=suffix,
    )


def file(
    url: Optional[str] = None,
    file_path: Optional[str] = None,
    base64_url: Optional[str] = None,
    bytes_data: Optional[bytes] = None,
    name: Optional[str] = None,
    size: Optional[int] = None,
    mime_type: Optional[str] = None,
    suffix: Optional[str] = None,
) -> FileSegment:
    """创建文件消息段

    支持多种方式提供文件：URL、文件路径、base64数据或字节数据

    Args:
        url: 文件URL
        file_path: 文件路径
        base64_url: 文件base64编码数据
        bytes_data: 文件字节数据
        name: 文件名
        size: 文件大小(字节)
        mime_type: 文件MIME类型
        suffix: 文件后缀

    Returns:
        FileSegment: 文件消息段
    """
    import base64
    import mimetypes

    # 确保至少提供了一种文件数据
    if not any([url, file_path, base64_url, bytes_data]):
        raise ValueError("必须提供文件URL、文件路径、base64数据或字节数据中的一种")

    # 从文件路径处理
    if file_path:
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"文件不存在：{file_path}")

        if not name:
            name = file_path_obj.name

        if not base64_url:
            with file_path_obj.open("rb") as f:
                file_bytes = f.read()
                base64_data = base64.b64encode(file_bytes).decode("utf-8")

                if not size:
                    size = len(file_bytes)

                if not mime_type:
                    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

                base64_url = f"data:{mime_type};base64,{base64_data}"

    # 从字节数据处理
    elif bytes_data:
        if not base64_url:
            base64_data = base64.b64encode(bytes_data).decode("utf-8")

            if not size:
                size = len(bytes_data)

            if not name:
                name = "file"

            if not mime_type:
                mime_type = "application/octet-stream"

            base64_url = f"data:{mime_type};base64,{base64_data}"

    return FileSegment(
        type=MessageSegmentType.FILE,
        url=url,
        base64_url=base64_url,
        name=name,
        size=size,
        mime_type=mime_type,
        suffix=suffix,
    )
