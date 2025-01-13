from asyncio import Queue
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from jose import JWTError, jwt
from sse_starlette.sse import EventSourceResponse

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_log_records, get_log_sources, logger, subscribe_logs
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.systems.user.auth import get_user_from_token
from nekro_agent.systems.user.deps import get_current_active_user
from nekro_agent.systems.user.perm import Role, require_role

router = APIRouter(prefix="/logs", tags=["Logs"])

# 基础日志来源
DEFAULT_LOG_SOURCES = ["nonebot", "nekro_agent", "uvicorn"]

# 日志订阅者队列
subscribers: List[Queue] = []


@router.get("", summary="获取历史日志")
@require_role(Role.Admin)
async def get_logs(
    page: int = 1,
    page_size: int = 500,
    source: Optional[str] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取历史日志记录"""
    logs = await get_log_records(page, page_size, source)
    total = await get_log_records(1, 0, source, count_only=True)  # 获取总数
    return Ret.success(
        msg="获取成功",
        data={
            "logs": logs,
            "total": total,
        },
    )


@router.get("/sources", summary="获取日志来源列表")
@require_role(Role.Admin)
async def get_sources(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取所有日志来源"""
    sources = await get_log_sources()
    # 合并默认来源和实际来源
    all_sources = sorted(set(DEFAULT_LOG_SOURCES) | set(sources))
    return Ret.success(msg="获取成功", data=all_sources)


@router.get("/stream", summary="实时日志流")
@require_role(Role.Admin)
async def stream_logs(token: str, _current_user: DBUser = Depends(get_current_active_user)) -> EventSourceResponse:
    """获取实时日志流"""
    try:
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
    except Exception as e:
        logger.error(f"日志流异常: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))
