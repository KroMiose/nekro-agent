"""内置命令自动注册"""

from nekro_agent.services.command.registry import command_registry

from .chat import InspectCommand, ResetCommand, StopCommand
from .config_cmd import ConfReloadCommand, ConfSaveCommand, ConfSetCommand, ConfShowCommand
from .debug import CodeLogCommand, DebugOffCommand, DebugOnCommand, ExecCommand, LogChatTestCommand, SystemCommand
from .info import NaHelpCommand, NaInfoCommand
from .model import ModelTestCommand
from .ops import (
    ClearSandboxCacheCommand,
    DockerLogsCommand,
    DockerRestartCommand,
    GithubStarsCheckCommand,
    InstanceIdCommand,
    LogErrListCommand,
    ShCommand,
)
from .plugin_cmd import NaPluginsCommand, PluginInfoCommand, ResetPluginCommand
from .quota_cmd import QuotaBoostCommand, QuotaCommand, QuotaResetCommand, QuotaSetCommand, QuotaWhitelistCommand
from .switch import NaOffCommand, NaOnCommand


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
        # 开关类
        NaOnCommand(),
        NaOffCommand(),
        # 配置类
        ConfShowCommand(),
        ConfSetCommand(),
        ConfReloadCommand(),
        ConfSaveCommand(),
        # 调试类
        ExecCommand(),
        CodeLogCommand(),
        SystemCommand(),
        DebugOnCommand(),
        DebugOffCommand(),
        LogChatTestCommand(),
        # 插件类
        NaPluginsCommand(),
        PluginInfoCommand(),
        ResetPluginCommand(),
        # 运维类
        ClearSandboxCacheCommand(),
        DockerRestartCommand(),
        DockerLogsCommand(),
        ShCommand(),
        InstanceIdCommand(),
        GithubStarsCheckCommand(),
        LogErrListCommand(),
        # 配额类
        QuotaCommand(),
        QuotaBoostCommand(),
        QuotaResetCommand(),
        QuotaSetCommand(),
        QuotaWhitelistCommand(),
        # 模型类
        ModelTestCommand(),
    ]
    for cmd in commands:
        command_registry.register(cmd)
