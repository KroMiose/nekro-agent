"""
# 工作区知识库工具插件 (kb_tools)

为绑定工作区的主 Agent 提供知识库检索、全文阅读和源文件获取能力。
"""

from . import main
from .plugin import plugin

__all__ = ["plugin", "main"]
