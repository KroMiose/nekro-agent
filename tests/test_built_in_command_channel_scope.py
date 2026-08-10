from nekro_agent.services.command.base import CommandPermission
from nekro_agent.services.command.built_in._scope import resolve_channel_target
from nekro_agent.services.command.built_in.chat import ResetCommand, StopCommand
from nekro_agent.services.command.built_in.config_cmd import (
    ConfReloadCommand,
    ConfSaveCommand,
    ConfSetCommand,
    ConfShowCommand,
)
from nekro_agent.services.command.built_in.debug import ExecCommand
from nekro_agent.services.command.built_in.ops import DockerLogsCommand, DockerRestartCommand, ShCommand
from nekro_agent.services.command.built_in.switch import NaObserveCommand, NaOffCommand, NaOnCommand
from nekro_agent.services.command.schemas import CommandExecutionContext, CommandResponseStatus


def _context(*, is_super_user: bool = False) -> CommandExecutionContext:
    return CommandExecutionContext(
        user_id="platform-user",
        chat_key="group_1",
        username="tester",
        adapter_key="fake",
        is_super_user=is_super_user,
        is_advanced_user=not is_super_user,
    )


def test_channel_state_commands_are_advanced_permission() -> None:
    commands = [
        ResetCommand(),
        StopCommand(),
        NaOnCommand(),
        NaOffCommand(),
        NaObserveCommand(),
    ]

    assert [command.metadata.permission for command in commands] == [CommandPermission.ADVANCED] * len(commands)


def test_sensitive_commands_are_super_user_permission() -> None:
    commands = [
        ExecCommand(),
        DockerRestartCommand(),
        DockerLogsCommand(),
        ShCommand(),
        ConfShowCommand(),
        ConfSetCommand(),
        ConfReloadCommand(),
        ConfSaveCommand(),
    ]

    assert [command.metadata.permission for command in commands] == [CommandPermission.SUPER_USER] * len(commands)


def test_advanced_user_channel_target_defaults_to_current_channel() -> None:
    target_chat_key, error_response = resolve_channel_target(_context(), "")

    assert target_chat_key == "group_1"
    assert error_response is None


def test_advanced_user_can_explicitly_target_current_channel() -> None:
    target_chat_key, error_response = resolve_channel_target(_context(), "group_1")

    assert target_chat_key == "group_1"
    assert error_response is None


def test_advanced_user_cannot_target_other_channel() -> None:
    target_chat_key, error_response = resolve_channel_target(_context(), "group_2")

    assert target_chat_key is None
    assert error_response is not None
    assert error_response.status == CommandResponseStatus.ERROR


def test_advanced_user_cannot_use_bulk_target() -> None:
    target_chat_key, error_response = resolve_channel_target(_context(), "*")

    assert target_chat_key is None
    assert error_response is not None
    assert error_response.status == CommandResponseStatus.ERROR


def test_super_user_can_use_bulk_target() -> None:
    target_chat_key, error_response = resolve_channel_target(_context(is_super_user=True), "*")

    assert target_chat_key == "*"
    assert error_response is None
