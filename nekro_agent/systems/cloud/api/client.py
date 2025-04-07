import httpx

from nekro_agent.core.config import config
from nekro_agent.core.os_env import OsEnv
from nekro_agent.systems.cloud.exceptions import (
    NekroCloudAPIKeyInvalid,
    NekroCloudDisabled,
)


def get_client(require_auth: bool = False) -> httpx.AsyncClient:
    """获取 HTTP 客户端

    Returns:
        httpx.AsyncClient: HTTP 客户端
    """
    if require_auth:
        if not OsEnv.NEKRO_CLOUD_API_BASE_URL or not config.ENABLE_NEKRO_CLOUD:
            raise NekroCloudDisabled
        if not config.NEKRO_CLOUD_API_KEY:
            raise NekroCloudAPIKeyInvalid
    return httpx.AsyncClient(
        base_url=OsEnv.NEKRO_CLOUD_API_BASE_URL,
        headers={
            "X-API-Key": f"{config.NEKRO_CLOUD_API_KEY}",
            "Content-Type": "application/json",
        },
    )
