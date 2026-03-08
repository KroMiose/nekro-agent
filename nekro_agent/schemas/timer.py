from typing import Literal, Optional

from pydantic import BaseModel

TimerTaskType = Literal["one_shot", "recurring"]
TimerTaskStatus = Literal["active", "paused", "error"]
TimerTaskSource = Literal["agent", "system", "unknown"]


class TimerTaskItem(BaseModel):
    id: str
    task_type: TimerTaskType
    title: str
    event_desc: str
    status: TimerTaskStatus
    workspace_id: Optional[int] = None
    workspace_name: Optional[str] = None
    chat_key: str
    channel_name: Optional[str] = None
    is_primary_channel: bool = False
    trigger_at: Optional[str] = None
    cron_expr: Optional[str] = None
    timezone: Optional[str] = None
    workday_mode: Optional[str] = None
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    source: TimerTaskSource = "unknown"
    is_temporary: bool = False
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    actionable: bool = True


class TimerTaskListResponse(BaseModel):
    total: int
    items: list[TimerTaskItem]


class TimerTaskSummary(BaseModel):
    total: int
    active_recurring: int
    paused: int
    upcoming_24h: int
    errors: int
    workspace_count: int


class ActionOkResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None
