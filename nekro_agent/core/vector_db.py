from typing import Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qdrant_models

from .args import Args
from .config import config
from .logger import logger
from .os_env import OsEnv

_qdrant_client: Optional[AsyncQdrantClient] = None


async def get_qdrant_client() -> AsyncQdrantClient:
    """获取或初始化Qdrant客户端"""
    global _qdrant_client

    if Args.LOAD_TEST:
        logger.warning("在测试模式下，不启用 Qdrant 数据库")
        return None  # type: ignore

    if OsEnv.RUN_IN_DOCKER:
        QDRANT_HOST = OsEnv.QDRANT_HOST
        QDRANT_PORT = OsEnv.QDRANT_PORT
        QDRANT_API_KEY = OsEnv.QDRANT_API_KEY
    else:
        QDRANT_HOST = config.QDRANT_HOST
        QDRANT_PORT = config.QDRANT_PORT
        QDRANT_API_KEY = config.QDRANT_API_KEY

    if _qdrant_client is None:
        _qdrant_client = AsyncQdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT,
            api_key=QDRANT_API_KEY,
        )
    return _qdrant_client
