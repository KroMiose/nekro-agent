"""小说自动发布插件入口"""

from . import handlers
from .plugin import plugin

__all__ = ["plugin", "handlers"]
