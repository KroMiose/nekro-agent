import asyncio
import random

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.systems.cloud.schemas.auth import StarCheckResponse

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
                response = await client.get(
                    url="/api/auth/official-repos-starred",
                )
                response.raise_for_status()

                response_text = response.text.strip()
                if not response_text:
                    logger.warning(
                        f"检查GitHub仓库Star状态返回空响应，第 {attempt + 1} 次尝试，status={response.status_code}",
                    )
                    if attempt == 0:
                        # 轻微退避 + 抖动，避免紧密循环打满上游
                        backoff = 0.2 + random.random() * 0.3
                        logger.debug(
                            f"空响应后将在 {backoff:.3f} 秒后重试 GitHub 仓库 Star 状态请求",
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise ValueError(f"empty response body, status={response.status_code}")

                content_type = response.headers.get("content-type", "")
                if "json" not in content_type.lower():
                    logger.warning(
                        f"检查GitHub仓库Star状态返回非JSON响应，content-type={content_type}, body={response_text[:200]}",
                    )

                return StarCheckResponse.model_validate_json(response_text)
    except Exception as e:
        logger.error(f"检查GitHub仓库Star状态发生错误: {e}")
        return StarCheckResponse.process_exception(e)
