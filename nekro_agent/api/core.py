"""核心功能 API

此模块提供了 Nekro-Agent 的核心功能 API 接口。
"""

from nekro_agent.core import logger
from nekro_agent.core.bot import get_bot
from nekro_agent.core.config import config
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import MethodType, agent_collector

__all__ = [
    "ExtMetaData",
    "MethodType",
    "agent_collector",
    "config",
    "get_bot",
    "logger",
] 