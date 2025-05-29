import asyncio
import contextlib
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union

from fastapi import Request
from sse_starlette.sse import EventSourceResponse

from nekro_agent.core.logger import logger


class ClientInfo:
    """客户端信息"""

    def __init__(self, client_id: str, name: str = "", platform: str = "unknown"):
        self.client_id = client_id
        self.name = name
        self.platform = platform  # 客户端平台标识
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.channels: Set[str] = set()  # 客户端关联的聊天频道
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.is_alive = True

    def update_heartbeat(self):
        """更新心跳时间"""
        self.last_heartbeat = datetime.now()

    def is_expired(self, timeout_seconds: int = 60) -> bool:
        """检查客户端是否超时"""
        return (datetime.now() - self.last_heartbeat).total_seconds() > timeout_seconds

    async def send_event(self, event_type: str, data: dict):
        """发送事件到客户端"""
        await self.event_queue.put({"type": event_type, "data": data})

    def add_channel(self, chat_key: str):
        """添加客户端关联的聊天频道"""
        self.channels.add(chat_key)

    def remove_channel(self, chat_key: str):
        """移除客户端关联的聊天频道"""
        self.channels.discard(chat_key)


class ClientManager:
    """客户端管理器"""

    def __init__(self):
        self.clients: Dict[str, ClientInfo] = {}
        self.cleanup_task = None

    async def start(self):
        """启动客户端管理器"""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("SSE 客户端管理器已启动")

    async def stop(self):
        """停止客户端管理器"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.cleanup_task
            self.cleanup_task = None
            logger.info("SSE 客户端管理器已停止")

    async def _cleanup_loop(self):
        """定期清理失效客户端"""
        while True:
            try:
                await asyncio.sleep(30)
                expired_clients = []

                for client_id, client in self.clients.items():
                    if client.is_expired():
                        expired_clients.append(client_id)

                for client_id in expired_clients:
                    logger.info(f"SSE 客户端 {client_id} 心跳超时，移除连接")
                    client = self.clients.pop(client_id, None)
                    if client:
                        client.is_alive = False

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SSE 客户端清理异常: {e}")

    def register_client(self, name: str = "", platform: str = "unknown") -> ClientInfo:
        """注册新客户端

        Args:
            name: 客户端名称
            platform: 平台标识

        Returns:
            ClientInfo: 客户端信息
        """
        client_id = str(uuid.uuid4())
        client = ClientInfo(client_id, name, platform)
        self.clients[client_id] = client
        logger.info(f"SSE 客户端 {client_id} ({name}/{platform}) 已连接")
        return client

    def unregister_client(self, client_id: str):
        """注销客户端"""
        client = self.clients.pop(client_id, None)
        if client:
            client.is_alive = False
            logger.info(f"SSE 客户端 {client_id} ({client.name}) 已断开连接")

    def get_client(self, client_id: str) -> Optional[ClientInfo]:
        """获取客户端信息"""
        return self.clients.get(client_id)

    def get_clients_by_channel(self, chat_key: str) -> List[ClientInfo]:
        """获取指定频道的所有客户端"""
        return [client for client in self.clients.values() if chat_key in client.channels]

    async def broadcast_to_channel(self, chat_key: str, event_type: str, data: dict):
        """向指定频道的所有客户端广播事件"""
        clients = self.get_clients_by_channel(chat_key)
        for client in clients:
            await client.send_event(event_type, data)

    async def broadcast_to_all(self, event_type: str, data: dict):
        """向所有客户端广播事件"""
        for client in self.clients.values():
            await client.send_event(event_type, data)

    def get_client_by_name(self, name: str) -> Optional[ClientInfo]:
        """根据名称获取客户端信息

        Args:
            name: 客户端名称

        Returns:
            Optional[ClientInfo]: 客户端信息，如果不存在则返回None
        """
        for client in self.clients.values():
            if client.name == name:
                return client
        return None


# 全局客户端管理器实例
client_manager = ClientManager()


async def sse_stream(request: Request, client: ClientInfo):
    """SSE 事件流生成器"""
    try:
        # 发送连接成功事件
        yield {"event": "connected", "data": {"client_id": client.client_id, "timestamp": int(time.time())}}

        # 心跳计时器
        heartbeat_timer = 0

        while client.is_alive:
            # 每5秒发送一次心跳
            if time.time() - heartbeat_timer >= 5:
                yield {"event": "heartbeat", "data": {"timestamp": int(time.time())}}
                heartbeat_timer = time.time()
                client.update_heartbeat()

            # 尝试从队列获取事件，最多等待1秒
            try:
                event = await asyncio.wait_for(client.event_queue.get(), timeout=1.0)
                yield {"event": event["type"], "data": event["data"]}
                client.event_queue.task_done()
            except asyncio.TimeoutError:
                pass  # 无新事件，继续循环

            # 检查客户端请求是否已断开
            if await request.is_disconnected():
                logger.info(f"SSE 客户端 {client.client_id} 连接已断开")
                break

    except asyncio.CancelledError:
        logger.info(f"SSE 客户端 {client.client_id} SSE流已取消")
    except Exception as e:
        logger.error(f"SSE 客户端 {client.client_id} SSE流异常: {e}")
    finally:
        # 确保客户端被正确注销
        client_manager.unregister_client(client.client_id)

    logger.info(f"SSE 客户端 {client.client_id} SSE流已结束")


def create_sse_response(request: Request, client: Union[ClientInfo, str]) -> EventSourceResponse:
    """创建SSE响应

    Args:
        request: 请求对象
        client: 客户端实例或客户端名称
    """
    # 如果是字符串，则创建新客户端
    if isinstance(client, str):
        client = client_manager.register_client(client)

    return EventSourceResponse(sse_stream(request, client))
