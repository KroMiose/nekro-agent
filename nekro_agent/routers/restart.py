import asyncio

from fastapi import APIRouter, Depends

from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.tools.docker_util import restart_self

router = APIRouter(prefix="/restart", tags=["Restart"])


@router.post("", summary="重启系统")
@require_role(Role.Admin)
async def restart_system(
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """重启整个系统服务"""

    try:
        # 执行重启操作
        if OsEnv.RUN_IN_DOCKER:
            logger.info("在Docker环境中执行重启操作")
            result = await restart_self()
            if result:
                return Ret.success(msg="重启命令已发送")
            return Ret.error(msg="重启命令发送失败")
        logger.info("在非Docker环境中执行重启操作")
        return Ret.error(msg="非Docker环境下无法自动重启，请手动重启应用")
    except Exception as e:
        logger.error(f"重启系统失败: {e}")
        return Ret.error(msg=f"重启失败: {e!s}")
