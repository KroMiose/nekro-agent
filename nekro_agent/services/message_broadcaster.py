"""消息实时广播服务

用于管理每个聊天频道的消息订阅，将新消息推送给所有连接的客户端。
"""

import asyncio
from typing import Dict

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import ChatMessage

logger = get_sub_logger("message_broadcaster")


class MessageSubscription:
    """消息订阅句柄，封装队列操作，避免 async generator + wait_for 的兼容性问题"""

    def __init__(self, queue: asyncio.Queue[ChatMessage], cleanup: callable):
        self._queue = queue
        self._cleanup = cleanup

    async def get(self, timeout: float) -> ChatMessage:
        """获取下一条消息，超时抛出 asyncio.TimeoutError"""
        return await asyncio.wait_for(self._queue.get(), timeout=timeout)

    def close(self) -> None:
        """关闭订阅，清理资源"""
        self._cleanup()


class MessageBroadcaster:
    """消息广播器 - 管理每个频道的消息订阅"""

    def __init__(self):
        """初始化消息广播器"""
        self.queues: Dict[str, list[asyncio.Queue]] = {}  # per chat_key: list of queues

    def subscribe(self, chat_key: str) -> MessageSubscription:
        """订阅指定频道的消息

        Args:
            chat_key: 聊天频道唯一标识

        Returns:
            MessageSubscription: 订阅句柄，调用 get(timeout) 获取消息，结束后调用 close()
        """
        if chat_key not in self.queues:
            self.queues[chat_key] = []

        queue: asyncio.Queue[ChatMessage] = asyncio.Queue()
        self.queues[chat_key].append(queue)
        logger.debug(f"新订阅者加入频道 {chat_key}, 当前订阅数: {len(self.queues[chat_key])}")

        def cleanup():
            if chat_key in self.queues and queue in self.queues[chat_key]:
                self.queues[chat_key].remove(queue)
                logger.debug(f"订阅者离开频道 {chat_key}, 当前订阅数: {len(self.queues[chat_key])}")
                if not self.queues[chat_key]:
                    del self.queues[chat_key]

        return MessageSubscription(queue, cleanup)

    async def publish(self, chat_key: str, message: ChatMessage) -> None:
        """发布消息到指定频道的所有订阅者

        Args:
            chat_key: 聊天频道唯一标识
            message: 要发布的消息
        """
        if chat_key not in self.queues:
            return

        logger.debug(f"广播消息到频道 {chat_key}, 订阅数: {len(self.queues[chat_key])}")

        # 异步发送到所有队列，不阻塞
        for queue in self.queues[chat_key]:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning(f"频道 {chat_key} 的订阅队列已满，跳过此消息")

    def get_subscriber_count(self, chat_key: str) -> int:
        """获取指定频道的订阅者数量

        Args:
            chat_key: 聊天频道唯一标识

        Returns:
            int: 订阅者数量
        """
        return len(self.queues.get(chat_key, []))

    def get_all_subscribed_channels(self) -> list[str]:
        """获取所有有订阅者的频道

        Returns:
            list[str]: 频道 chat_key 列表
        """
        return list(self.queues.keys())


# 全局消息广播器实例
message_broadcaster = MessageBroadcaster()
