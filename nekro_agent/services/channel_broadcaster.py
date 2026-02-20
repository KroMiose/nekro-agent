"""频道实时广播服务

用于管理频道列表的实时更新，将频道创建、更新、删除事件推送给所有连接的客户端。
"""

import asyncio
from typing import AsyncGenerator, Optional

from pydantic import BaseModel

from nekro_agent.core.logger import get_sub_logger

logger = get_sub_logger("channel_broadcaster")


class ChannelEvent(BaseModel):
    """频道事件"""

    event_type: str  # 'created', 'updated', 'deleted', 'activated', 'deactivated'
    chat_key: str
    channel_name: Optional[str] = None
    is_active: Optional[bool] = None


class ChannelBroadcaster:
    """频道广播器 - 管理全局频道列表的实时更新"""

    def __init__(self):
        """初始化频道广播器"""
        self.queues: list[asyncio.Queue] = []  # 全局订阅队列列表

    async def subscribe(self) -> AsyncGenerator[ChannelEvent, None]:
        """订阅频道更新事件

        Yields:
            ChannelEvent: 频道事件

        Raises:
            Exception: 当订阅被取消时
        """
        queue: asyncio.Queue = asyncio.Queue()
        self.queues.append(queue)
        logger.debug(f"新订阅者加入频道列表, 当前订阅数: {len(self.queues)}")

        try:
            while True:
                event = await queue.get()
                yield event
        except asyncio.CancelledError:
            logger.debug("频道列表订阅被取消")
            raise
        finally:
            self.queues.remove(queue)
            logger.debug(f"订阅者离开频道列表, 当前订阅数: {len(self.queues)}")

    async def publish_update(self, event_type: str, chat_key: str, channel_name: Optional[str] = None, is_active: Optional[bool] = None) -> None:
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
