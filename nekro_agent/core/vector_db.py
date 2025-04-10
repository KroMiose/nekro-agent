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
    host: str
    port: int
    api_key: Optional[str]


def get_qdrant_config() -> QdrantConfig:
    """获取 Qdrant 配置"""
    if OsEnv.RUN_IN_DOCKER:
        QDRANT_HOST = OsEnv.QDRANT_HOST
        QDRANT_PORT = OsEnv.QDRANT_PORT
        QDRANT_API_KEY = OsEnv.QDRANT_API_KEY
    else:
        QDRANT_HOST = config.QDRANT_HOST
        QDRANT_PORT = config.QDRANT_PORT
        QDRANT_API_KEY = config.QDRANT_API_KEY
    return QdrantConfig(host=QDRANT_HOST, port=QDRANT_PORT, api_key=QDRANT_API_KEY or None)


async def get_qdrant_client() -> AsyncQdrantClient:
    """获取或初始化Qdrant客户端"""
    global _qdrant_client

    if Args.LOAD_TEST:
        logger.warning("在测试模式下，不启用 Qdrant 数据库")
        return None  # type: ignore

    if _qdrant_client is None:
        qdrant_config = get_qdrant_config()
        _qdrant_client = AsyncQdrantClient(
            host=qdrant_config.host,
            port=qdrant_config.port,
            api_key=qdrant_config.api_key,
        )
    return _qdrant_client
