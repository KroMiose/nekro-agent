from nekro_agent.core.logger import get_sub_logger
from nekro_agent.systems.cloud.schemas.announcement import AnnouncementDetailResponse, AnnouncementLatestResponse

from .client import get_client

logger = get_sub_logger("cloud_api")


async def get_latest_announcements(limit: int = 5) -> AnnouncementLatestResponse:
    """获取最新公告摘要

    Args:
        limit: 返回数量，最大 10

    Returns:
        AnnouncementLatestResponse: 包含最新公告摘要的响应
    """
    try:
        async with get_client() as client:
            response = await client.get(
                url="/api/v2/announcement/latest",
                params={"limit": min(limit, 10)},
            )
            response.raise_for_status()
            return AnnouncementLatestResponse(**response.json())
    except Exception as e:
        logger.error(f"获取最新公告失败: {e}")
        return AnnouncementLatestResponse.process_exception(e)


async def get_announcement_detail(announcement_id: str) -> AnnouncementDetailResponse:
    """获取公告详情

    Args:
        announcement_id: 公告 ID

    Returns:
        AnnouncementDetailResponse: 包含公告详情的响应
    """
    try:
        async with get_client() as client:
            response = await client.get(url=f"/api/v2/announcement/{announcement_id}")
            response.raise_for_status()
            return AnnouncementDetailResponse(**response.json())
    except Exception as e:
        logger.error(f"获取公告详情失败: {e}")
        return AnnouncementDetailResponse.process_exception(e)
