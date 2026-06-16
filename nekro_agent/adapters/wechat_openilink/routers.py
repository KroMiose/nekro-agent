from typing import Any, Callable

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.models.db_user import DBUser
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role


class OpenILinkLoginStatus(BaseModel):
    state: str
    logged_in: bool
    login_url: str | None = None
    error_message: str | None = None
    updated_at: float | None = None
    self_user_id: str | None = None
    self_user_name: str | None = None


def create_router(get_login_status: Callable[[], dict[str, Any]]) -> APIRouter:
    router = APIRouter(prefix="/login", tags=["WeChat OpenILink Login"])

    @router.get("/status")
    @require_role(Role.Admin)
    async def get_status(_current_user: DBUser = Depends(get_current_active_user)) -> OpenILinkLoginStatus:
        return OpenILinkLoginStatus.model_validate(get_login_status())

    return router
