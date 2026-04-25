"""频道实时广播服务

用于管理频道列表的实时更新，将频道创建、更新、删除事件推送给所有连接的客户端。
"""

import asyncio
from typing import Optional

from pydantic import BaseModel

from nekro_agent.core.logger import get_sub_logger

logger = get_sub_logger("channel_broadcaster")


class ChannelEvent(BaseModel):
    """频道事件"""

    event_type: str  # 'created', 'updated', 'deleted', 'activated', 'deactivated'
    chat_key: str
    channel_name: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None  # 'active', 'observe', 'disabled'


class ChannelSubscription:
    """频道事件订阅句柄"""

    def __init__(self, queue: asyncio.Queue[ChannelEvent], cleanup: callable):
        self._queue = queue
        self._cleanup = cleanup

    async def get(self, timeout: float) -> ChannelEvent:
        """获取下一个事件，超时抛出 asyncio.TimeoutError"""
        return await asyncio.wait_for(self._queue.get(), timeout=timeout)

    def close(self) -> None:
        """关闭订阅，清理资源"""
        self._cleanup()


class ChannelBroadcaster:
    """频道广播器 - 管理全局频道列表的实时更新"""

    def __init__(self):
        """初始化频道广播器"""
        self.queues: list[asyncio.Queue] = []  # 全局订阅队列列表

    def subscribe(self) -> ChannelSubscription:
        """订阅频道更新事件

        Returns:
            ChannelSubscription: 订阅句柄，调用 get(timeout) 获取事件，结束后调用 close()
        """
        queue: asyncio.Queue[ChannelEvent] = asyncio.Queue()
        self.queues.append(queue)
        logger.debug(f"新订阅者加入频道列表, 当前订阅数: {len(self.queues)}")

        def cleanup():
            if queue in self.queues:
                self.queues.remove(queue)
                logger.debug(f"订阅者离开频道列表, 当前订阅数: {len(self.queues)}")

        return ChannelSubscription(queue, cleanup)

    async def publish_update(self, event_type: str, chat_key: str, channel_name: Optional[str] = None, is_active: Optional[bool] = None, status: Optional[str] = None) -> None:
        """发布频道更新事件到所有订阅者

        Args:
            event_type: 事件类型 ('created', 'updated', 'deleted', 'activated', 'deactivated')
            chat_key: 聊天频道唯一标识
            channel_name: 频道名称 (可选)
            is_active: 是否激活 (可选)
        """
        event = ChannelEvent(
            event_type=event_type,
            chat_key=chat_key,
            channel_name=channel_name,
            is_active=is_active,
            status=status,
        )

        logger.debug(f"广播频道事件 {event_type} 到 {len(self.queues)} 个订阅者, chat_key={chat_key}")

        # 异步发送到所有队列，不阻塞
        for queue in self.queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"频道列表的订阅队列已满，跳过事件 {event_type}")

    def get_subscriber_count(self) -> int:
        """获取频道列表的订阅者数量

        Returns:
            int: 订阅者数量
        """
        return len(self.queues)


# 全局频道广播器实例
channel_broadcaster = ChannelBroadcaster()
