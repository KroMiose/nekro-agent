"""GitHub插件模块

接收GitHub webhook消息并处理，支持订阅仓库消息
"""

from . import handlers, methods, models
from .plugin import plugin

__all__ = ["plugin"]
