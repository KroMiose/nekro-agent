"""核心功能 API

此模块提供了 Nekro-Agent 的核心功能 API 接口。
"""

from nekro_agent.core import logger
from nekro_agent.core.bot import get_bot
from nekro_agent.core.config import config

__all__ = [
    "config",
    "get_bot",
    "logger",
]
