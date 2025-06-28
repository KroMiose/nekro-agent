import asyncio
import time
from datetime import datetime
from typing import Awaitable, Callable, Dict, List, Optional

from nekro_agent.core import logger
from nekro_agent.services.message_service import message_service


class TimerTask:
    """定时任务类"""

    def __init__(self, chat_key: str, trigger_time: int, event_desc: str):
        self.chat_key = chat_key
        self.trigger_time = trigger_time
        self.event_desc = event_desc
        self.task: Optional[asyncio.Task] = None
        self.temporary: bool = False  # 是否为临时定时器
        self.callback: Optional[Callable[[], Awaitable[None]]] = None  # 回调函数


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

    async def set_timer(
        self,
        chat_key: str,
        trigger_time: int,
        event_desc: str,
        silent: bool = False,
        override: bool = False,
        temporary: Optional[bool] = None,
        callback: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> bool:
        """设置定时器

        Args:
            chat_key (str): 会话标识
            trigger_time (int): 触发时间戳。如果为0则立即触发会话;如果小于0则清空当前会话的定时器。
            event_desc (str): 详细事件描述
            silent (bool, optional): 是否静默设置. Defaults to False.
            override (bool): 是否为临时定时器，每个会话只能存在一个临时定时器，新设置的临时定时器会自动覆盖同一会话中已存在的临时定时器。
            temporary (Optional[bool], optional): 清除定时器时的类型筛选。None表示清除所有定时器，True只清除临时定时器，False只清除非临时定时器。仅在 trigger_time < 0 时生效。
            callback (Optional[Callable[[], Awaitable[None]]], optional): 定时器触发时执行的回调函数. Defaults to None.

        Returns:
            bool: 是否设置成功
        """
        # 如果触发时间小于0，清空当前会话的定时器
        if trigger_time < 0:
            if chat_key in self.tasks:
                if temporary is None:
                    # 清空所有定时器
                    del self.tasks[chat_key]
                else:
                    # 根据 temporary 参数筛选要保留的定时器
                    self.tasks[chat_key] = [task for task in self.tasks[chat_key] if task.temporary != temporary]
                    if not self.tasks[chat_key]:
                        del self.tasks[chat_key]
                if not silent:
                    logger.info(
                        f"已清空会话 {chat_key} 的{'所有' if temporary is None else '临时' if temporary else '非临时'}定时器",
                    )
            return True

        # 如果触发时间为0，立即触发会话
        if trigger_time == 0:
            await message_service.schedule_agent_task(chat_key)
            return True

        # 检查触发时间是否已过
        if trigger_time <= int(time.time()):
            return False

        if chat_key not in self.tasks:
            self.tasks[chat_key] = []
        elif override:
            # 如果是临时定时器，移除之前的临时定时器
            self.tasks[chat_key] = [task for task in self.tasks[chat_key] if not task.temporary]

        # 创建定时任务
        task = TimerTask(chat_key, trigger_time, event_desc)
        task.temporary = override
        task.callback = callback
        self.tasks[chat_key].append(task)
        if not silent:
            logger.info(f"定时器设置成功: {chat_key} | 触发时间: {datetime.fromtimestamp(trigger_time)}")
        return True

    def get_timers(self, chat_key: str) -> List[TimerTask]:
        """获取指定会话的所有未触发定时器

        Args:
            chat_key (str): 会话标识

        Returns:
            List[TimerTask]: 定时器任务列表
        """
        return self.tasks.get(chat_key, [])

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
                        # 执行回调函数或发送系统消息
                        if task.callback:
                            await task.callback()
                        elif task.event_desc:
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
