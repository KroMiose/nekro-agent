"""命令输出实时广播服务

用于将命令执行结果推送给 WebUI 客户端，不做持久化。
"""

import asyncio
import time
from typing import AsyncGenerator

from pydantic import BaseModel

from nekro_agent.core.logger import get_sub_logger

logger = get_sub_logger("command_output_broadcaster")


class CommandOutputEvent(BaseModel):
    """命令输出事件"""

    chat_key: str
    command_name: str
    status: str  # CommandResponseStatus.value
    message: str
    timestamp: float


class CommandOutputBroadcaster:
    """命令输出广播器 - 管理每个频道的命令输出订阅"""

    def __init__(self):
        self.queues: dict[str, list[asyncio.Queue[CommandOutputEvent]]] = {}

    async def subscribe(self, chat_key: str) -> AsyncGenerator[CommandOutputEvent, None]:
        """订阅指定频道的命令输出

        Args:
            chat_key: 聊天频道唯一标识

        Yields:
            CommandOutputEvent: 命令输出事件
        """
        if chat_key not in self.queues:
            self.queues[chat_key] = []

        queue: asyncio.Queue[CommandOutputEvent] = asyncio.Queue()
        self.queues[chat_key].append(queue)
        logger.debug(f"命令输出订阅者加入频道 {chat_key}, 当前订阅数: {len(self.queues[chat_key])}")

        try:
            while True:
                event = await queue.get()
                yield event
        except asyncio.CancelledError:
            logger.debug(f"频道 {chat_key} 的命令输出订阅被取消")
            raise
        finally:
            self.queues[chat_key].remove(queue)
            logger.debug(f"命令输出订阅者离开频道 {chat_key}, 当前订阅数: {len(self.queues[chat_key])}")
            if not self.queues[chat_key]:
                del self.queues[chat_key]

    async def publish(self, chat_key: str, command_name: str, status: str, message: str) -> None:
        """发布命令输出事件到指定频道的所有订阅者

        Args:
            chat_key: 聊天频道唯一标识
            command_name: 命令名称
            status: 命令响应状态
            message: 输出消息
        """
        if chat_key not in self.queues:
            return

        event = CommandOutputEvent(
            chat_key=chat_key,
            command_name=command_name,
            status=status,
            message=message,
            timestamp=time.time(),
        )

        logger.debug(f"广播命令输出到频道 {chat_key}, 订阅数: {len(self.queues[chat_key])}")

        for queue in self.queues[chat_key]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"频道 {chat_key} 的命令输出订阅队列已满，跳过此事件")


# 全局命令输出广播器实例
command_output_broadcaster = CommandOutputBroadcaster()
