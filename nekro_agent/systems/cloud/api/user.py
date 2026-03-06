from nekro_agent.core.logger import get_sub_logger
from nekro_agent.systems.cloud.schemas.user import CommunityUserResponse

from .client import get_client

logger = get_sub_logger("cloud_api")


async def get_community_user_profile() -> CommunityUserResponse:
    """获取社区用户信息

    Returns:
        CommunityUserResponse: 包含社区用户数据的响应
    """
    try:
        async with get_client(require_auth=True) as client:
            response = await client.get(url="/api/v2/user")
            response.raise_for_status()
            return CommunityUserResponse(**response.json())
    except Exception as e:
        logger.error(f"获取社区用户信息失败: {e}")
        return CommunityUserResponse.process_exception(e)
