#!/usr/bin/env python3
"""
WeChatPad 实时消息处理器
基于WebSocket实现实时消息接收和处理
"""

import asyncio
import json
import logging
import websockets
import urllib.parse
from typing import Dict, Any, Callable, Optional, List, TYPE_CHECKING
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from nekro_agent.core import logger as nekro_logger
from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformMessage,
    PlatformUser,
)
from nekro_agent.adapters.interface.schemas.extra import PlatformMessageExt
from nekro_agent.schemas.chat_message import ChatMessageSegment, ChatType

from .config import WeChatPadConfig

if TYPE_CHECKING:
    from .adapter import WeChatPadAdapter


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = 1          # 文本消息
    IMAGE = 3         # 图片消息
    VOICE = 34        # 语音消息
    VIDEO = 43        # 视频消息
    EMOJI = 47        # 表情消息
    LOCATION = 48     # 位置消息
    LINK = 49         # 链接消息
    FILE = 6          # 文件消息
    SYSTEM = 10000    # 系统消息


@dataclass
class WeChatMessage:
    """微信消息数据结构"""
    msg_id: int
    from_user: str
    to_user: str
    msg_type: int
    content: str
    status: int
    create_time: int
    msg_source: str
    push_content: str
    new_msg_id: int
    
    @property
    def message_type(self) -> MessageType:
        """获取消息类型枚举"""
        try:
            return MessageType(self.msg_type)
        except ValueError:
            return MessageType.TEXT  # 默认为文本消息
    
    @property
    def create_datetime(self) -> datetime:
        """获取创建时间的datetime对象"""
        return datetime.fromtimestamp(self.create_time)
    
    @property
    def is_group_message(self) -> bool:
        """判断是否为群消息"""
        return "@chatroom" in self.to_user or "@chatroom" in self.from_user
    
    @property
    def sender_name(self) -> str:
        """从push_content中提取发送者名称"""
        if " : " in self.push_content:
            return self.push_content.split(" : ")[0]
        return self.from_user
    
    @property
    def actual_sender_wxid(self) -> str:
        """获取实际发送者的wxid（处理群消息中的真实发送者）"""
        if self.is_group_message and ":" in self.content:
            # 群消息格式: "wxid_xxx:\n消息内容"
            lines = self.content.split("\n", 1)
            if len(lines) > 0 and lines[0].endswith(":"):
                return lines[0][:-1]  # 移除末尾的冒号
        return self.from_user
    
    @property
    def actual_content(self) -> str:
        """获取实际消息内容（处理群消息格式）"""
        if self.is_group_message and ":" in self.content:
            # 群消息格式: "wxid_xxx:\n消息内容"
            lines = self.content.split("\n", 1)
            if len(lines) > 1 and lines[0].endswith(":"):
                return lines[1]  # 返回实际消息内容
        return self.content
    
    @property
    def channel_id(self) -> str:
        """获取频道ID（群聊ID或私聊对方ID）"""
        if self.is_group_message:
            # 群消息：使用to_user作为群ID
            return self.to_user
        else:
            # 私聊：使用实际发送者ID
            return self.actual_sender_wxid
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "msg_id": self.msg_id,
            "from_user": self.from_user,
            "to_user": self.to_user,
            "msg_type": self.msg_type,
            "message_type": self.message_type.name,
            "content": self.content,
            "status": self.status,
            "create_time": self.create_time,
            "create_datetime": self.create_datetime.isoformat(),
            "msg_source": self.msg_source,
            "push_content": self.push_content,
            "new_msg_id": self.new_msg_id,
            "is_group_message": self.is_group_message,
            "sender_name": self.sender_name
        }


class MessageHandler:
    """消息处理器基类"""
    
    async def handle_message(self, message: WeChatMessage) -> bool:
        """
        处理消息
        返回True表示消息已处理，False表示继续传递给下一个处理器
        """
        raise NotImplementedError


class TextMessageHandler(MessageHandler):
    """文本消息处理器"""
    
    def __init__(self, keywords: List[str] = None, callback: Callable = None):
        self.keywords = keywords or []
        self.callback = callback
    
    async def handle_message(self, message: WeChatMessage) -> bool:
        if message.message_type != MessageType.TEXT:
            return False
        
        # 关键词过滤
        if self.keywords:
            if not any(keyword in message.content for keyword in self.keywords):
                return False
        
        logging.info(f"处理文本消息: {message.sender_name} -> {message.content}")
        
        if self.callback:
            await self.callback(message)
        
        return True


class GroupMessageHandler(MessageHandler):
    """群消息处理器"""
    
    def __init__(self, group_ids: List[str] = None, callback: Callable = None):
        self.group_ids = group_ids or []
        self.callback = callback
    
    async def handle_message(self, message: WeChatMessage) -> bool:
        if not message.is_group_message:
            return False
        
        # 群ID过滤
        if self.group_ids:
            if not any(group_id in message.to_user or group_id in message.from_user 
                      for group_id in self.group_ids):
                return False
        
        logging.info(f"处理群消息: {message.sender_name} 在群中发送 -> {message.content}")
        
        if self.callback:
            await self.callback(message)
        
        return True


class WeChatRealtimeProcessor:
    """微信实时消息处理器"""
    
    def __init__(self, config: WeChatPadConfig, adapter: Optional['WeChatPadAdapter'] = None):
        self.config = config
        self.adapter = adapter  # 适配器引用，用于消息转发
        self.handlers: List[MessageHandler] = []
        self.is_running = False
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.start_time: Optional[datetime] = None
        self.message_count = 0
        
        # 设置日志记录器
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        
    def add_handler(self, handler: MessageHandler):
        """添加消息处理器"""
        self.handlers.append(handler)
        self.logger.info(f"添加消息处理器: {handler.__class__.__name__}")
    
    def remove_handler(self, handler: MessageHandler):
        """移除消息处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)
            self.logger.info(f"移除消息处理器: {handler.__class__.__name__}")
    
    def _build_websocket_url(self) -> str:
        """构建WebSocket URL"""
        base_url = self.config.WECHATPAD_API_URL
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url += "/ws/GetSyncMsg"
        
        # 添加认证参数
        params = {"key": self.config.WECHATPAD_AUTH_KEY}
        ws_url += "?" + urllib.parse.urlencode(params)
        
        return ws_url
    
    def _parse_message(self, raw_data: str) -> Optional[WeChatMessage]:
        """解析原始消息数据"""
        try:
            data = json.loads(raw_data)
            
            # 提取消息字段
            msg_id = data.get("msg_id", 0)
            from_user = data.get("from_user_name", {}).get("str", "")
            to_user = data.get("to_user_name", {}).get("str", "")
            msg_type = data.get("msg_type", 1)
            content = data.get("content", {}).get("str", "")
            status = data.get("status", 0)
            create_time = data.get("create_time", 0)
            msg_source = data.get("msg_source", "")
            push_content = data.get("push_content", "")
            new_msg_id = data.get("new_msg_id", 0)
            
            return WeChatMessage(
                msg_id=msg_id,
                from_user=from_user,
                to_user=to_user,
                msg_type=msg_type,
                content=content,
                status=status,
                create_time=create_time,
                msg_source=msg_source,
                push_content=push_content,
                new_msg_id=new_msg_id
            )
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error(f"解析消息失败: {e}, 原始数据: {raw_data}")
            return None
    
    async def _process_message(self, message: WeChatMessage):
        """处理单条消息"""
        self.message_count += 1
        
        self.logger.debug(f"收到消息 #{self.message_count}: {message.sender_name} -> {message.actual_content}")
        
        # 1. 转发消息到nekro-agent核心系统
        if self.adapter:
            try:
                await self._forward_to_nekro_agent(message)
            except Exception as e:
                self.logger.error(f"转发消息到nekro-agent失败: {e}")
        
        # 2. 依次调用自定义处理器
        for handler in self.handlers:
            try:
                handled = await handler.handle_message(message)
                if handled:
                    self.logger.debug(f"消息被处理器 {handler.__class__.__name__} 处理")
                    break
            except Exception as e:
                self.logger.error(f"处理器 {handler.__class__.__name__} 处理消息时出错: {e}")
    
    async def _forward_to_nekro_agent(self, message: WeChatMessage):
        """转发消息到nekro-agent核心系统"""
        if not self.adapter:
            return
        
        # 获取自身信息用于判断 is_self
        try:
            self_info = await self.adapter.get_self_info()
            bot_wxid = self_info.user_id
        except Exception as e:
            self.logger.warning(f"获取自身信息失败，无法判断 is_self: {e}")
            bot_wxid = ""
        
        # 判断是否为自己发送的消息
        is_self = message.actual_sender_wxid == bot_wxid
        
        # 如果是自己发送的消息，跳过处理
        if is_self:
            self.logger.debug(f"跳过自己发送的消息: {message.actual_content[:50]}...")
            return
        
        # 判断是群聊还是私聊
        is_group = message.is_group_message
        channel_id = message.channel_id
        chat_type = ChatType.GROUP if is_group else ChatType.PRIVATE
        
        # 判断是否为 @ 消息（仅在群聊中有意义）
        is_tome = False
        if is_group and bot_wxid:
            # 检查消息中是否包含 @ 机器人的内容
            is_tome = (f"@{bot_wxid}" in message.actual_content or 
                      message.actual_content.startswith("@"))
        elif not is_group:
            # 私聊消息默认为 @ 机器人
            is_tome = True
        
        # 构造平台频道信息
        platform_channel = PlatformChannel(
            channel_id=channel_id,
            channel_name=message.group_name if is_group else "",  # 
            channel_type=chat_type,
        )
        
        # 构造平台用户信息
        platform_user = PlatformUser(
            user_id=message.actual_sender_wxid,
            user_name=message.sender_name,
            platform_name="微信",
            user_avatar="",  # 暂时为空，后续可通过 API 获取
        )
        
        # 构造消息段（根据消息类型处理）
        content_segments = []
        if message.message_type == MessageType.TEXT:
            content_segments.append(ChatMessageSegment(
                type="text",
                data={"text": message.actual_content}
            ))
        elif message.message_type == MessageType.IMAGE:
            # TODO: 解析图片XML数据，提取图片URL
            content_segments.append(ChatMessageSegment(
                type="text",
                data={"text": "[图片]"}
            ))
        elif message.message_type == MessageType.VOICE:
            # TODO: 解析语音XML数据，提取语音URL
            content_segments.append(ChatMessageSegment(
                type="text",
                data={"text": "[语音]"}
            ))
        elif message.message_type == MessageType.EMOJI:
            # TODO: 解析表情XML数据，提取表情URL
            content_segments.append(ChatMessageSegment(
                type="text",
                data={"text": "[表情]"}
            ))
        else:
            # 其他类型消息，使用原始内容
            content_segments.append(ChatMessageSegment(
                type="text",
                data={"text": message.actual_content}
            ))
        
        # 构造平台消息
        platform_message = PlatformMessage(
            message_id=str(message.msg_id),
            sender_id=message.actual_sender_wxid,
            sender_name=message.sender_name,
            sender_nickname=message.sender_name,
            content_data=content_segments,
            content_text=message.actual_content,
            is_tome=is_tome,
            timestamp=message.create_time,
            is_self=is_self,
            ext_data=PlatformMessageExt(),  # 扩展数据，后续可添加引用消息等信息
        )
        
        # 提交消息到收集器
        await collect_message(self.adapter, platform_channel, platform_user, platform_message)
        
        nekro_logger.info(f"实时消息已转发: [{channel_id}] {message.sender_name}: {message.actual_content}")
    
    async def start(self):
        """启动实时消息处理"""
        if self.is_running:
            self.logger.warning("实时消息处理器已在运行")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        self.message_count = 0
        
        ws_url = self._build_websocket_url()
        self.logger.info(f"连接WebSocket: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                self.websocket = websocket
                self.logger.info("✅ WebSocket连接成功，开始接收消息...")
                
                async for raw_message in websocket:
                    if not self.is_running:
                        break
                    
                    # 解析消息
                    message = self._parse_message(raw_message)
                    if message:
                        # 处理消息
                        await self._process_message(message)
                    else:
                        self.logger.warning(f"无法解析消息: {raw_message}")
                        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("WebSocket连接已关闭")
        except Exception as e:
            self.logger.error(f"WebSocket连接错误: {e}")
        finally:
            self.is_running = False
            self.websocket = None
            self.logger.info("实时消息处理器已停止")
    
    async def stop(self):
        """停止实时消息处理"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
        
        self.logger.info("正在停止实时消息处理器...")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if self.start_time:
            running_time = datetime.now() - self.start_time
            messages_per_minute = self.message_count / max(running_time.total_seconds() / 60, 1)
        else:
            running_time = None
            messages_per_minute = 0
        
        return {
            "is_running": self.is_running,
            "message_count": self.message_count,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "running_time_seconds": running_time.total_seconds() if running_time else 0,
            "messages_per_minute": round(messages_per_minute, 2),
            "handlers_count": len(self.handlers)
        }


# 便捷函数
async def create_simple_text_handler(keywords: List[str], response_callback: Callable):
    """创建简单的文本消息处理器"""
    async def handle_text_message(message: WeChatMessage):
        await response_callback(message)
    
    return TextMessageHandler(keywords=keywords, callback=handle_text_message)


async def create_echo_handler():
    """创建回显处理器（用于调试）"""
    async def echo_message(message: WeChatMessage):
        print(f"[{message.create_datetime}] {message.sender_name}: {message.content}")
    
    return TextMessageHandler(callback=echo_message)
