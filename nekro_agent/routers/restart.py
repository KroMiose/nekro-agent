from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import OperationFailedError
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.tools.docker_util import restart_self

logger = get_sub_logger("system_control")
router = APIRouter(prefix="/restart", tags=["Restart"])


class ActionResponse(BaseModel):
    ok: bool = True


@router.post("", summary="重启系统")
@require_role(Role.Admin)
async def restart_system(
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """重启整个系统服务"""
    if OsEnv.RUN_IN_DOCKER:
        logger.info("在Docker环境中执行重启操作")
        result = await restart_self()
        if result:
            return ActionResponse(ok=True)
        raise OperationFailedError(operation="重启系统")
    logger.info("在非Docker环境中执行重启操作")
    raise OperationFailedError(operation="重启系统")
