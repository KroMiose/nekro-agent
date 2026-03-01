"""内置命令自动注册"""

from nekro_agent.services.command.registry import command_registry

from .chat import InspectCommand, ResetCommand, StopCommand
from .info import NaHelpCommand, NaInfoCommand


def register_built_in_commands() -> None:
    """注册所有内置命令"""
    commands = [
        # 会话类
        ResetCommand(),
        StopCommand(),
        InspectCommand(),
        # 信息类
        NaInfoCommand(),
        NaHelpCommand(),
    ]
    for cmd in commands:
        command_registry.register(cmd)
