import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

import aiofiles

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import TIMER_ONE_SHOT_PERSIST_PATH
from nekro_agent.services.message_service import message_service

logger = get_sub_logger("timer")


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

    _PERSIST_VERSION = 1
    _MISFIRE_GRACE_SECONDS = 300

    def __init__(self):
        self.tasks: Dict[str, List[TimerTask]] = {}  # chat_key -> [TimerTask]
        self.running = False
        self._persist_lock = asyncio.Lock()

    def _persist_path(self) -> Path:
        path = Path(TIMER_ONE_SHOT_PERSIST_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def _load_persisted_tasks(self) -> None:
        """从数据目录恢复一次性/临时定时器。

        仅恢复 callback 为空的任务（即普通提醒/自唤醒），避免把“节日提醒”等带回调的系统任务写死到磁盘里，
        从而保证用户更新预设节日配置后，重启即可按新逻辑重新计算并同步。
        """
        path = self._persist_path()
        if not path.exists():
            return
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                raw = await f.read()
            data = json.loads(raw)
        except Exception:
            logger.exception(f"加载持久化定时器失败: path={path}")
            return

        if not isinstance(data, dict) or data.get("version") != self._PERSIST_VERSION:
            logger.error(f"加载持久化定时器失败: version 不匹配: {data!r}")
            return

        items = data.get("tasks")
        if not isinstance(items, list):
            return

        now = int(time.time())
        restored = 0
        dropped = 0
        triggered = 0

        for item in items:
            if not isinstance(item, dict):
                continue
            chat_key = item.get("chat_key")
            trigger_time = item.get("trigger_time")
            event_desc = item.get("event_desc")
            temporary = item.get("temporary", False)

            if not isinstance(chat_key, str) or not isinstance(trigger_time, int) or not isinstance(event_desc, str):
                continue

            # 已过期：在宽限期内补发一次，否则丢弃
            if trigger_time <= now:
                lag = now - trigger_time
                if 0 <= lag <= self._MISFIRE_GRACE_SECONDS and event_desc:
                    try:
                        await message_service.push_system_message(
                            chat_key=chat_key,
                            agent_messages=f"⏰ 定时提醒（补发）：{event_desc}",
                            trigger_agent=True,
                        )
                        triggered += 1
                    except Exception:
                        logger.exception(f"补发持久化定时器失败: chat_key={chat_key}")
                else:
                    dropped += 1
                continue

            task = TimerTask(chat_key, trigger_time, event_desc)
            task.temporary = bool(temporary)
            task.callback = None
            self.tasks.setdefault(chat_key, []).append(task)
            restored += 1

        logger.info(
            f"持久化定时器恢复完成: restored={restored}, triggered={triggered}, dropped={dropped}",
        )

    async def _persist_tasks(self) -> None:
        """将当前一次性/临时定时器持久化到数据目录。

        仅持久化 callback 为空的任务，避免把系统回调任务写死到磁盘。
        """
        async with self._persist_lock:
            tasks_dump: list[dict] = []
            for chat_key, tasks in self.tasks.items():
                for t in tasks:
                    if t.callback is not None:
                        continue
                    tasks_dump.append(
                        {
                            "chat_key": chat_key,
                            "trigger_time": int(t.trigger_time),
                            "event_desc": t.event_desc,
                            "temporary": bool(t.temporary),
                        },
                    )

            payload = {"version": self._PERSIST_VERSION, "tasks": tasks_dump}
            path = self._persist_path()
            tmp = path.with_suffix(path.suffix + ".tmp")
            try:
                async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(payload, ensure_ascii=False))
                tmp.replace(path)
            except Exception:
                logger.exception(f"持久化定时器写入失败: path={path}")

    async def start(self):
        """启动定时器服务"""
        if self.running:
            return
        self.running = True
        await self._load_persisted_tasks()
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
            chat_key (str): 聊天频道标识
            trigger_time (int): 触发时间戳。如果为0则立即触发频道;如果小于0则清空当前频道的定时器。
            event_desc (str): 详细事件描述
            silent (bool, optional): 是否静默设置. Defaults to False.
            override (bool): 是否为临时定时器，每个频道只能存在一个临时定时器，新设置的临时定时器会自动覆盖同一频道中已存在的临时定时器。
            temporary (Optional[bool], optional): 清除定时器时的类型筛选。None表示清除所有定时器，True只清除临时定时器，False只清除非临时定时器。仅在 trigger_time < 0 时生效。
            callback (Optional[Callable[[], Awaitable[None]]], optional): 定时器触发时执行的回调函数. Defaults to None.

        Returns:
            bool: 是否设置成功
        """
        # 如果触发时间小于0，清空当前频道的定时器
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
                        f"已清空频道 {chat_key} 的{'所有' if temporary is None else '临时' if temporary else '非临时'}定时器",
                    )
                # 清理后同步到磁盘（只影响 callback 为空的任务）
                await self._persist_tasks()
            return True

        # 如果触发时间为0，立即触发频道
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

        # 仅普通/临时定时器持久化；带 callback 的系统定时器不写磁盘
        if callback is None:
            await self._persist_tasks()
        return True

    def get_timers(self, chat_key: str) -> List[TimerTask]:
        """获取指定频道的所有未触发定时器

        Args:
            chat_key (str): 聊天频道标识

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
                        try:
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
                        except Exception:
                            logger.exception(f"定时器触发失败: chat_key={task.chat_key}")

                # 移除已触发的任务
                self.tasks[chat_key] = [t for t in tasks if t not in triggered_tasks]
                if not self.tasks[chat_key]:
                    del self.tasks[chat_key]

                if triggered_tasks:
                    await self._persist_tasks()

            await asyncio.sleep(1)  # 每秒检查一次


# 全局定时器服务实例
timer_service = TimerService()

