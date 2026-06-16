from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.models.db_user import DBUser
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role


class QQBotOpenClawStatus(BaseModel):
    configured: bool
    running: bool
    connected: bool
    app_id: str
    session_id: str | None = None
    last_seq: int | None = None
    self_user_id: str | None = None
    last_connected_at: float | None = None
    last_error: str | None = None
    ref_index_entries: int = 0
    onboarding_url: str = "https://q.qq.com/qqbot/openclaw/index.html"
    onboarding_qr_url: str = "https://q.qq.com/qqbot/openclaw/index.html"


class QQBotOpenClawActionResult(BaseModel):
    success: bool
    message: str
    detail: dict[str, Any] | None = None


def create_router(
    *,
    get_status: Callable[[], Awaitable[dict[str, Any]]],
    restart_gateway: Callable[[], Awaitable[dict[str, Any]]],
    clear_ref_index: Callable[[], Awaitable[dict[str, Any]]],
    clear_session: Callable[[], Awaitable[dict[str, Any]]],
    test_token: Callable[[], Awaitable[dict[str, Any]]],
) -> APIRouter:
    router = APIRouter(prefix="/maintenance", tags=["QQBot OpenClaw Maintenance"])

    @router.get("/status")
    @require_role(Role.User)
    async def status(_current_user: DBUser = Depends(get_current_active_user)) -> QQBotOpenClawStatus:
        return QQBotOpenClawStatus.model_validate(await get_status())

    @router.post("/restart")
    @require_role(Role.Admin)
    async def restart(_current_user: DBUser = Depends(get_current_active_user)) -> QQBotOpenClawActionResult:
        return QQBotOpenClawActionResult.model_validate(await restart_gateway())

    @router.post("/clear-ref-index")
    @require_role(Role.Admin)
    async def clear_refs(_current_user: DBUser = Depends(get_current_active_user)) -> QQBotOpenClawActionResult:
        return QQBotOpenClawActionResult.model_validate(await clear_ref_index())

    @router.post("/clear-session")
    @require_role(Role.Admin)
    async def session_clear(_current_user: DBUser = Depends(get_current_active_user)) -> QQBotOpenClawActionResult:
        return QQBotOpenClawActionResult.model_validate(await clear_session())

    @router.post("/test-token")
    @require_role(Role.Admin)
    async def token_test(_current_user: DBUser = Depends(get_current_active_user)) -> QQBotOpenClawActionResult:
        return QQBotOpenClawActionResult.model_validate(await test_token())

    return router
