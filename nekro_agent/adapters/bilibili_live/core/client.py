import asyncio
import json
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

import aiohttp
from pydantic import BaseModel, Field

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger


class Danmaku(BaseModel):
    from_live_room: int = Field(
        default=0, description="消息来源(房间号)",
    )
    uid: str = Field(default="0", description="消息用户ID")
    username: str = Field(default="unknown", description="用户名")
    text: str = Field(default="", description="弹幕内容")
    time: int = Field(default=0, description="弹幕发送时间")
    url: List[str] = Field(default_factory=list, description="弹幕中的表情图片url列表")
    is_trigget: bool = Field(
        default=True, description="是否触发LLM (由ws客户端接收并处理)",
    )
    is_system: bool = Field(
        default=False, description="是否作为system身份发送 (由ws客户端接收并处理)",
    )

class BilibiliWebSocketClient:
    """Bilibili WebSocket客户端"""
    
    def __init__(self, ws_url: str, danmaku_handler: Callable[[Danmaku], Coroutine[Any, Any, None]]):
        """初始化WebSocket客户端
        
        Args:
            ws_url: WebSocket服务器地址
            danmaku_handler: 弹幕消息处理函数
        """
        self.ws_url = ws_url
        self.danmaku_handler = danmaku_handler
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.animate_control_ws: Optional[aiohttp.ClientWebSocketResponse] = None  # 新增：动画控制连接
        self.is_running = False
        self.reconnect_interval = 5  # 重连间隔(秒)
        
    async def connect(self) -> None:
        """连接到WebSocket服务器"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            # 连接弹幕WebSocket
            danmaku_url = f"{self.ws_url}/ws/danmaku"
            logger.info(f"正在连接到Bilibili WebSocket服务器: {danmaku_url}")
            self.websocket = await self.session.ws_connect(danmaku_url)
            logger.success(f"已连接到Bilibili WebSocket服务器: {danmaku_url}")
            animate_control_url = f"{self.ws_url}/ws/animate_control"
            self.animate_control_ws = await self.session.ws_connect(animate_control_url)
            
        except Exception as e:
            logger.error(f"连接Bilibili WebSocket服务器失败: {e}")
            raise
            
    async def listen(self) -> None:
        """监听WebSocket消息"""
        if not self.websocket:
            raise RuntimeError("WebSocket连接未建立")
            
        self.is_running = True
        logger.info("开始监听Bilibili WebSocket消息...")
        
        try:
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket错误: {self.websocket.exception()}")
                    break
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                    logger.warning("WebSocket连接已关闭")
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket监听过程中发生错误: {e}")
        finally:
            self.is_running = False
            
    async def _handle_message(self, message_data: str) -> None:
        """处理接收到的消息"""
        try:
            # 解析JSON消息
            data = json.loads(message_data)
            logger.debug(f"接收到Bilibili弹幕数据: {data}")
            
            # 创建Danmaku模型实例
            danmaku = Danmaku.model_validate(data)
            
            # 调用弹幕处理函数
            await self.danmaku_handler(danmaku)
            
        except json.JSONDecodeError as e:
            logger.error(f"解析Bilibili消息JSON失败: {e}, 原始数据: {message_data}")
        except Exception as e:
            logger.error(f"处理Bilibili弹幕消息失败: {e}")
            
    async def start_with_auto_reconnect(self) -> None:
        """启动WebSocket客户端并支持自动重连"""
        while True:
            try:
                await self.connect()
                await self.listen()
            except Exception as e:
                logger.error(f"WebSocket连接失败: {e}")
                
            if not self.is_running:
                logger.info(f"WebSocket连接断开，{self.reconnect_interval}秒后尝试重连...")
                await asyncio.sleep(self.reconnect_interval)
                # 重连时需要重置连接状态
                await self._cleanup_connections()
            else:
                break
    
    async def _cleanup_connections(self) -> None:
        """清理连接状态"""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        if self.animate_control_ws and not self.animate_control_ws.closed:
            await self.animate_control_ws.close()
        self.websocket = None
        self.animate_control_ws = None
                
    async def close(self) -> None:
        """关闭WebSocket连接"""
        self.is_running = False
        
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
            
        if self.animate_control_ws and not self.animate_control_ws.closed:
            await self.animate_control_ws.close()
            
        if self.session and not self.session.closed:
            await self.session.close()
            
        logger.info("Bilibili WebSocket连接已关闭")
        
    async def send_animate_control(self, data: Dict[str, Any]) -> None:
        """向动画控制端点发送JSON消息（使用长连接）
        
        Args:
            data: 要发送的数据字典，将被转换为JSON格式
        """
        try:
            # 检查连接状态，如果连接已断开则重新连接
            if self.animate_control_ws:
                # 发送消息
                json_data = json.dumps(data)
                await self.animate_control_ws.send_str(json_data)
                logger.info(f"已向animate_control端点发送消息: {json_data}")
                
        except Exception as e:
            logger.error(f"向animate_control端点发送消息失败: {e}")
            self.animate_control_ws = None
            animate_control_url = f"{self.ws_url}/ws/animate_control"
            if self.session:
                self.animate_control_ws = await self.session.ws_connect(animate_control_url)