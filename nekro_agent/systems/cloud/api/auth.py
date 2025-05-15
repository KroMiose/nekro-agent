from nekro_agent.core.logger import logger
from nekro_agent.systems.cloud.schemas.auth import StarCheckResponse

from .client import get_client


async def check_official_repos_starred() -> StarCheckResponse:
    """检查用户是否已给官方GitHub仓库点亮Star

    返回用户已Star和未Star的仓库列表，以及是否已Star所有指定仓库

    Returns:
        StarCheckResponse: 包含Star状态的响应结果
    """
    try:
        async with get_client(require_auth=True) as client:
            response = await client.get(
                url="/api/auth/official-repos-starred",
            )
            response.raise_for_status()
            return StarCheckResponse(**response.json())
    except Exception as e:
        logger.error(f"检查GitHub仓库Star状态发生错误: {e}")
        return StarCheckResponse.process_exception(e)
