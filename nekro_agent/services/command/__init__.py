"""命令系统

提供平台无关的命令注册、解析、执行和管理能力。
"""

from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission, PluginCommand
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import (
    Arg,
    CommandExecutionContext,
    CommandRequest,
    CommandResponse,
    CommandResponseStatus,
)

__all__ = [
    "Arg",
    "BaseCommand",
    "CmdCtl",
    "CommandExecutionContext",
    "CommandMetadata",
    "CommandPermission",
    "CommandRequest",
    "CommandResponse",
    "CommandResponseStatus",
    "PluginCommand",
]
