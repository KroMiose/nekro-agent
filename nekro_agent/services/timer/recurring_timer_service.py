from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from croniter import croniter

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_recurring_timer_job import DBRecurringTimerJob
from nekro_agent.services.message_service import message_service

from .cn_workday_service import cn_workday_service

logger = get_sub_logger("timer")


@dataclass(frozen=True, order=True)
class _HeapItem:
    next_run_ts: float
    job_id: str
    version: int


class RecurringTimerService:
    """持久化 cron 定时任务服务。

    设计目标：
    - 任务持久化，可随服务重启恢复
    - 低 CPU：按最近触发时间 sleep，不做每秒轮询
    - 健壮：单任务异常不影响整体；连续失败自动暂停并提示一次
    """

    def __init__(self) -> None:
        self._running: bool = False
        self._loop_task: Optional[asyncio.Task] = None
        self._wakeup = asyncio.Event()
        self._lock = asyncio.Lock()

        self._versions: Dict[str, int] = {}
        self._heap: List[_HeapItem] = []

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        await self._reload_from_db()
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("RecurringTimer service started")

    async def stop(self) -> None:
        self._running = False
        self._wakeup.set()
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        async with self._lock:
            self._heap.clear()
            self._versions.clear()
        logger.info("RecurringTimer service stopped")

    async def upsert_job(self, job: DBRecurringTimerJob) -> None:
        """当任务创建/更新/恢复时调用，用于刷新调度。"""
        next_dt = await self._compute_next_run(job, base_dt=None)
        job.next_run_at = next_dt
        logger.debug(
            f"[cron] upsert_job computed next_run_at: job_id={job.job_id}, "
            f"cron={job.cron_expr}, mode={job.workday_mode}, tz={job.timezone}, next={next_dt}",
        )
        try:
            await job.save()
        except Exception:
            # 不应因 DB 写入问题影响调度本身（至少保证内存调度继续）
            logger.exception(f"更新 cron 任务 next_run_at 持久化失败: job_id={job.job_id}")
        await self._schedule_job(job)

    async def pause_job(self, job: DBRecurringTimerJob) -> None:
        job.status = "paused"
        await job.save()
        logger.debug(f"[cron] pause_job: job_id={job.job_id}")
        await self._unschedule_job(job.job_id)

    async def resume_job(self, job: DBRecurringTimerJob) -> None:
        job.status = "active"
        job.consecutive_failures = 0
        job.last_error = None
        job.paused_notice_sent_at = None
        await job.save()
        logger.debug(f"[cron] resume_job: job_id={job.job_id}")
        await self.upsert_job(job)

    async def delete_job(self, job_id: str) -> None:
        logger.debug(f"[cron] delete_job: job_id={job_id}")
        await self._unschedule_job(job_id)
        await DBRecurringTimerJob.filter(job_id=job_id).delete()

    async def run_now(self, job: DBRecurringTimerJob) -> bool:
        """立即执行一次任务（不改变 cron 表达式）。"""
        if job.status != "active":
            return False
        logger.debug(f"[cron] run_now: job_id={job.job_id}")
        await self._fire_job(job, fired_at=datetime.now(ZoneInfo(job.timezone)), is_misfire=False)
        await self.upsert_job(job)
        return True

    async def list_jobs(
        self,
        chat_key: str,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[DBRecurringTimerJob]:
        qs = DBRecurringTimerJob.filter(chat_key=chat_key)
        if status:
            qs = qs.filter(status=status)
        jobs = await qs.order_by("-update_time").limit(limit)
        # 自动补齐 next_run_at，避免历史数据/异常导致 cron 无法触发
        for job in jobs:
            if job.status == "active" and job.next_run_at is None:
                try:
                    await self.upsert_job(job)
                except Exception:
                    logger.exception(f"补齐 cron 任务 next_run_at 失败: job_id={job.job_id}")
        return jobs

    async def get_summary(
        self,
        chat_key: str,
        upcoming_limit: int,
        recent_limit: int,
    ) -> Tuple[int, int, List[DBRecurringTimerJob], List[DBRecurringTimerJob]]:
        active_count = await DBRecurringTimerJob.filter(chat_key=chat_key, status="active").count()
        paused_count = await DBRecurringTimerJob.filter(chat_key=chat_key, status="paused").count()

        # 自动补齐 next_run_at（仅少量），避免 upcoming 为空或 next_run_at 为 None
        missing = (
            await DBRecurringTimerJob.filter(chat_key=chat_key, status="active", next_run_at__isnull=True)
            .order_by("-update_time")
            .limit(max(upcoming_limit, 5))
        )
        for job in missing:
            try:
                await self.upsert_job(job)
            except Exception:
                logger.exception(f"补齐 cron 任务 next_run_at 失败: job_id={job.job_id}")

        upcoming = (
            await DBRecurringTimerJob.filter(chat_key=chat_key, status="active", next_run_at__not_isnull=True)
            .order_by("next_run_at")
            .limit(upcoming_limit)
        )
        recent = (
            await DBRecurringTimerJob.filter(chat_key=chat_key, last_run_at__not_isnull=True)
            .order_by("-last_run_at")
            .limit(recent_limit)
        )
        return active_count, paused_count, upcoming, recent

    async def _reload_from_db(self) -> None:
        """启动恢复：把 active 的 job 计算 next_run 并入堆。"""
        async with self._lock:
            self._heap.clear()
            self._versions.clear()

        jobs = await DBRecurringTimerJob.filter(status="active").all()
        logger.debug(f"[cron] reload_from_db: active_jobs={len(jobs)}")
        for job in jobs:
            try:
                next_dt = await self._compute_next_run(job, base_dt=None)
            except Exception:
                logger.exception(f"恢复 cron 任务失败: job_id={job.job_id}")
                continue
            job.next_run_at = next_dt
            await job.save()
            logger.debug(
                f"[cron] restored: job_id={job.job_id}, cron={job.cron_expr}, "
                f"mode={job.workday_mode}, tz={job.timezone}, next={next_dt}",
            )
            await self._schedule_job(job)

    async def _schedule_job(self, job: DBRecurringTimerJob) -> None:
        if job.status != "active" or job.next_run_at is None:
            return
        job_id = job.job_id
        async with self._lock:
            version = self._versions.get(job_id, 0) + 1
            self._versions[job_id] = version
            heapq.heappush(self._heap, _HeapItem(job.next_run_at.timestamp(), job_id, version))
            heap_size = len(self._heap)
        self._wakeup.set()
        logger.debug(
            f"[cron] scheduled: job_id={job_id}, version={version}, "
            f"next_ts={job.next_run_at.timestamp():.3f}, heap_size={heap_size}",
        )

    async def _unschedule_job(self, job_id: str) -> None:
        async with self._lock:
            self._versions[job_id] = self._versions.get(job_id, 0) + 1
            new_ver = self._versions[job_id]
        self._wakeup.set()
        logger.debug(f"[cron] unschedule: job_id={job_id}, version={new_ver}")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                item = await self._peek_next_item()
                if item is None:
                    await self._wait_for_wakeup(None)
                    continue

                now_ts = datetime.now().timestamp()
                if item.next_run_ts > now_ts:
                    logger.debug(
                        f"[cron] wait_until_due: job_id={item.job_id}, "
                        f"due_in={item.next_run_ts - now_ts:.3f}s",
                    )
                    await self._wait_for_wakeup(item.next_run_ts - now_ts)
                    continue

                item = await self._pop_next_ready_item()
                if item is None:
                    continue

                job = await DBRecurringTimerJob.get_or_none(job_id=item.job_id)
                if not job or job.status != "active":
                    logger.debug(f"[cron] skip_pop_item: job_id={item.job_id}, reason=missing_or_inactive")
                    continue

                logger.debug(
                    f"[cron] due: job_id={job.job_id}, cron={job.cron_expr}, "
                    f"mode={job.workday_mode}, tz={job.timezone}, next_run_at={job.next_run_at}",
                )
                fired_at = datetime.now(ZoneInfo(job.timezone))
                await self._handle_due_job(job, fired_at)
            except asyncio.CancelledError:
                return
            except Exception:
                logger.exception("RecurringTimer loop error")
                await asyncio.sleep(1)

    async def _peek_next_item(self) -> Optional[_HeapItem]:
        async with self._lock:
            while self._heap:
                item = self._heap[0]
                current_ver = self._versions.get(item.job_id, 0)
                if item.version != current_ver:
                    heapq.heappop(self._heap)
                    continue
                return item
        return None

    async def _pop_next_ready_item(self) -> Optional[_HeapItem]:
        """弹出堆顶的有效项（仅当其 version 仍然有效）。"""
        async with self._lock:
            while self._heap:
                item = heapq.heappop(self._heap)
                current_ver = self._versions.get(item.job_id, 0)
                if item.version != current_ver:
                    continue
                return item
        return None

    async def _wait_for_wakeup(self, timeout_seconds: Optional[float]) -> None:
        self._wakeup.clear()
        try:
            if timeout_seconds is None:
                await self._wakeup.wait()
            else:
                await asyncio.wait_for(self._wakeup.wait(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            return

    async def _handle_due_job(self, job: DBRecurringTimerJob, fired_at: datetime) -> None:
        is_misfire = False
        next_run_at = job.next_run_at
        if next_run_at is not None:
            diff = fired_at - next_run_at.replace(tzinfo=fired_at.tzinfo)
            if diff.total_seconds() > 1:
                is_misfire = True

        if is_misfire:
            if next_run_at is None:
                await self.upsert_job(job)
                return
            lag_seconds = int((fired_at - next_run_at.replace(tzinfo=fired_at.tzinfo)).total_seconds())
            logger.debug(f"[cron] misfire_detected: job_id={job.job_id}, lag={lag_seconds}s")
            if lag_seconds > job.misfire_grace_seconds:
                if job.misfire_policy == "skip":
                    logger.debug(
                        f"[cron] misfire_skip: job_id={job.job_id}, "
                        f"policy=skip, grace={job.misfire_grace_seconds}s",
                    )
                    await self.upsert_job(job)
                    return
                # fire_once: 超过宽限仍然跳过（避免补发太久以前的提醒）
                logger.debug(
                    f"[cron] misfire_drop: job_id={job.job_id}, "
                    f"policy=fire_once, grace={job.misfire_grace_seconds}s",
                )
                await self.upsert_job(job)
                return

        await self._fire_job(job, fired_at=fired_at, is_misfire=is_misfire)
        await self.upsert_job(job)

    async def _fire_job(self, job: DBRecurringTimerJob, fired_at: datetime, is_misfire: bool) -> None:
        try:
            logger.debug(f"[cron] fire: job_id={job.job_id}, misfire={is_misfire}")
            title = f"{job.title}\n" if job.title else ""
            misfire_tag = "（补发）" if is_misfire else ""
            system_message = f"⏰ 定时提醒{misfire_tag}：{title}{job.event_desc}"
            await message_service.push_system_message(
                chat_key=job.chat_key,
                agent_messages=system_message,
                trigger_agent=True,
            )
        except Exception as e:
            job.consecutive_failures += 1
            job.last_error = str(e)
            await job.save()
            logger.exception(f"cron 任务触发失败: job_id={job.job_id}")

            if job.consecutive_failures >= 3:
                await self._auto_pause_job(job)
            return

        job.last_run_at = fired_at
        job.consecutive_failures = 0
        job.last_error = None
        await job.save()
        logger.debug(f"[cron] fire_success: job_id={job.job_id}, fired_at={fired_at}")

    async def _auto_pause_job(self, job: DBRecurringTimerJob) -> None:
        if job.paused_notice_sent_at is not None:
            job.status = "paused"
            await job.save()
            await self._unschedule_job(job.job_id)
            return

        job.status = "paused"
        job.paused_notice_sent_at = datetime.now(ZoneInfo(job.timezone))
        await job.save()
        await self._unschedule_job(job.job_id)
        logger.debug(f"[cron] auto_paused: job_id={job.job_id}, failures={job.consecutive_failures}")

        try:
            await message_service.push_system_message(
                chat_key=job.chat_key,
                agent_messages=(
                    "⏸️ 定时任务已自动暂停：连续触发失败次数过多。\n"
                    f"- 任务ID: {job.job_id}\n"
                    f"- 标题: {job.title or '（无）'}\n"
                    f"- 最近错误: {job.last_error or '（无）'}\n"
                    "你可以让 AI 调用 resume_recurring_timer 恢复，或 update_recurring_timer 修正参数。"
                ),
                trigger_agent=False,
            )
        except Exception:
            logger.exception(f"发送自动暂停提示失败: job_id={job.job_id}")

    async def _compute_next_run(self, job: DBRecurringTimerJob, base_dt: Optional[datetime]) -> datetime:
        tz = ZoneInfo(job.timezone)
        now = datetime.now(tz)
        base = base_dt or now
        if job.last_run_at is not None:
            # DB 可能保存为本地时间（naive）或 aware；统一换算到 job.tz
            last = job.last_run_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=tz)
            else:
                last = last.astimezone(tz)
            base = max(base, last + timedelta(seconds=1))

        itr = croniter(job.cron_expr, base)
        next_dt: datetime = itr.get_next(datetime)  # type: ignore[assignment]
        next_dt = next_dt.astimezone(tz)
        filtered = await self._apply_workday_filter(job, itr, next_dt)
        if filtered != next_dt:
            logger.debug(
                f"[cron] filter_shifted_next: job_id={job.job_id}, from={next_dt}, to={filtered}, mode={job.workday_mode}",
            )
        return filtered

    async def _apply_workday_filter(self, job: DBRecurringTimerJob, itr: croniter, next_dt: datetime) -> datetime:
        if job.workday_mode == "none":
            return next_dt

        max_skip = 370
        skipped = 0
        for _ in range(max_skip):
            if job.workday_mode == "mon_fri":
                if next_dt.weekday() < 5:
                    if skipped:
                        logger.debug(
                            f"[cron] workday_filter_ok: job_id={job.job_id}, skipped={skipped}, mode=mon_fri",
                        )
                    return next_dt
            elif job.workday_mode == "weekend":
                if next_dt.weekday() >= 5:
                    if skipped:
                        logger.debug(
                            f"[cron] workday_filter_ok: job_id={job.job_id}, skipped={skipped}, mode=weekend",
                        )
                    return next_dt
            elif job.workday_mode == "cn_workday":
                ok = await cn_workday_service.is_workday(next_dt.date())
                if ok is None:
                    # 降级：无法获取 CN 数据时使用 mon_fri
                    if next_dt.weekday() < 5:
                        if skipped:
                            logger.debug(
                                f"[cron] workday_filter_ok: job_id={job.job_id}, skipped={skipped}, mode=cn_workday_fallback",
                            )
                        return next_dt
                elif ok:
                    if skipped:
                        logger.debug(
                            f"[cron] workday_filter_ok: job_id={job.job_id}, skipped={skipped}, mode=cn_workday",
                        )
                    return next_dt
            elif job.workday_mode == "cn_restday":
                ok = await cn_workday_service.is_restday(next_dt.date())
                if ok is None:
                    # 降级：无法获取 CN 数据时，按周末判断
                    if next_dt.weekday() >= 5:
                        if skipped:
                            logger.debug(
                                f"[cron] workday_filter_ok: job_id={job.job_id}, skipped={skipped}, mode=cn_restday_fallback",
                            )
                        return next_dt
                elif ok:
                    if skipped:
                        logger.debug(
                            f"[cron] workday_filter_ok: job_id={job.job_id}, skipped={skipped}, mode=cn_restday",
                        )
                    return next_dt
            else:
                return next_dt

            next_dt = itr.get_next(datetime)  # type: ignore[assignment]
            next_dt = next_dt.astimezone(ZoneInfo(job.timezone))
            skipped += 1

        logger.debug(
            f"[cron] workday_filter_exceeded: job_id={job.job_id}, mode={job.workday_mode}, skipped={skipped}",
        )
        raise ValueError("workday filter exceeded max iterations")


recurring_timer_service = RecurringTimerService()

