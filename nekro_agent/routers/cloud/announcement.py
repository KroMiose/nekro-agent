import time
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Path, Query

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import CloudServiceError
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.systems.cloud.api.announcement import get_announcement_detail, get_latest_announcements
from nekro_agent.systems.cloud.api.telemetry import get_announcement_updated_at
from nekro_agent.systems.cloud.schemas.announcement import AnnouncementDetail, AnnouncementSummary

logger = get_sub_logger("cloud_api")
router = APIRouter(prefix="/cloud/announcement", tags=["Cloud Announcement"])

# 公告缓存（10分钟）
_announcement_cache: Dict[str, Dict] = {}
_ANNOUNCEMENT_CACHE_EXPIRES = 600
_DETAIL_CACHE_EXPIRES = 1800  # 详情缓存 30 分钟


@router.get("/updated-at")
async def announcement_updated_at(
    _current_user: DBUser = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """获取公告最后更新时间（由遥测响应缓存）"""
    return {"announcementUpdatedAt": get_announcement_updated_at()}


@router.get("/latest")
async def latest_announcements(
    limit: int = Query(5, ge=1, le=10, description="返回数量"),
    force: bool = Query(False, description="是否强制刷新"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> List[AnnouncementSummary]:
    """获取最新公告摘要"""

    cache_key = f"latest_{limit}"

    if not force and cache_key in _announcement_cache:
        cached = _announcement_cache[cache_key]
        if time.time() < cached.get("expires_at", 0):
            return [AnnouncementSummary.model_validate(item) for item in cached["data"]]

    result = await get_latest_announcements(limit)

    if not result.success:
        raise CloudServiceError(reason=str(result.message or result.error or "未知错误"))
    if result.data is None:
        raise CloudServiceError(reason="获取公告失败")

    current_time = time.time()
    _announcement_cache[cache_key] = {
        "data": [item.model_dump(by_alias=True) for item in result.data],
        "expires_at": current_time + _ANNOUNCEMENT_CACHE_EXPIRES,
    }

    return result.data


@router.get("/{announcement_id}")
async def announcement_detail(
    announcement_id: str = Path(description="公告 ID"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> AnnouncementDetail:
    """获取公告详情"""

    cache_key = f"detail_{announcement_id}"

    if cache_key in _announcement_cache:
        cached = _announcement_cache[cache_key]
        if time.time() < cached.get("expires_at", 0):
            return AnnouncementDetail.model_validate(cached["data"])

    result = await get_announcement_detail(announcement_id)

    if not result.success:
        raise CloudServiceError(reason=str(result.message or result.error or "未知错误"))
    if not result.data:
        raise CloudServiceError(reason="获取公告详情失败")

    current_time = time.time()
    _announcement_cache[cache_key] = {
        "data": result.data.model_dump(by_alias=True),
        "expires_at": current_time + _DETAIL_CACHE_EXPIRES,
    }

    return result.data
