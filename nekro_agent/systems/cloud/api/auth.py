import asyncio
import random

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.systems.cloud.schemas.auth import StarCheckResponse

from .base import parse_json_response
from .client import get_client

logger = get_sub_logger("cloud_api")
async def check_official_repos_starred() -> StarCheckResponse:
    """检查用户是否已给官方GitHub仓库点亮Star

    返回用户已Star和未Star的仓库列表，以及是否已Star所有指定仓库

    Returns:
        StarCheckResponse: 包含Star状态的响应结果
    """
    try:
        async with get_client(require_auth=True) as client:
            for attempt in range(2):
                try:
                    response = await client.get(
                        url="/api/auth/official-repos-starred",
                    )
                    response.raise_for_status()

                    return parse_json_response(response, StarCheckResponse, "检查GitHub仓库Star状态")
                except ValueError as e:
                    # 空响应时尝试重试
                    if attempt == 0 and "empty" in str(e).lower():
                        backoff = 0.2 + random.random() * 0.3
                        logger.warning(
                            f"检查GitHub仓库Star状态返回空响应，将在 {backoff:.3f} 秒后重试...",
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise
    except Exception as e:
        logger.error(f"检查GitHub仓库Star状态发生错误: {e}")
        return StarCheckResponse.process_exception(e)
