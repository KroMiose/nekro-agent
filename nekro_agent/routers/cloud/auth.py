import time
from typing import Dict

from fastapi import APIRouter, Depends, Query

from nekro_agent.core.logger import logger
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.systems.cloud.api.auth import check_official_repos_starred

router = APIRouter(prefix="/cloud/auth", tags=["Cloud Authentication"])

# 内存缓存
_star_cache: Dict[str, Dict] = {}
# 未star状态的缓存过期时间（秒）
_UNSTARRED_CACHE_EXPIRES = 5  # 5 秒
# 已star状态的缓存过期时间（秒）
_STARRED_CACHE_EXPIRES = 86400  # 24小时


def clear_star_status_cache() -> None:
    """清除GitHub Star状态缓存"""
    global _star_cache
    _star_cache.pop("star_status", None)


@router.get("/github-stars")
async def check_github_stars(
    force: bool = Query(False, description="是否强制检查（忽略缓存）"),
    clear_cache: bool = Query(False, description="是否清除缓存后再检查"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """检查用户是否已Star官方GitHub仓库"""

    if clear_cache:
        clear_star_status_cache()

    # 检查缓存
    if not force and "star_status" in _star_cache:
        cached_data = _star_cache["star_status"]
        current_time = time.time()

        # 检查缓存是否过期
        if current_time < cached_data.get("expires_at", 0):
            return Ret.success(msg="获取缓存的GitHub Star状态成功", data=cached_data["data"])

    # 调用云服务API检查
    result = await check_official_repos_starred()

    if not result.success:
        return Ret.fail(msg=f"检查GitHub Stars状态失败: {result.message}")

    # 设置缓存
    if result.data:
        current_time = time.time()
        all_starred = result.data.all_starred
        # 根据是否所有仓库都被star来决定缓存过期时间
        expires_at = current_time + (_STARRED_CACHE_EXPIRES if all_starred else _UNSTARRED_CACHE_EXPIRES)

        _star_cache["star_status"] = {
            "data": result.data.dict(by_alias=True),
            "expires_at": expires_at,
            "timestamp": current_time,
        }

        logger.debug(f"已缓存 GitHub Star状态 {all_starred}，过期时间: {int(expires_at - current_time)} 秒")

    return Ret.success(msg="检查GitHub Stars状态成功", data=result.data)
