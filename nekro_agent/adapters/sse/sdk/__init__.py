"""
SSE 客户端SDK
===========

提供用于与SSE适配器通信的客户端SDK工具。
"""

# 从models.py导入标准化的模型
# 从client.py导入客户端类
from .client import SSEClient
from .models import (
    AtSegment,
    ChannelInfo,
    # 频道订阅
    ChannelSubscribeRequest,
    ChannelSubscribeResponse,
    ChunkComplete,
    # 分块传输
    ChunkData,
    # 客户端管理
    ClientInfo,
    ConnectedData,
    # 事件模型
    Event,
    FileSegment,
    HeartbeatData,
    ImageSegment,
    # 消息模型
    MessageBase,
    # 消息段模型
    MessageSegment,
    MessageSegmentType,
    MessageSegmentUnion,
    ReceiveMessage,
    RegisterRequest,
    RegisterResponse,
    # 请求响应
    Request,
    Response,
    SendMessage,
    TextSegment,
    # 用户和频道信息
    UserInfo,
    at,
    file,
    image,
    # 构造函数
    text,
)

# 保持向后兼容的别名
Message = MessageBase

__all__ = [
    "AtSegment",
    "ChannelInfo",
    # 频道订阅
    "ChannelSubscribeRequest",
    "ChannelSubscribeResponse",
    "ChunkComplete",
    # 分块传输
    "ChunkData",
    # 客户端管理
    "ClientInfo",
    "ConnectedData",
    # 事件模型
    "Event",
    "FileSegment",
    "HeartbeatData",
    "ImageSegment",
    "Message",  # 别名
    # 消息模型
    "MessageBase",
    # 消息段模型
    "MessageSegment",
    "MessageSegmentType",
    "MessageSegmentUnion",
    "ReceiveMessage",
    "RegisterRequest",
    "RegisterResponse",
    # 请求响应
    "Request",
    "Response",
    # 客户端
    "SSEClient",
    "SendMessage",
    "TextSegment",
    # 用户和频道信息
    "UserInfo",
    "at",
    "file",
    "image",
    # 构造函数
    "text",
]
