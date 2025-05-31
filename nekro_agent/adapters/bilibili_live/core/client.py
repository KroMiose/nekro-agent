import asyncio
import json
from contextlib import asynccontextmanager, suppress
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Coroutine, Dict, List, Optional, Union
from weakref import WeakSet

import aiohttp
from pydantic import BaseModel, Field

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger


class ConnectionState(Enum):
    """WebSocket连接状态枚举"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"
    CLOSED = "closed"


class Danmaku(BaseModel):
    from_live_room: int = Field(
        default=0,
        description="消息来源(房间号)",
    )
    uid: str = Field(default="0", description="消息用户ID")
    username: str = Field(default="unknown", description="用户名")
    text: str = Field(default="", description="弹幕内容")
    time: int = Field(default=0, description="弹幕发送时间")
    url: List[str] = Field(default_factory=list, description="弹幕中的表情图片url列表")
    is_trigget: bool = Field(
        default=True,
        description="是否触发LLM (由ws客户端接收并处理)",
    )
    is_system: bool = Field(
        default=False,
        description="是否作为system身份发送 (由ws客户端接收并处理)",
    )


class WebSocketConnection:
    """WebSocket连接封装类"""

    def __init__(self, session: aiohttp.ClientSession, url: str):
        self.session = session
        self.url = url
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.state = ConnectionState.DISCONNECTED

    async def connect(self) -> None:
        """建立WebSocket连接"""
        if self.state in (ConnectionState.CONNECTED, ConnectionState.CONNECTING):
            return

        self.state = ConnectionState.CONNECTING
        try:
            self.websocket = await self.session.ws_connect(self.url)
            self.state = ConnectionState.CONNECTED
            logger.info(f"WebSocket连接已建立: {self.url}")
        except Exception as e:
            self.state = ConnectionState.DISCONNECTED
            logger.error(f"WebSocket连接失败 {self.url}: {e}")
            raise

    async def close(self) -> None:
        """关闭WebSocket连接"""
        if self.state == ConnectionState.CLOSED:
            return

        self.state = ConnectionState.CLOSING
        try:
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
        except Exception as e:
            logger.warning(f"关闭WebSocket连接时出现警告 {self.url}: {e}")
        finally:
            self.websocket = None
            self.state = ConnectionState.CLOSED
            logger.info(f"WebSocket连接已关闭: {self.url}")

    @property
    def is_connected(self) -> bool:
        """检查连接是否有效"""
        return self.state == ConnectionState.CONNECTED and self.websocket is not None and not self.websocket.closed

    async def send_json(self, data: Dict[str, Any]) -> None:
        """发送JSON数据并监控连接状态"""
        if not self.is_connected:
            raise RuntimeError(f"WebSocket未连接: {self.url}")

        json_data = json.dumps(data, ensure_ascii=False)
        try:
            logger.debug(f"准备发送数据到 {self.url}: {json_data}")
            await self.websocket.send_str(json_data) # type: ignore
            logger.debug(f"数据发送成功到 {self.url}")
            
            # 发送后检查连接状态
            if self.websocket.closed: # type: ignore
                logger.warning(f"发送后检测到连接已关闭: {self.url}")
                self.state = ConnectionState.DISCONNECTED
                
        except ConnectionResetError as e:
            logger.error(f"发送数据时连接被重置 {self.url}: {e}")
            self.state = ConnectionState.DISCONNECTED
            raise
        except aiohttp.ClientConnectionError as e:
            logger.error(f"发送数据时连接错误 {self.url}: {e}")
            self.state = ConnectionState.DISCONNECTED
            raise
        except Exception as e:
            logger.error(f"发送数据时发生未知错误 {self.url}: {e}")
            self.state = ConnectionState.DISCONNECTED
            raise

    async def receive_message(self) -> Optional[aiohttp.WSMessage]:
        """接收原始WebSocket消息 - 增强错误处理"""
        if not self.is_connected:
            raise RuntimeError(f"WebSocket未连接: {self.url}")

        try:
            msg = await self.websocket.receive() # type: ignore
            
            # 详细记录收到的消息类型
            if msg.type == aiohttp.WSMsgType.CLOSE:
                logger.warning(f"收到关闭消息 {self.url}: code={msg.data}, extra={msg.extra}")
                self.state = ConnectionState.DISCONNECTED
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"收到错误消息 {self.url}: {self.websocket.exception()}") # type: ignore
                self.state = ConnectionState.DISCONNECTED
            elif msg.type == aiohttp.WSMsgType.TEXT:
                logger.debug(f"收到文本消息 {self.url}: {msg.data}")
            else:
                logger.debug(f"收到其他类型消息 {self.url}: type={msg.type}")
                
            return msg  # noqa: TRY300
        except Exception as e:
            logger.error(f"接收消息时发生错误 {self.url}: {e}")
            self.state = ConnectionState.DISCONNECTED
            raise

    async def receive_json(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """接收JSON数据 - 仅用于需要超时的场景"""
        if not self.is_connected:
            raise RuntimeError(f"WebSocket未连接: {self.url}")

        try:
            if timeout:
                msg = await asyncio.wait_for(self.websocket.receive(), timeout=timeout) # type: ignore
            else:
                msg = await self.websocket.receive() # type: ignore

            if msg.type == aiohttp.WSMsgType.TEXT:
                return json.loads(msg.data)
            if msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"WebSocket错误: {self.websocket.exception()}") # type: ignore
                raise RuntimeError(f"WebSocket错误: {self.websocket.exception()}") # type: ignore
            if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                logger.warning(f"连接关闭 {self.url}: code={getattr(msg, 'data', 'unknown')}")
                self.state = ConnectionState.DISCONNECTED
                return None
        except json.JSONDecodeError as e:
            logger.error(f"解析JSON数据失败: {e}")
            raise
        except asyncio.TimeoutError:
            logger.debug(f"接收消息超时: {self.url}")
            return None

        return None


class BilibiliWebSocketClient:
    """Bilibili WebSocket客户端 - 调试增强版本"""

    # 类级别的实例跟踪，用于优雅关闭
    _instances: WeakSet = WeakSet()

    def __init__(
        self,
        ws_url: str,
        danmaku_handler: Callable[[Danmaku], Coroutine[Any, Any, None]],
        *,
        reconnect_interval: float = 5.0,
        connection_timeout: float = 30.0,
        response_timeout: float = 10.0,
        max_reconnect_attempts: int = -1,  # -1 表示无限重连
        keep_animate_connection: bool = True,  # 新增：是否保持动画控制连接
    ):
        """初始化WebSocket客户端

        Args:
            ws_url: WebSocket服务器地址
            danmaku_handler: 弹幕消息处理函数
            reconnect_interval: 重连间隔(秒)
            connection_timeout: 连接超时时间(秒)
            response_timeout: 响应超时时间(秒)
            max_reconnect_attempts: 最大重连次数，-1表示无限重连
            keep_animate_connection: 是否保持动画控制连接活跃
        """
        self.ws_url = ws_url
        self.danmaku_handler = danmaku_handler
        self.reconnect_interval = reconnect_interval
        self.connection_timeout = connection_timeout
        self.response_timeout = response_timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self.keep_animate_connection = keep_animate_connection

        # 连接管理
        self._session: Optional[aiohttp.ClientSession] = None
        self._danmaku_conn: Optional[WebSocketConnection] = None
        self._animate_control_conn: Optional[WebSocketConnection] = None

        # 运行状态
        self._is_running = False
        self._reconnect_count = 0
        self._listen_task: Optional[asyncio.Task] = None
        self._animate_monitor_task: Optional[asyncio.Task] = None  # 新增：动画连接监控任务
        self._close_event = asyncio.Event()

        # 注册实例以便优雅关闭
        self._instances.add(self)

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._danmaku_conn is not None and self._danmaku_conn.is_connected

    @property
    def is_animate_connected(self) -> bool:
        """检查动画控制连接是否已连接"""
        return self._animate_control_conn is not None and self._animate_control_conn.is_connected

    @property
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._is_running

    async def _create_session(self) -> aiohttp.ClientSession:
        """创建HTTP会话"""
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30, keepalive_timeout=30, enable_cleanup_closed=True)
        timeout = aiohttp.ClientTimeout(total=self.connection_timeout)
        return aiohttp.ClientSession(connector=connector, timeout=timeout, headers={"User-Agent": "Nekro-Agent/1.0"})

    async def _monitor_animate_connection(self) -> None:
        """监控动画控制连接状态"""
        if not self.keep_animate_connection:
            return
            
        while self._is_running:
            try:
                if self._animate_control_conn and self._animate_control_conn.is_connected:
                    # 发送心跳或保活消息
                    logger.debug("检查动画控制连接状态...")
                    
                    # 可以尝试发送ping消息来保持连接
                    try:
                        # 这里可以根据服务端要求发送特定的保活消息
                        # await self._animate_control_conn.websocket.ping()
                        pass
                    except Exception as e:
                        logger.warning(f"动画控制连接心跳失败: {e}")
                        
                await asyncio.sleep(30)  # 每30秒检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"动画连接监控出错: {e}")
                await asyncio.sleep(5)

    async def connect(self) -> None:
        """连接到WebSocket服务器"""
        if self.is_connected:
            logger.debug("WebSocket已连接，跳过重复连接")
            return

        try:
            # 创建HTTP会话
            if not self._session or self._session.closed:
                self._session = await self._create_session()

            # 创建连接对象
            danmaku_url = f"{self.ws_url}/ws/danmaku"
            animate_control_url = f"{self.ws_url}/ws/animate_control"

            self._danmaku_conn = WebSocketConnection(self._session, danmaku_url)
            self._animate_control_conn = WebSocketConnection(self._session, animate_control_url)

            # 建立连接
            await self._danmaku_conn.connect()
            await self._animate_control_conn.connect()

            logger.success("Bilibili WebSocket连接已建立")
            self._reconnect_count = 0  # 重置重连计数
            
            # 启动动画连接监控
            if self.keep_animate_connection and not self._animate_monitor_task:
                self._animate_monitor_task = asyncio.create_task(self._monitor_animate_connection())

        except Exception as e:
            await self._cleanup_connections()
            logger.error(f"连接Bilibili WebSocket服务器失败: {e}")
            raise

    async def _cleanup_connections(self) -> None:
        """清理连接资源"""
        # 停止动画连接监控
        if self._animate_monitor_task and not self._animate_monitor_task.done():
            self._animate_monitor_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._animate_monitor_task
        self._animate_monitor_task = None
        
        cleanup_tasks = []

        if self._danmaku_conn:
            cleanup_tasks.append(self._danmaku_conn.close())

        if self._animate_control_conn:
            cleanup_tasks.append(self._animate_control_conn.close())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self._danmaku_conn = None
        self._animate_control_conn = None

    async def listen(self) -> None:
        """监听WebSocket消息"""
        if not self.is_connected:
            raise RuntimeError("WebSocket连接未建立")

        self._is_running = True
        logger.info("开始监听Bilibili WebSocket消息...")

        try:
            while self._is_running and self.is_connected:
                try:
                    # 直接接收消息，不使用超时
                    msg = await self._danmaku_conn.receive_message() # type: ignore

                    if msg is None:
                        logger.warning("接收到空消息，连接可能已断开")
                        break

                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            message_data = json.loads(msg.data)
                            await self._handle_message(message_data)
                        except json.JSONDecodeError as e:
                            logger.error(f"解析消息JSON失败: {e}, 原始数据: {msg.data}")
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket错误: {self._danmaku_conn.websocket.exception()}") # type: ignore
                        break
                    elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                        logger.warning("WebSocket连接已关闭")
                        break
                    elif msg.type == aiohttp.WSMsgType.PONG:
                        logger.debug("收到PONG消息")
                    else:
                        logger.debug(f"收到其他类型消息: {msg.type}")

                except asyncio.CancelledError:
                    logger.info("监听任务被取消")
                    break
                except Exception as e:
                    logger.error(f"处理WebSocket消息时发生错误: {e}")
                    if not self.is_connected:
                        break

        except Exception as e:
            logger.error(f"WebSocket监听过程中发生错误: {e}")
        finally:
            self._is_running = False
            logger.info("WebSocket消息监听已停止")

    async def _handle_message(self, message_data: Dict[str, Any]) -> None:
        """处理接收到的消息"""
        try:
            logger.debug(f"接收到Bilibili弹幕数据: {message_data}")

            # 创建Danmaku模型实例
            danmaku = Danmaku.model_validate(message_data)

            # 调用弹幕处理函数
            await self.danmaku_handler(danmaku)

        except Exception as e:
            logger.error(f"处理Bilibili弹幕消息失败: {e}")

    async def start_with_auto_reconnect(self) -> None:
        """启动WebSocket客户端并支持自动重连"""
        self._close_event.clear()

        while not self._close_event.is_set():
            try:
                await self.connect()
                await self.listen()

            except Exception as e:
                logger.error(f"WebSocket连接失败: {e}")

            # 检查是否需要重连
            if self._close_event.is_set():
                break

            if self.max_reconnect_attempts > 0 and self._reconnect_count >= self.max_reconnect_attempts:
                logger.error(f"已达到最大重连次数({self.max_reconnect_attempts})，停止重连")
                break

            self._reconnect_count += 1
            logger.info(f"WebSocket连接断开，{self.reconnect_interval}秒后尝试第{self._reconnect_count}次重连...")

            # 清理连接状态
            await self._cleanup_connections()

            # 等待重连间隔或关闭事件
            try:
                await asyncio.wait_for(self._close_event.wait(), timeout=self.reconnect_interval)
                break  # 收到关闭信号
            except asyncio.TimeoutError:
                continue  # 超时，继续重连

    async def close(self) -> None:
        """关闭WebSocket连接"""
        logger.info("正在关闭Bilibili WebSocket连接...")

        # 设置关闭事件
        self._close_event.set()
        self._is_running = False

        # 等待监听任务完成
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listen_task

        # 清理连接
        await self._cleanup_connections()

        # 关闭会话
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

        logger.info("Bilibili WebSocket连接已关闭")

    async def send_animate_control(self, data: Dict[str, Any], wait_response: bool = False, auto_reconnect: bool = True) -> Optional[Dict[str, Any]]:
        """向动画控制端点发送JSON消息 - 增强版本

        Args:
            data: 要发送的数据字典
            wait_response: 是否等待并返回服务器响应
            auto_reconnect: 如果连接断开是否自动重连

        Returns:
            如果wait_response为True，返回服务器响应的数据字典；否则返回None
        """
        # 检查连接状态，如果需要则重连
        if auto_reconnect and (not self._animate_control_conn or not self._animate_control_conn.is_connected):
            logger.info("动画控制连接未建立，尝试重新连接...")
            try:
                if not self._session or self._session.closed:
                    self._session = await self._create_session()
                    
                animate_control_url = f"{self.ws_url}/ws/animate_control"
                self._animate_control_conn = WebSocketConnection(self._session, animate_control_url)
                await self._animate_control_conn.connect()
            except Exception as e:
                logger.error(f"重新连接动画控制端点失败: {e}")
                return None

        if not self._animate_control_conn or not self._animate_control_conn.is_connected:
            logger.error("动画控制WebSocket未连接")
            return None

        try:
            logger.info(f"准备向animate_control端点发送消息: {json.dumps(data, ensure_ascii=False)}")
            
            # 记录发送前的连接状态
            logger.debug(f"发送前连接状态: {self._animate_control_conn.state}")
            
            await self._animate_control_conn.send_json(data)
            
            # 记录发送后的连接状态
            logger.debug(f"发送后连接状态: {self._animate_control_conn.state}")
            logger.info("消息发送完成")

            if wait_response:
                logger.debug("等待服务器响应...")
                response = await self._animate_control_conn.receive_json(timeout=self.response_timeout)
                if response is not None:
                    logger.debug(f"收到animate_control响应: {response}")
                else:
                    logger.warning("未收到服务器响应或连接已断开")
                return response

            return None  # noqa: TRY300

        except Exception as e:
            logger.error(f"向animate_control端点发送消息失败: {e}")
            # 连接可能已断开，清理状态
            if self._animate_control_conn:
                self._animate_control_conn.state = ConnectionState.DISCONNECTED
            return None

    @classmethod
    async def shutdown_all(cls) -> None:
        """关闭所有实例（用于优雅关闭）"""
        instances = list(cls._instances)
        if instances:
            logger.info(f"正在关闭 {len(instances)} 个WebSocket客户端实例...")
            await asyncio.gather(*[instance.close() for instance in instances], return_exceptions=True)

    @asynccontextmanager
    async def auto_reconnect_context(self) -> AsyncGenerator["BilibiliWebSocketClient", None]:
        """自动重连上下文管理器"""
        try:
            # 启动自动重连任务
            self._listen_task = asyncio.create_task(self.start_with_auto_reconnect())
            yield self
        finally:
            await self.close()