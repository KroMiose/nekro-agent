"""
SSE 客户端管理器
==============

负责管理客户端连接、心跳机制、频道订阅和事件分发。

主要功能:
1. 客户端注册与连接
2. 频道订阅管理
3. 事件队列和分发
4. 连接状态检测和清理
"""

import asyncio
import contextlib
import time
import uuid
from datetime import datetime, timedelta
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Union,
)

from fastapi import Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from nekro_agent.adapters.sse.sdk.models import (
    ConnectedData,
    Event,
    HeartbeatData,
)
from nekro_agent.core.logger import logger


class SseClient:
    """SSE 客户端

    表示单个连接到服务端的客户端实例
    """

    def __init__(self, client_id: str, name: str = "", platform: str = "unknown"):
        """初始化客户端

        Args:
            client_id: 客户端唯一标识
            name: 客户端名称
            platform: 平台标识，例如 'wechat', 'telegram' 等
        """
        self.client_id = client_id
        self.name = name
        self.platform = platform
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.subscribed_channels: Set[str] = set()  # 已订阅的频道(channel_id)
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.is_alive = True
        self.handlers: Dict[str, Callable[[BaseModel], Awaitable[bool]]] = {}

    def update_heartbeat(self) -> None:
        """更新心跳时间"""
        self.last_heartbeat = datetime.now()

    def is_expired(self, timeout_seconds: int = 60) -> bool:
        """检查客户端是否超时未响应

        Args:
            timeout_seconds: 超时时间（秒）

        Returns:
            bool: 是否已超时
        """
        return (datetime.now() - self.last_heartbeat).total_seconds() > timeout_seconds

    async def send_event(self, event: Event) -> None:
        """发送事件到客户端的事件队列
        Args:
            event: Event[Pydantic模型]
        """
        if not self.is_alive:
            return
        await self.event_queue.put(event)

    def has_events(self) -> bool:
        """检查是否有待处理的事件"""
        return not self.event_queue.empty()

    def pop_event(self) -> Dict[str, Any]:
        """获取下一个待处理事件(非阻塞)"""
        if self.event_queue.empty():
            return {}

        try:
            return self.event_queue.get_nowait()
        except asyncio.QueueEmpty:
            return {}

    def add_channel(self, channel_id: str) -> None:
        """添加订阅的频道

        Args:
            channel_id: 聊天频道标识
        """
        self.subscribed_channels.add(channel_id)

    def remove_channel(self, channel_id: str) -> None:
        """移除订阅的频道

        Args:
            channel_id: 聊天频道标识
        """
        self.subscribed_channels.discard(channel_id)

    def register_handler(self, request_id: str, handler: Callable[[BaseModel], Awaitable[bool]]) -> None:
        """注册请求处理器

        Args:
            request_id: 请求ID
            handler: 处理函数，接收响应数据，返回是否处理成功
        """
        handler_name = f"_request_{request_id}"
        self.handlers[handler_name] = handler

    async def handle_response(self, response_data: BaseModel) -> bool:
        """处理客户端响应

        Args:
            response_data: 响应数据

        Returns:
            bool: 是否处理成功
        """
        request_id = getattr(response_data, "requestId", None) or getattr(response_data, "request_id", None)
        if not request_id:
            logger.error(f"客户端 {self.client_id} 响应缺少 requestId")
            return False

        handler_name = f"_request_{request_id}"
        if handler_name in self.handlers:
            handler = self.handlers.pop(handler_name)
            return await handler(response_data)

        logger.warning(f"客户端 {self.client_id} 响应 {request_id} 没有对应的处理器")
        return False


class SseClientManager:
    """SSE 客户端管理器

    负责管理所有连接的客户端
    """

    def __init__(self):
        """初始化客户端管理器"""
        self.clients: Dict[str, SseClient] = {}
        self.cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动客户端管理器"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("SSE 客户端管理器已启动")

    async def stop(self) -> None:
        """停止客户端管理器"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.cleanup_task
            self.cleanup_task = None
            logger.info("SSE 客户端管理器已停止")

    async def _cleanup_loop(self) -> None:
        """定期清理失效客户端"""
        while True:
            try:
                await asyncio.sleep(30)
                expired_clients = []

                for client_id, client in self.clients.items():
                    if client.is_expired():
                        expired_clients.append(client_id)

                for client_id in expired_clients:
                    logger.info(f"SSE 客户端 {client_id} 已超时，移除连接")
                    client = self.clients.pop(client_id, None)
                    if client:
                        client.is_alive = False

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SSE 客户端清理异常: {e}")

    def register_client(self, name: str = "", platform: str = "unknown") -> SseClient:
        """注册新客户端

        Args:
            name: 客户端名称
            platform: 平台标识

        Returns:
            SseClient: 新注册的客户端
        """
        client_id = str(uuid.uuid4())
        client = SseClient(client_id, name, platform)
        self.clients[client_id] = client
        logger.info(f"SSE 客户端 {client_id} ({name}/{platform}) 已连接")
        return client

    def unregister_client(self, client_id: str) -> None:
        """注销客户端

        Args:
            client_id: 客户端ID
        """
        client = self.clients.pop(client_id, None)
        if client:
            client.is_alive = False
            logger.info(f"SSE 客户端 {client_id} ({client.name}) 已断开连接")

    def get_client(self, client_id: str) -> Optional[SseClient]:
        """获取指定ID的客户端

        Args:
            client_id: 客户端ID

        Returns:
            Optional[SseClient]: 客户端对象，如果不存在返回None
        """
        return self.clients.get(client_id)

    def get_client_by_name(self, name: str) -> Optional[SseClient]:
        """根据名称获取客户端

        Args:
            name: 客户端名称

        Returns:
            Optional[SseClient]: 客户端对象，如果不存在返回None
        """
        for client in self.clients.values():
            if client.name == name:
                return client
        return None

    def get_clients_by_channel(self, channel_id: str) -> List[SseClient]:
        """获取订阅了指定频道的客户端列表

        Args:
            channel_id: 聊天频道标识

        Returns:
            List[SseClient]: 客户端列表
        """
        return [client for client in self.clients.values() if channel_id in client.subscribed_channels]

    def get_clients_by_platform(self, platform: str) -> List[SseClient]:
        """获取指定平台的客户端列表

        Args:
            platform: 平台标识

        Returns:
            List[SseClient]: 客户端列表
        """
        return [client for client in self.clients.values() if client.platform == platform]

    async def broadcast_to_channel(self, channel_id: str, event_type: str, data: BaseModel) -> None:
        """向指定频道的所有客户端广播事件

        Args:
            channel_id: 聊天频道标识
            event_type: 事件类型
            data: 事件数据
        """
        clients = self.get_clients_by_channel(channel_id)
        for client in clients:
            await client.send_event(Event(event=event_type, data=data))

    async def broadcast_to_all(self, event_type: str, data: BaseModel) -> None:
        """向所有客户端广播事件

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        for client in self.clients.values():
            await client.send_event(Event(event=event_type, data=data))


# SSE 事件流处理函数
async def sse_stream(request: Request, client: SseClient) -> AsyncGenerator[Dict[str, Any], None]:
    """SSE 事件流生成器

    处理SSE连接的事件流生成

    Args:
        request: 请求对象
        client: 客户端实例

    Yields:
        Dict[str, Any]: 事件数据，包含event和data字段
    """
    try:
        # 发送连接成功事件
        connected_event = Event[ConnectedData](
            event="connected", data=ConnectedData(client_id=client.client_id, timestamp=int(time.time())),
        )
        yield connected_event.to_sse_format()

        # 心跳计时器
        heartbeat_timer = 0

        while client.is_alive:
            if time.time() - heartbeat_timer >= 5:
                heartbeat_event = Event[HeartbeatData](
                    event="heartbeat", data=HeartbeatData(timestamp=int(time.time())),
                )
                yield heartbeat_event.to_sse_format()
                heartbeat_timer = time.time()
                client.update_heartbeat()

            try:
                event: Event = await asyncio.wait_for(client.event_queue.get(), timeout=1.0)
                yield event.to_sse_format()
                client.event_queue.task_done()
            except asyncio.TimeoutError:
                pass

            if await request.is_disconnected():
                logger.info(f"SSE客户端 {client.client_id} 连接已断开")
                break

    except asyncio.CancelledError:
        logger.info(f"SSE客户端 {client.client_id} SSE流已取消")
    except Exception as e:
        logger.error(f"SSE客户端 {client.client_id} SSE流异常: {e}")
    finally:
        client.is_alive = False
    logger.info(f"SSE客户端 {client.client_id} SSE流已结束")


def create_sse_response(request: Request, client: Union[SseClient, str], manager: SseClientManager) -> EventSourceResponse:
    """创建SSE响应

    Args:
        request: 请求对象
        client: 客户端实例或客户端名称
        manager: 客户端管理器

    Returns:
        EventSourceResponse: SSE响应对象
    """
    # 如果是字符串，则创建/获取客户端
    if isinstance(client, str):
        # 尝试获取已存在的客户端
        existing_client = manager.get_client_by_name(client)
        client = existing_client if existing_client else manager.register_client(client)

    # 返回SSE响应
    return EventSourceResponse(sse_stream(request, client))
