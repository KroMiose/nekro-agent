from typing import Optional, Tuple

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qdrant_models

from .args import Args
from .config import config
from .logger import logger
from .os_env import OsEnv

_qdrant_client: Optional[AsyncQdrantClient] = None


class QdrantConfig(BaseModel):
    url: str
    api_key: Optional[str]


def get_qdrant_config() -> QdrantConfig:
    """获取 Qdrant 配置"""
    if OsEnv.RUN_IN_DOCKER:
        QDRANT_URL = OsEnv.QDRANT_URL
        QDRANT_API_KEY = OsEnv.QDRANT_API_KEY
    else:
        QDRANT_URL = config.QDRANT_URL
        QDRANT_API_KEY = config.QDRANT_API_KEY
    return QdrantConfig(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)


async def get_qdrant_client() -> AsyncQdrantClient:
    """获取或初始化Qdrant客户端"""
    global _qdrant_client

    if Args.LOAD_TEST:
        logger.warning("在测试模式下，不启用 Qdrant 数据库")
        return None  # type: ignore

    if _qdrant_client is None:
        qdrant_config = get_qdrant_config()
        _qdrant_client = AsyncQdrantClient(
            url=qdrant_config.url,
            api_key=qdrant_config.api_key,
        )
    return _qdrant_client
