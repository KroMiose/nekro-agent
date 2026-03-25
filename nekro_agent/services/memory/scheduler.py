"""记忆维护调度器

事件驱动 + 优先级队列的自适应调度系统。
监听消息事件，动态决定何时触发记忆沉淀。
"""

from __future__ import annotations

import asyncio
import heapq
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.services.memory.feature_flags import is_memory_system_enabled
from nekro_agent.services.memory.maintenance import prune_all_workspaces

logger = get_sub_logger("memory.scheduler")


class ConsolidationPriority(int, Enum):
    """沉淀优先级"""

    LOW = 3  # 低优先级：消息量少，活跃度低
    NORMAL = 2  # 普通优先级
    HIGH = 1  # 高优先级：消息量大或长时间未沉淀
    URGENT = 0  # 紧急：达到强制阈值


@dataclass
class WorkspaceActivityStats:
    """工作区活动统计"""

    workspace_id: int
    pending_messages: int = 0  # 待处理消息数
    last_message_at: datetime | None = None  # 最后消息时间
    last_consolidation_at: datetime | None = None  # 最后沉淀时间
    consecutive_skips: int = 0  # 连续跳过次数


@dataclass(order=True)
class ConsolidationTask:
    """沉淀任务"""

    priority: ConsolidationPriority
    scheduled_at: float = field(compare=True)  # 计划执行时间戳
    workspace_id: int = field(compare=False)
    chat_key: str = field(compare=False)
    version: int = field(compare=False, default=0)  # 用于任务更新


class MemoryMaintenanceScheduler:
    """记忆维护调度器

    设计目标：
    - 事件驱动：消息到达时更新统计，动态调整优先级
    - 低 CPU：使用堆 + sleep，不做轮询
    - 自适应：根据工作区活跃度调整沉淀频率
    - 并发控制：限制同时执行的沉淀任务数
    """

    def __init__(self) -> None:
        self._running = False
        self._loop_task: asyncio.Task | None = None
        self._prune_task: asyncio.Task | None = None
        self._execution_tasks: set[asyncio.Task] = set()
        self._wakeup = asyncio.Event()
        self._lock = asyncio.Lock()

        # 工作区统计
        self._workspace_stats: dict[int, WorkspaceActivityStats] = {}
        # chat_key -> workspace_id 映射缓存
        self._chat_workspace_map: dict[str, int] = {}

        # 优先级队列
        self._heap: list[ConsolidationTask] = []
        self._versions: dict[int, int] = {}  # workspace_id -> 当前版本

        # 并发控制
        self._running_tasks: set[int] = set()  # 正在执行的 workspace_id
        self._semaphore = asyncio.Semaphore(config.MEMORY_SCHEDULER_MAX_CONCURRENT)

        # 沉淀处理器（由外部注入）
        self._consolidation_handler: Callable[[int, str], asyncio.Task] | None = None

    async def start(self) -> None:
        """启动调度器"""
        if self._running:
            return
        if not is_memory_system_enabled():
            logger.info("记忆系统总开关关闭，跳过记忆调度器启动")
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())
        if config.MEMORY_PRUNE_ENABLED:
            self._prune_task = asyncio.create_task(self._run_prune_loop())
        # 异步恢复待处理的沉淀任务。默认关闭，避免启动后历史大批量补跑拖垮接口响应。
        if config.MEMORY_STARTUP_RECOVERY_ENABLED:
            asyncio.create_task(self._recover_pending_consolidations())
        logger.info("记忆维护调度器已启动")

    async def stop(self) -> None:
        """停止调度器"""
        self._running = False
        self._wakeup.set()
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        if self._prune_task and not self._prune_task.done():
            self._prune_task.cancel()
        for task in list(self._execution_tasks):
            if not task.done():
                task.cancel()
        async with self._lock:
            self._heap.clear()
            self._versions.clear()
            self._workspace_stats.clear()
        self._execution_tasks.clear()
        logger.info("记忆维护调度器已停止")

    def set_consolidation_handler(
        self,
        handler: Callable[[int, str], asyncio.Task],
    ) -> None:
        """设置沉淀处理器

        Args:
            handler: 接收 (workspace_id, chat_key) 返回 Task 的函数
        """
        self._consolidation_handler = handler

    async def on_new_message(
        self,
        chat_key: str,
        workspace_id: int,
        content_length: int = 0,
    ) -> None:
        """新消息事件处理

        Args:
            chat_key: 聊天频道标识
            workspace_id: 工作区 ID
            content_length: 消息内容长度
        """
        if not is_memory_system_enabled():
            return

        async with self._lock:
            # 更新映射缓存
            self._chat_workspace_map[chat_key] = workspace_id

            # 更新统计
            stats = self._workspace_stats.setdefault(
                workspace_id,
                WorkspaceActivityStats(workspace_id=workspace_id),
            )
            stats.pending_messages += 1
            stats.last_message_at = datetime.now()

            # 检查是否需要调度沉淀
            priority = self._compute_priority(stats)
            if priority is not None:
                await self._schedule_consolidation(workspace_id, chat_key, priority)

    def _compute_priority(self, stats: WorkspaceActivityStats) -> ConsolidationPriority | None:
        """计算沉淀优先级

        Returns:
            优先级，或 None 表示不需要沉淀
        """
        now = datetime.now()

        # 检查最小间隔
        if stats.last_consolidation_at:
            since_last = (now - stats.last_consolidation_at).total_seconds()
            if since_last < config.MEMORY_CONSOLIDATION_MIN_INTERVAL_SECONDS:
                return None

        # 计算优先级
        msg_count = stats.pending_messages
        hours_since_last = (
            (now - stats.last_consolidation_at).total_seconds() / 3600
            if stats.last_consolidation_at
            else float("inf")
        )

        # 紧急：超过消息阈值的 2 倍
        if msg_count >= config.MEMORY_CONSOLIDATION_MSG_THRESHOLD * 2:
            return ConsolidationPriority.URGENT

        # 高优先级：达到消息阈值或时间阈值的 2 倍
        if (
            msg_count >= config.MEMORY_CONSOLIDATION_MSG_THRESHOLD
            or hours_since_last >= config.MEMORY_CONSOLIDATION_TIME_THRESHOLD_HOURS * 2
        ):
            return ConsolidationPriority.HIGH

        # 普通优先级：达到时间阈值
        if hours_since_last >= config.MEMORY_CONSOLIDATION_TIME_THRESHOLD_HOURS:
            return ConsolidationPriority.NORMAL

        # 低优先级：有一定消息量
        if msg_count >= config.MEMORY_CONSOLIDATION_MSG_THRESHOLD // 2:
            return ConsolidationPriority.LOW

        return None

    async def _schedule_consolidation(
        self,
        workspace_id: int,
        chat_key: str,
        priority: ConsolidationPriority,
        extra_delay_seconds: float = 0.0,
    ) -> None:
        """调度沉淀任务"""
        # 如果正在执行，跳过
        if workspace_id in self._running_tasks:
            return

        # 更新版本号
        version = self._versions.get(workspace_id, 0) + 1
        self._versions[workspace_id] = version

        # 计算调度时间（错峰）
        delay = len(self._heap) * config.MEMORY_SCHEDULER_STAGGER_DELAY_SECONDS + max(0.0, extra_delay_seconds)
        scheduled_at = time.time() + delay

        task = ConsolidationTask(
            priority=priority,
            scheduled_at=scheduled_at,
            workspace_id=workspace_id,
            chat_key=chat_key,
            version=version,
        )
        heapq.heappush(self._heap, task)
        self._wakeup.set()

        logger.debug(
            f"调度沉淀任务: workspace={workspace_id}, priority={priority.name}, delay={delay}s",
        )

    async def _run_loop(self) -> None:
        """主调度循环"""
        while self._running:
            try:
                # 获取下一个任务
                task = await self._get_next_task()
                if task is None:
                    # 等待新任务
                    self._wakeup.clear()
                    await self._wakeup.wait()
                    continue

                # 等待到计划时间
                now = time.time()
                if task.scheduled_at > now:
                    await asyncio.sleep(task.scheduled_at - now)

                # 执行任务。这里不能直接 await，否则整个调度循环会被单个长任务串行阻塞，
                # 导致并发信号量形同虚设。
                exec_task = asyncio.create_task(self._execute_task(task))
                self._execution_tasks.add(exec_task)
                exec_task.add_done_callback(self._execution_tasks.discard)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"调度循环异常: {e}")
                await asyncio.sleep(1)

    async def _run_prune_loop(self) -> None:
        """后台定期清理低价值记忆。"""
        interval_seconds = max(3600, config.MEMORY_PRUNE_INTERVAL_HOURS * 3600)
        while self._running:
            try:
                await asyncio.sleep(interval_seconds)
                if not self._running:
                    return
                results = await prune_all_workspaces()
                total_paragraphs = sum(item.paragraphs_pruned for item in results.values())
                total_relations = sum(item.relations_pruned for item in results.values())
                total_entities = sum(item.entities_pruned for item in results.values())
                logger.info(
                    f"自动记忆清理完成: workspaces={len(results)}, "
                    f"paragraphs={total_paragraphs}, relations={total_relations}, entities={total_entities}",
                )
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.exception(f"自动记忆清理循环异常: {e}")
                await asyncio.sleep(60)

    async def _get_next_task(self) -> ConsolidationTask | None:
        """获取下一个有效任务"""
        async with self._lock:
            while self._heap:
                task = heapq.heappop(self._heap)
                # 检查版本是否有效
                if self._versions.get(task.workspace_id, 0) == task.version:
                    return task
            return None

    async def _execute_task(self, task: ConsolidationTask) -> None:
        """执行沉淀任务"""
        workspace_id = task.workspace_id

        if self._consolidation_handler is None:
            logger.warning("沉淀处理器未设置，跳过任务")
            return

        try:
            async with self._semaphore:
                from nekro_agent.services.memory.rebuild import is_workspace_memory_rebuild_running

                if is_workspace_memory_rebuild_running(workspace_id):
                    logger.info(f"工作区记忆重建进行中，延后实时沉淀: workspace={workspace_id}")
                    async with self._lock:
                        await self._schedule_consolidation(
                            workspace_id,
                            task.chat_key,
                            task.priority,
                            extra_delay_seconds=max(2.0, config.MEMORY_CONSOLIDATION_BATCH_COOLDOWN_SECONDS),
                        )
                    return

                self._running_tasks.add(workspace_id)
                try:
                    logger.info(f"开始执行沉淀: workspace={workspace_id}")
                    await self._consolidation_handler(workspace_id, task.chat_key)

                    # 更新统计
                    async with self._lock:
                        if workspace_id in self._workspace_stats:
                            stats = self._workspace_stats[workspace_id]
                            stats.pending_messages = 0
                            stats.last_consolidation_at = datetime.now()
                            stats.consecutive_skips = 0

                    logger.info(f"沉淀完成: workspace={workspace_id}")
                    cooldown = max(0.0, float(config.MEMORY_CONSOLIDATION_BATCH_COOLDOWN_SECONDS))
                    if cooldown > 0:
                        await asyncio.sleep(cooldown)

                except Exception as e:
                    logger.exception(f"沉淀任务失败: workspace={workspace_id}, error={e}")
                    # 增加跳过计数
                    async with self._lock:
                        if workspace_id in self._workspace_stats:
                            self._workspace_stats[workspace_id].consecutive_skips += 1
                finally:
                    self._running_tasks.discard(workspace_id)
        except Exception as e:
            logger.exception(f"沉淀任务调度执行异常: workspace={workspace_id}, error={e}")

    async def force_consolidation(self, workspace_id: int, chat_key: str) -> bool:
        """强制触发沉淀

        Args:
            workspace_id: 工作区 ID
            chat_key: 聊天频道标识

        Returns:
            是否成功调度
        """
        async with self._lock:
            if workspace_id in self._running_tasks:
                return False
            await self._schedule_consolidation(
                workspace_id,
                chat_key,
                ConsolidationPriority.URGENT,
            )
            return True

    async def _recover_pending_consolidations(self) -> None:
        """重启后恢复待处理的沉淀任务

        扫描所有活跃工作区，检查是否有达到阈值的待沉淀消息。
        """
        try:
            import json

            from nekro_agent.models.db_chat_channel import DBChatChannel
            from nekro_agent.models.db_chat_message import DBChatMessage
            from nekro_agent.models.db_workspace import DBWorkspace

            # 等待一段时间，确保数据库和其他服务就绪
            await asyncio.sleep(3)

            workspaces = await DBWorkspace.filter(status="active").all()
            recovered_count = 0
            max_tasks = max(0, int(config.MEMORY_STARTUP_RECOVERY_MAX_TASKS))

            for ws in workspaces:
                try:
                    # 获取该工作区的所有频道
                    channels = await DBChatChannel.filter(workspace_id=ws.id).all()

                    for channel in channels:
                        # 读取记忆状态
                        last_consolidated_db_id = 0
                        try:
                            data = json.loads(channel.data or "{}")
                            if isinstance(data, dict):
                                memory_state = data.get("memory_state", {})
                                if isinstance(memory_state, dict):
                                    raw_db_id = memory_state.get("last_consolidated_message_db_id", 0)
                                    if isinstance(raw_db_id, int) and raw_db_id >= 0:
                                        last_consolidated_db_id = raw_db_id
                        except json.JSONDecodeError:
                            pass

                        # 统计待处理消息数
                        pending_count = await DBChatMessage.filter(
                            chat_key=channel.chat_key,
                            id__gt=last_consolidated_db_id,
                        ).count()

                        # 如果达到阈值，调度沉淀任务
                        if pending_count >= config.MEMORY_CONSOLIDATION_MSG_THRESHOLD:
                            async with self._lock:
                                self._chat_workspace_map[channel.chat_key] = ws.id
                                stats = self._workspace_stats.setdefault(
                                    ws.id,
                                    WorkspaceActivityStats(workspace_id=ws.id),
                                )
                                stats.pending_messages = pending_count
                                await self._schedule_consolidation(
                                    ws.id,
                                    channel.chat_key,
                                    ConsolidationPriority.NORMAL,
                                )
                            recovered_count += 1
                            logger.debug(
                                f"恢复待处理沉淀: workspace={ws.id}, "
                                f"chat_key={channel.chat_key}, pending={pending_count}",
                            )
                            if max_tasks and recovered_count >= max_tasks:
                                logger.info(
                                    f"启动恢复已达到任务上限: recovered={recovered_count}, max={max_tasks}",
                                )
                                logger.info(f"已恢复 {recovered_count} 个待处理的沉淀任务")
                                return

                except Exception as e:
                    logger.warning(f"恢复工作区沉淀任务失败: workspace={ws.id}, error={e}")

            if recovered_count > 0:
                logger.info(f"已恢复 {recovered_count} 个待处理的沉淀任务")

        except Exception as e:
            logger.warning(f"恢复待处理沉淀任务失败: {e}")

    def get_stats(self) -> dict[int, dict]:
        """获取所有工作区的统计信息"""
        return {
            ws_id: {
                "pending_messages": stats.pending_messages,
                "last_message_at": stats.last_message_at.isoformat() if stats.last_message_at else None,
                "last_consolidation_at": (stats.last_consolidation_at.isoformat() if stats.last_consolidation_at else None),
                "consecutive_skips": stats.consecutive_skips,
            }
            for ws_id, stats in self._workspace_stats.items()
        }


# 全局单例
memory_scheduler = MemoryMaintenanceScheduler()
