from fastapi import APIRouter, Depends

from nekro_agent.core.logger import logger
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.systems.cloud.api.telemetry import get_community_stats

router = APIRouter(prefix="/cloud/telemetry", tags=["Cloud Telemetry"])


@router.get("/community-stats", summary="获取社区统计数据")
@require_role(Role.Admin)
async def get_community_stats_api(
    force_refresh: bool = False,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取社区统计数据

    Args:
        force_refresh: 是否强制刷新缓存
        _current_user: 当前用户

    Returns:
        Ret: 返回结果
    """
    stats = await get_community_stats(force_refresh=force_refresh)

    if stats is None:
        return Ret.fail(msg="获取社区统计数据失败")

    return Ret.success(msg="获取社区统计数据成功", data=stats)
