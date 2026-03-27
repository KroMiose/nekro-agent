"""旧版 guard 模块兼容层 — 所有导出已迁移至 command 模块。"""

from nekro_agent.adapters.onebot_v11.matchers.command import (  # noqa: F401
    command_guard,
    finish_with,
    reset_command_guard,
)

__all__ = [
    "command_guard",
    "finish_with",
    "reset_command_guard",
]
