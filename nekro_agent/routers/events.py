"""全局系统事件 SSE 端点"""

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from nekro_agent.models.db_user import DBUser
from nekro_agent.services.system_broadcast import (
    subscribe_system_events,
    unsubscribe_system_events,
)
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("/stream", summary="全局系统事件实时推送（SSE）")
@require_role(Role.Admin)
async def stream_system_events(
    _current_user: DBUser = Depends(get_current_active_user),
) -> EventSourceResponse:
    """订阅全局系统事件流（工作区状态变化、CC 沙盒活动状态等）。

    事件格式（JSON）：
    - type=workspace_status: {type, workspace_id, status, name}
    - type=workspace_cc_active: {type, workspace_id, active, max_duration_ms}
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        q = subscribe_system_events()
        if q is None:
            yield '{"type":"error","message":"连接数已达上限，请稍后重试"}'
            return
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield payload
                except asyncio.TimeoutError:
                    yield ": ping"  # SSE keep-alive
        finally:
            unsubscribe_system_events(q)

    return EventSourceResponse(event_generator())
