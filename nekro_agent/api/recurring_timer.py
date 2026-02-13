"""周期定时器相关 API

该模块是对 RecurringTimerService 的稳定封装，供插件或其他服务调用。
"""

from __future__ import annotations

import re
import secrets
import string
from datetime import datetime
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from croniter import croniter
from tortoise.exceptions import IntegrityError

from nekro_agent.models.db_recurring_timer_job import DBRecurringTimerJob
from nekro_agent.services.timer.recurring_timer_service import recurring_timer_service

__all__ = [
    "create_cron_job",
    "delete_job",
    "get_job",
    "get_job_id",
    "get_job_summary",
    "list_jobs",
    "pause_job",
    "resume_job",
    "run_now",
    "update_job",
    "validate_cron_expr",
    "validate_timezone",
]

_JOB_ID_ALLOWED = string.ascii_lowercase + string.digits
_JOB_ID_RE = re.compile(r"^[a-z0-9]{4,12}$")


def get_job_id(job: DBRecurringTimerJob) -> str:
    """获取任务对外ID（短ID，全局唯一）。"""
    return job.job_id


def _gen_job_id(length: int) -> str:
    return "".join(secrets.choice(_JOB_ID_ALLOWED) for _ in range(length))


async def _create_with_unique_job_id(
    *,
    chat_key: str,
    cron_expr: str,
    event_desc: str,
    timezone: str,
    workday_mode: str,
    title: Optional[str],
) -> DBRecurringTimerJob:
    """生成全局唯一 job_id 并创建任务。

    规则：
    - 默认 4 位
    - 连续 10 次冲突则扩展位数再试
    """
    length = 4
    while True:
        for _ in range(10):
            job_id = _gen_job_id(length)
            if not _JOB_ID_RE.fullmatch(job_id):
                continue
            # 先查一遍减少异常概率（仍可能并发冲突，最终以唯一约束为准）
            if await DBRecurringTimerJob.filter(job_id=job_id).exists():
                continue
            try:
                return await DBRecurringTimerJob.create(
                    job_id=job_id,
                    chat_key=chat_key,
                    title=title,
                    event_desc=event_desc,
                    cron_expr=cron_expr,
                    timezone=timezone,
                    workday_mode=workday_mode,
                    status="active",
                )
            except IntegrityError:
                continue
        length = min(length + 1, 12)


def validate_timezone(timezone: str) -> None:
    """校验时区字符串是否合法。"""
    ZoneInfo(timezone)


def validate_cron_expr(cron_expr: str, base_dt: Optional[datetime] = None) -> None:
    """校验 cron 表达式（默认 5 段：min hour day month dow）。

    仅用于校验可解析性与可计算下一次触发，不负责业务语义。
    """
    if not cron_expr.strip():
        raise ValueError("cron_expr 不能为空")
    base_dt = base_dt or datetime.now()
    croniter(cron_expr, base_dt).get_next(datetime)


async def create_cron_job(
    chat_key: str,
    cron_expr: str,
    event_desc: str,
    timezone: str,
    workday_mode: str = "none",
    title: Optional[str] = None,
) -> DBRecurringTimerJob:
    """创建一个周期 cron 任务。"""
    validate_timezone(timezone)
    validate_cron_expr(cron_expr)
    job = await _create_with_unique_job_id(
        chat_key=chat_key,
        cron_expr=cron_expr,
        event_desc=event_desc,
        timezone=timezone,
        workday_mode=workday_mode,
        title=title,
    )
    await recurring_timer_service.upsert_job(job)
    return job


async def update_job(
    job_id: str,
    *,
    cron_expr: Optional[str] = None,
    event_desc: Optional[str] = None,
    timezone: Optional[str] = None,
    workday_mode: Optional[str] = None,
    title: Optional[str] = None,
) -> DBRecurringTimerJob:
    """更新任务字段并刷新调度。"""
    job = await get_job(job_id)
    if cron_expr is not None:
        validate_cron_expr(cron_expr)
        job.cron_expr = cron_expr
    if event_desc is not None:
        job.event_desc = event_desc
    if timezone is not None:
        validate_timezone(timezone)
        job.timezone = timezone
    if workday_mode is not None:
        job.workday_mode = workday_mode
    if title is not None:
        job.title = title
    await job.save()
    if job.status == "active":
        await recurring_timer_service.upsert_job(job)
    return job


async def get_job(job_id: str) -> DBRecurringTimerJob:
    if not _JOB_ID_RE.fullmatch(job_id.strip()):
        raise ValueError(f"任务ID格式非法: {job_id}")
    job = await DBRecurringTimerJob.get_or_none(job_id=job_id.strip())
    if not job:
        raise ValueError(f"定时任务不存在: {job_id}")
    if job.status == "active" and job.next_run_at is None:
        # 自动补齐，避免 next_run_at 为空导致 cron 不触发
        await recurring_timer_service.upsert_job(job)
    return job


async def delete_job(job_id: str) -> None:
    await recurring_timer_service.delete_job(job_id.strip())


async def pause_job(job_id: str) -> DBRecurringTimerJob:
    job = await get_job(job_id)
    await recurring_timer_service.pause_job(job)
    return job


async def resume_job(job_id: str) -> DBRecurringTimerJob:
    job = await get_job(job_id)
    await recurring_timer_service.resume_job(job)
    return job


async def run_now(job_id: str) -> bool:
    job = await get_job(job_id)
    return await recurring_timer_service.run_now(job)


async def list_jobs(chat_key: str, status: Optional[str] = None, limit: int = 50) -> List[DBRecurringTimerJob]:
    return await recurring_timer_service.list_jobs(chat_key=chat_key, status=status, limit=limit)


async def get_job_summary(
    chat_key: str,
    upcoming_limit: int,
    recent_limit: int,
) -> Tuple[int, int, List[DBRecurringTimerJob], List[DBRecurringTimerJob]]:
    return await recurring_timer_service.get_summary(
        chat_key=chat_key,
        upcoming_limit=upcoming_limit,
        recent_limit=recent_limit,
    )

