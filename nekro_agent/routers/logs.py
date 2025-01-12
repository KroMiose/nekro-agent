from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from sse_starlette.sse import EventSourceResponse

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_log_records, get_log_sources, subscribe_logs
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.message import Ret
from nekro_agent.systems.user.auth import get_user_from_token
from nekro_agent.systems.user.deps import get_current_active_user

router = APIRouter(prefix="/logs", tags=["Logs"])

# 基础日志来源
DEFAULT_LOG_SOURCES = ["nonebot", "nekro_agent", "uvicorn"]


@router.get("", summary="获取历史日志")
async def get_logs(
    page: int = 1,
    page_size: int = 500,
    source: Optional[str] = None,
    _=Depends(get_current_active_user),
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
async def get_sources(_=Depends(get_current_active_user)) -> Ret:
    """获取所有日志来源"""
    sources = await get_log_sources()
    # 合并默认来源和实际来源
    all_sources = sorted(set(DEFAULT_LOG_SOURCES) | set(sources))
    return Ret.success(msg="获取成功", data=all_sources)


@router.get("/stream", summary="实时日志流")
async def stream_logs(token: Optional[str] = None) -> EventSourceResponse:
    """获取实时日志流"""
    if not token or not await get_user_from_token(token):
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    async def event_generator() -> AsyncGenerator[str, None]:
        async for log in subscribe_logs():
            yield log

    return EventSourceResponse(event_generator())
