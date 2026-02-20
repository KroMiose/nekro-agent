"""消息实时广播服务

用于管理每个聊天频道的消息订阅，将新消息推送给所有连接的客户端。
"""

import asyncio
from typing import AsyncGenerator, Dict

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import ChatMessage

logger = get_sub_logger("message_broadcaster")


class MessageBroadcaster:
    """消息广播器 - 管理每个频道的消息订阅"""

    def __init__(self):
        """初始化消息广播器"""
        self.queues: Dict[str, list[asyncio.Queue]] = {}  # per chat_key: list of queues

    async def subscribe(self, chat_key: str) -> AsyncGenerator[ChatMessage, None]:
        """订阅指定频道的消息

        Args:
            chat_key: 聊天频道唯一标识

        Yields:
            ChatMessage: 新消息

        Raises:
            Exception: 当订阅被取消时
        """
        if chat_key not in self.queues:
            self.queues[chat_key] = []

        queue: asyncio.Queue = asyncio.Queue()
        self.queues[chat_key].append(queue)
        logger.debug(f"新订阅者加入频道 {chat_key}, 当前订阅数: {len(self.queues[chat_key])}")

        try:
            while True:
                message = await queue.get()
                yield message
        except asyncio.CancelledError:
            logger.debug(f"频道 {chat_key} 的订阅被取消")
            raise
        finally:
            self.queues[chat_key].remove(queue)
            logger.debug(f"订阅者离开频道 {chat_key}, 当前订阅数: {len(self.queues[chat_key])}")
            # 如果频道没有订阅者，清理该频道的队列列表
            if not self.queues[chat_key]:
                del self.queues[chat_key]

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
