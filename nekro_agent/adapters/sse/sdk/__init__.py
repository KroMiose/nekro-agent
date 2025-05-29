"""
SSE 客户端SDK
===========

提供用于与SSE适配器通信的客户端SDK工具。
"""

from .client import (
    AtSegment,
    FileSegment,
    ImageSegment,
    Message,
    MessageSegment,
    ReceiveMessage,
    SendMessage,
    SSEClient,
    TextSegment,
    at,
    file,
    image,
    text,
)

__all__ = [
    "AtSegment",
    "FileSegment",
    "ImageSegment",
    "Message",
    "MessageSegment",
    "ReceiveMessage",
    "SSEClient",
    "SendMessage",
    "TextSegment",
    "at",
    "file",
    "image",
    "text",
]
