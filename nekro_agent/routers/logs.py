from asyncio import Queue
from datetime import datetime
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from nekro_agent.core.logger import (
    get_log_records,
    get_log_sources,
    subscribers,
)
from nekro_agent.models.db_user import DBUser
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/logs", tags=["Logs"])

# 基础日志来源
DEFAULT_LOG_SOURCES = ["nonebot", "nekro_agent", "uvicorn"]


class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    source: str
    function: str
    line: int
    subsystem: Optional[str] = None
    plugin_key: Optional[str] = None


class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total: int


@router.get("", summary="获取历史日志", response_model=LogsResponse)
@require_role(Role.Admin)
async def get_logs(
    page: int = 1,
    page_size: int = 500,
    source: Optional[str] = None,
    subsystem: Optional[str] = None,
    plugin_key: Optional[str] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> LogsResponse:
    """获取历史日志记录"""
    logs = await get_log_records(page, page_size, source, count_only=False, subsystem=subsystem, plugin_key=plugin_key)
    total = await get_log_records(1, 0, source, count_only=True, subsystem=subsystem, plugin_key=plugin_key)

    assert isinstance(logs, list)
    assert isinstance(total, int)

    return LogsResponse(logs=[LogEntry(**log) for log in logs], total=total)


@router.get("/sources", summary="获取日志来源列表", response_model=List[str])
@require_role(Role.Admin)
async def get_sources(_current_user: DBUser = Depends(get_current_active_user)) -> List[str]:
    """获取所有日志来源"""
    sources = await get_log_sources()
    return sorted(set(DEFAULT_LOG_SOURCES) | set(sources))


@router.get("/stream", summary="实时日志流")
@require_role(Role.Admin)
async def stream_logs(_current_user: DBUser = Depends(get_current_active_user)) -> EventSourceResponse:
    """获取实时日志流"""

    async def event_generator() -> AsyncGenerator[str, None]:
        queue: Queue = Queue()
        subscribers.append(queue)
        try:
            while True:
                message = await queue.get()
                yield message
        finally:
            subscribers.remove(queue)

    return EventSourceResponse(event_generator())


@router.get("/download", summary="下载最近日志")
@require_role(Role.Admin)
async def download_logs(
    lines: int = 1000,
    source: Optional[str] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Response:
    """下载最近的日志文件

    Args:
        lines: 要下载的日志行数
        source: 日志来源过滤

    Returns:
        日志文件下载响应
    """
    max_lines = min(lines, 10000)

    logs = await get_log_records(page=1, page_size=max_lines, source=source, count_only=False)
    if not isinstance(logs, list):
        logs = []

    log_text = ""
    for log in logs:
        log_text += (
            f"[{log['timestamp']}] [{log['level']}] {log['source']} | {log['function']}:{log['line']} | {log['message']}\n"
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source_part = f"_{source}" if source else ""
    filename = f"nekro_agent_logs{source_part}_{timestamp}.txt"

    response = Response(content=log_text, media_type="text/plain")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
