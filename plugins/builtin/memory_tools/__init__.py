"""
# 主动记忆工具插件 (memory_tools)

为绑定工作区的主 Agent 提供主动检索结构化记忆、展开记忆详情与追溯来源的只读能力。
"""

from . import main
from .plugin import plugin

__all__ = ["plugin", "main"]
