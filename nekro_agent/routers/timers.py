from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional, Set

from fastapi import APIRouter, Depends, Query

from nekro_agent.api import recurring_timer
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_recurring_timer_job import DBRecurringTimerJob
from nekro_agent.models.db_user import DBUser
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.schemas.errors import NotFoundError, ValidationError
from nekro_agent.schemas.timer import (
    ActionOkResponse,
    TimerTaskItem,
    TimerTaskListResponse,
    TimerTaskSummary,
)
from nekro_agent.services.timer import timer_service
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.workspace.manager import WorkspaceService

router = APIRouter(prefix="/timers", tags=["Timers"])

TaskType = Literal["one_shot", "recurring"]
StatusFilter = Literal["active", "paused", "error"]
SortBy = Literal["next_run_asc", "recent_update", "recent_run", "error_first"]
TimeRange = Literal["all", "today", "24h", "7d", "overdue"]


def _format_dt(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _derive_title(text: str) -> str:
    first_line = (text or "").strip().splitlines()[0] if text.strip() else ""
    return first_line[:48]


def _parse_dt(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def _compare_now(base: datetime) -> datetime:
    if base.tzinfo is None:
        return datetime.now()
    return datetime.now(base.tzinfo)


async def _load_context(chat_keys: Set[str]) -> tuple[Dict[str, DBChatChannel], Dict[int, DBWorkspace], Dict[str, bool]]:
    if not chat_keys:
        return {}, {}, {}

    channels = await DBChatChannel.filter(chat_key__in=list(chat_keys)).all()
    channel_map = {channel.chat_key: channel for channel in channels}

    workspace_ids = sorted({channel.workspace_id for channel in channels if channel.workspace_id is not None})
    if not workspace_ids:
        return channel_map, {}, {}

    workspaces = await DBWorkspace.filter(id__in=workspace_ids).all()
    workspace_map = {workspace.id: workspace for workspace in workspaces}

    all_workspace_channels = await DBChatChannel.filter(workspace_id__in=workspace_ids).all()
    workspace_bound_chat_keys: Dict[int, List[str]] = {}
    for channel in all_workspace_channels:
        if channel.workspace_id is None:
            continue
        workspace_bound_chat_keys.setdefault(channel.workspace_id, []).append(channel.chat_key)

    primary_map: Dict[str, bool] = {}
    for workspace in workspaces:
        primary_chat_key = WorkspaceService.get_primary_channel_chat_key(
            workspace,
            workspace_bound_chat_keys.get(workspace.id, []),
        )
        if primary_chat_key:
            primary_map[primary_chat_key] = True

    return channel_map, workspace_map, primary_map


def _build_one_shot_item(
    task,
    channel_map: Dict[str, DBChatChannel],
    workspace_map: Dict[int, DBWorkspace],
    primary_map: Dict[str, bool],
) -> TimerTaskItem:
    channel = channel_map.get(task.chat_key)
    workspace = workspace_map.get(channel.workspace_id) if channel and channel.workspace_id is not None else None
    source = "system" if task.chat_key.startswith("system_") else "agent"
    return TimerTaskItem(
        id=task.task_id,
        task_type="one_shot",
        title=_derive_title(task.event_desc),
        event_desc=task.event_desc,
        status="active",
        workspace_id=workspace.id if workspace else None,
        workspace_name=workspace.name if workspace else None,
        chat_key=task.chat_key,
        channel_name=channel.channel_name if channel else None,
        is_primary_channel=primary_map.get(task.chat_key, False),
        trigger_at=datetime.fromtimestamp(task.trigger_time).isoformat(),
        next_run_at=datetime.fromtimestamp(task.trigger_time).isoformat(),
        source=source,
        is_temporary=bool(task.temporary),
        actionable=source != "system",
    )


def _build_recurring_item(
    job: DBRecurringTimerJob,
    channel_map: Dict[str, DBChatChannel],
    workspace_map: Dict[int, DBWorkspace],
    primary_map: Dict[str, bool],
) -> TimerTaskItem:
    channel = channel_map.get(job.chat_key)
    workspace = workspace_map.get(channel.workspace_id) if channel and channel.workspace_id is not None else None
    has_error = bool(job.last_error) or job.consecutive_failures > 0
    source = "system" if job.chat_key.startswith("system_") else "agent"
    status: Literal["active", "paused", "error"]
    if job.status == "paused":
        status = "paused"
    elif has_error:
        status = "error"
    else:
        status = "active"
    return TimerTaskItem(
        id=job.job_id,
        task_type="recurring",
        title=job.title or _derive_title(job.event_desc),
        event_desc=job.event_desc,
        status=status,
        workspace_id=workspace.id if workspace else None,
        workspace_name=workspace.name if workspace else None,
        chat_key=job.chat_key,
        channel_name=channel.channel_name if channel else None,
        is_primary_channel=primary_map.get(job.chat_key, False),
        cron_expr=job.cron_expr,
        timezone=job.timezone,
        workday_mode=job.workday_mode,
        next_run_at=_format_dt(job.next_run_at),
        last_run_at=_format_dt(job.last_run_at),
        consecutive_failures=job.consecutive_failures,
        last_error=job.last_error,
        source=source,
        create_time=_format_dt(job.create_time),
        update_time=_format_dt(job.update_time),
        actionable=source != "system",
    )


async def _build_all_items() -> List[TimerTaskItem]:
    one_shot_tasks = timer_service.get_all_timers(include_callbacks=False)
    recurring_jobs = await DBRecurringTimerJob.all()

    chat_keys = {task.chat_key for task in one_shot_tasks} | {job.chat_key for job in recurring_jobs}
    channel_map, workspace_map, primary_map = await _load_context(chat_keys)

    items: List[TimerTaskItem] = []
    for task in one_shot_tasks:
        items.append(_build_one_shot_item(task, channel_map, workspace_map, primary_map))
    for job in recurring_jobs:
        items.append(_build_recurring_item(job, channel_map, workspace_map, primary_map))
    return items


def _match_time_range(item: TimerTaskItem, time_range: TimeRange) -> bool:
    if time_range == "all":
        return True

    target_raw = item.next_run_at or item.trigger_at
    if not target_raw:
        return time_range == "overdue" and item.status == "error"

    target = _parse_dt(target_raw)
    now = _compare_now(target)
    end_today = datetime.combine(now.date(), datetime.max.time(), tzinfo=target.tzinfo)
    if time_range == "today":
        return now <= target <= end_today
    if time_range == "24h":
        return now <= target <= now + timedelta(hours=24)
    if time_range == "7d":
        return now <= target <= now + timedelta(days=7)
    if time_range == "overdue":
        return target < now
    return True


def _sort_items(items: List[TimerTaskItem], sort_by: SortBy) -> List[TimerTaskItem]:
    def next_ts(item: TimerTaskItem) -> float:
        raw = item.next_run_at or item.trigger_at
        if not raw:
            return float("inf")
        return datetime.fromisoformat(raw).timestamp()

    def recent_update_ts(item: TimerTaskItem) -> float:
        raw = item.update_time or item.create_time
        if not raw:
            return 0
        return datetime.fromisoformat(raw).timestamp()

    def recent_run_ts(item: TimerTaskItem) -> float:
        if not item.last_run_at:
            return 0
        return datetime.fromisoformat(item.last_run_at).timestamp()

    def error_rank(item: TimerTaskItem) -> int:
        return 0 if item.status == "error" or item.last_error or item.consecutive_failures > 0 else 1

    if sort_by == "recent_update":
        return sorted(items, key=recent_update_ts, reverse=True)
    if sort_by == "recent_run":
        return sorted(items, key=recent_run_ts, reverse=True)
    if sort_by == "error_first":
        return sorted(items, key=lambda item: (error_rank(item), next_ts(item), item.title.lower()))
    return sorted(items, key=lambda item: (next_ts(item), item.title.lower()))


def _apply_filters(
    items: List[TimerTaskItem],
    *,
    search: str,
    workspace_id: Optional[int],
    task_type: Optional[TaskType],
    status: Optional[StatusFilter],
    time_range: TimeRange,
) -> List[TimerTaskItem]:
    keyword = search.strip().lower()
    filtered: List[TimerTaskItem] = []

    for item in items:
        if workspace_id is not None and item.workspace_id != workspace_id:
            continue
        if task_type and item.task_type != task_type:
            continue
        if status == "error":
            if item.status != "error" and not item.last_error and item.consecutive_failures <= 0:
                continue
        elif status and item.status != status:
            continue
        if not _match_time_range(item, time_range):
            continue
        if keyword:
            haystack = " ".join(
                [
                    item.id,
                    item.title,
                    item.event_desc,
                    item.workspace_name or "",
                    item.channel_name or "",
                    item.chat_key,
                ]
            ).lower()
            if keyword not in haystack:
                continue
        filtered.append(item)

    return filtered


@router.get("/summary", response_model=TimerTaskSummary, summary="获取定时任务概览统计")
async def get_timer_summary(_current_user: DBUser = Depends(get_current_active_user)) -> TimerTaskSummary:
    items = await _build_all_items()
    upcoming_24h = 0
    workspace_ids = set()
    errors = 0

    for item in items:
        if item.workspace_id is not None:
            workspace_ids.add(item.workspace_id)
        if item.status == "error" or item.last_error or item.consecutive_failures > 0:
            errors += 1
        raw = item.next_run_at or item.trigger_at
        if raw:
            target = _parse_dt(raw)
            now = _compare_now(target)
            if now <= target <= now + timedelta(hours=24):
                upcoming_24h += 1

    return TimerTaskSummary(
        total=len(items),
        active_recurring=sum(1 for item in items if item.task_type == "recurring" and item.status == "active"),
        paused=sum(1 for item in items if item.status == "paused"),
        upcoming_24h=upcoming_24h,
        errors=errors,
        workspace_count=len(workspace_ids),
    )


@router.get("/list", response_model=TimerTaskListResponse, summary="获取定时任务列表")
async def get_timer_list(
    search: str = Query(default=""),
    workspace_id: Optional[int] = Query(default=None),
    task_type: Optional[TaskType] = Query(default=None),
    status: Optional[StatusFilter] = Query(default=None),
    time_range: TimeRange = Query(default="all"),
    sort_by: SortBy = Query(default="next_run_asc"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> TimerTaskListResponse:
    items = await _build_all_items()
    filtered = _apply_filters(
        items,
        search=search,
        workspace_id=workspace_id,
        task_type=task_type,
        status=status,
        time_range=time_range,
    )
    return TimerTaskListResponse(total=len(filtered), items=_sort_items(filtered, sort_by))


@router.get("/{task_type}/{task_id}", response_model=TimerTaskItem, summary="获取单个定时任务详情")
async def get_timer_detail(
    task_type: TaskType,
    task_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> TimerTaskItem:
    items = await _build_all_items()
    for item in items:
        if item.task_type == task_type and item.id == task_id:
            return item
    raise NotFoundError(resource=f"定时任务 {task_id}")


@router.post("/{task_type}/{task_id}/run-now", response_model=ActionOkResponse, summary="立即执行定时任务")
async def run_timer_now(
    task_type: TaskType,
    task_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    if task_type == "one_shot":
        ok = await timer_service.trigger_timer_now(task_id)
    else:
        ok = await recurring_timer.run_now(task_id)
    if not ok:
        raise NotFoundError(resource=f"定时任务 {task_id}")
    return ActionOkResponse(ok=True, message="任务已执行")


@router.post("/{task_type}/{task_id}/pause", response_model=ActionOkResponse, summary="暂停周期定时任务")
async def pause_timer(
    task_type: TaskType,
    task_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    if task_type != "recurring":
        raise ValidationError(reason="一次性任务不支持暂停")
    await recurring_timer.pause_job(task_id)
    return ActionOkResponse(ok=True, message="任务已暂停")


@router.post("/{task_type}/{task_id}/resume", response_model=ActionOkResponse, summary="恢复周期定时任务")
async def resume_timer(
    task_type: TaskType,
    task_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    if task_type != "recurring":
        raise ValidationError(reason="一次性任务不支持恢复")
    await recurring_timer.resume_job(task_id)
    return ActionOkResponse(ok=True, message="任务已恢复")


@router.delete("/{task_type}/{task_id}", response_model=ActionOkResponse, summary="删除定时任务")
async def delete_timer(
    task_type: TaskType,
    task_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    if task_type == "one_shot":
        ok = await timer_service.delete_timer_by_id(task_id)
        if not ok:
            raise NotFoundError(resource=f"定时任务 {task_id}")
    else:
        await recurring_timer.delete_job(task_id)
    return ActionOkResponse(ok=True, message="任务已删除")
