"""WeChatPad 适配器包

这个包实现了与 WeChatPadPro API 的集成，支持微信消息的接收和发送。

主要组件：
- WeChatPadAdapter: 主适配器类
- WeChatPadConfig: 配置类
- WeChatPadClient: HTTP 客户端
- WeChatPadMessageEvent: 消息事件模型
"""

from .adapter import WeChatPadAdapter
from .config import WeChatPadConfig
from .http_client import WeChatPadClient
from .schemas import WeChatPadMessageEvent, MessageType
from .realtime_processor import (
    WeChatRealtimeProcessor,
    WeChatMessage,
    MessageHandler,
    TextMessageHandler,
    GroupMessageHandler,
)

__all__ = [
    "WeChatPadAdapter",
    "WeChatPadConfig", 
    "WeChatPadClient",
    "WeChatPadMessageEvent",
    "MessageType",
    "WeChatRealtimeProcessor",
    "WeChatMessage",
    "MessageHandler",
    "TextMessageHandler",
    "GroupMessageHandler",
]