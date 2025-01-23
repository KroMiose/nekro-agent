import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional

from nekro_agent.core import logger
from nekro_agent.services.message.message_service import message_service


class TimerTask:
    """定时任务类"""

    def __init__(self, chat_key: str, trigger_time: int, event_desc: str):
        self.chat_key = chat_key
        self.trigger_time = trigger_time
        self.event_desc = event_desc
        self.task: Optional[asyncio.Task] = None


class TimerService:
    """定时器服务类"""

    def __init__(self):
        self.tasks: Dict[str, List[TimerTask]] = {}  # chat_key -> [TimerTask]
        self.running = False

    async def start(self):
        """启动定时器服务"""
        if self.running:
            return
        self.running = True
        asyncio.create_task(self._timer_loop())
        logger.info("Timer service started")

    async def stop(self):
        """停止定时器服务"""
        self.running = False
        # 取消所有任务
        for tasks in self.tasks.values():
            for task in tasks:
                if task.task and not task.task.done():
                    task.task.cancel()
        self.tasks.clear()
        logger.info("Timer service stopped")

    async def set_timer(self, chat_key: str, trigger_time: int, event_desc: str, silent: bool = False) -> bool:
        """设置定时器

        Args:
            chat_key (str): 会话标识
            trigger_time (int): 触发时间戳，如果为0则立即触发
            event_desc (str): 事件描述

        Returns:
            bool: 是否设置成功
        """
        # 如果触发时间为0，立即触发会话
        if trigger_time == 0:
            await message_service.schedule_agent_task(chat_key)
            return True

        # 检查触发时间是否已过
        if trigger_time <= int(time.time()):
            return False

        if chat_key not in self.tasks:
            self.tasks[chat_key] = []

        # 创建定时任务
        task = TimerTask(chat_key, trigger_time, event_desc)
        self.tasks[chat_key].append(task)
        if not silent:
            logger.info(f"定时器设置成功: {chat_key} | 触发时间: {datetime.fromtimestamp(trigger_time)}")
        return True

    async def _timer_loop(self):
        """定时器循环"""
        while self.running:
            current_time = int(time.time())

            # 检查所有任务
            for chat_key, tasks in list(self.tasks.items()):
                triggered_tasks = []
                for task in tasks:
                    if task.trigger_time <= current_time:
                        triggered_tasks.append(task)
                        # 发送系统消息并触发 agent
                        if task.event_desc:
                            system_message = f"⏰ 定时提醒：{task.event_desc}"
                            await message_service.push_system_message(
                                chat_key=task.chat_key,
                                agent_messages=system_message,
                                trigger_agent=True,
                            )
                        else:
                            await message_service.schedule_agent_task(task.chat_key)

                # 移除已触发的任务
                self.tasks[chat_key] = [t for t in tasks if t not in triggered_tasks]
                if not self.tasks[chat_key]:
                    del self.tasks[chat_key]

            await asyncio.sleep(1)  # 每秒检查一次


# 全局定时器服务实例
timer_service = TimerService()
