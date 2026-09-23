from types import SimpleNamespace
from typing import Annotated, Any

import pytest

from nekro_agent.adapters.interface.base import BaseAdapter
from nekro_agent.core.config import config
from nekro_agent.routers.commands import router
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.built_in.config_cmd import (
    ConfReloadCommand,
    ConfSaveCommand,
    ConfSetCommand,
    ConfShowCommand,
)
from nekro_agent.services.command.built_in.debug import ExecCommand
from nekro_agent.services.command.built_in.ops import (
    ClearSandboxCacheCommand,
    DockerLogsCommand,
    DockerRestartCommand,
    ShCommand,
)
from nekro_agent.services.command.manager import CommandManager
from nekro_agent.services.command.parser import ArgumentParser
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse
from nekro_agent.services.user.deps import get_current_active_user


class _NoopCommand(BaseCommand):
    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="noop",
            description="noop",
            permission=CommandPermission.SUPER_USER,
        )

    async def execute(self, context: CommandExecutionContext, **kwargs: Any) -> CommandResponse:
        del context, kwargs
        raise NotImplementedError


def _parse_mixed_args(
    context: CommandExecutionContext,
    value: Annotated[int, Arg("整数", positional=True)],
    label: str = "default",
) -> None:
    del context, value, label


def _parse_bool_arg(context: CommandExecutionContext, enabled: bool) -> None:
    del context, enabled


def _super_user_context() -> CommandExecutionContext:
    return CommandExecutionContext(
        user_id="admin",
        chat_key="fake-channel",
        username="admin",
        adapter_key="fake",
        is_super_user=True,
        is_advanced_user=True,
    )


def test_adapter_command_detection_respects_global_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = SimpleNamespace(config=SimpleNamespace(COMMAND_ENABLED=True, COMMAND_PREFIX="/"))
    monkeypatch.setattr(config, "COMMAND_ENABLED", False)

    assert BaseAdapter.detect_command(adapter, "/noop") is None


def test_adapter_command_detection_respects_adapter_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = SimpleNamespace(config=SimpleNamespace(COMMAND_ENABLED=False, COMMAND_PREFIX="/"))
    monkeypatch.setattr(config, "COMMAND_ENABLED", True)

    assert BaseAdapter.detect_command(adapter, "/noop") is None


def test_command_manager_respects_global_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "COMMAND_ENABLED", False)
    manager = CommandManager.__new__(CommandManager)

    assert manager.is_command_enabled("noop") is False


def test_sensitive_built_in_commands_are_guarded_by_advanced_switch() -> None:
    commands = [
        ExecCommand(),
        ConfShowCommand(),
        ConfSetCommand(),
        ConfReloadCommand(),
        ConfSaveCommand(),
        ClearSandboxCacheCommand(),
        DockerRestartCommand(),
        DockerLogsCommand(),
        ShCommand(),
    ]

    assert all(command.metadata.requires_advanced_command for command in commands)


@pytest.mark.asyncio
async def test_high_risk_command_requires_advanced_command_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "ENABLE_ADVANCED_COMMAND", False)
    command = ExecCommand()

    allowed, error = await command.check_permission(_super_user_context())

    assert allowed is False
    assert error is not None
    manager = CommandManager.__new__(CommandManager)
    assert manager.is_command_enabled_for_meta(command.metadata) is False


@pytest.mark.asyncio
async def test_regular_super_user_command_ignores_advanced_command_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "ENABLE_ADVANCED_COMMAND", False)
    command = _NoopCommand()

    allowed, error = await command.check_permission(_super_user_context())

    assert allowed is True
    assert error is None


def test_parser_rejects_extra_positional_arguments() -> None:
    with pytest.raises(ValueError, match="多余参数"):
        ArgumentParser.parse(_parse_mixed_args, "7 extra")


@pytest.mark.parametrize("raw_value", ["true", "1", "yes", "on"])
def test_parser_accepts_explicit_true_values(raw_value: str) -> None:
    assert ArgumentParser.parse(_parse_bool_arg, f"enabled:{raw_value}") == {"enabled": True}


@pytest.mark.parametrize("raw_value", ["false", "0", "no", "off"])
def test_parser_accepts_explicit_false_values(raw_value: str) -> None:
    assert ArgumentParser.parse(_parse_bool_arg, f"enabled:{raw_value}") == {"enabled": False}


def test_parser_rejects_invalid_bool_value() -> None:
    with pytest.raises(ValueError, match="布尔值"):
        ArgumentParser.parse(_parse_bool_arg, "enabled:maybe")


def test_channel_state_path_cannot_escape_base_directory(tmp_path) -> None:
    state_path = CommandManager._channel_state_path(str(tmp_path), "../../outside")

    assert state_path.parent == tmp_path
    assert state_path.name.startswith("channel-")
    assert state_path.suffix == ".json"


def test_channel_state_path_preserves_existing_safe_names(tmp_path) -> None:
    state_path = CommandManager._channel_state_path(str(tmp_path), "onebot_v11-group_123")

    assert state_path == tmp_path / "onebot_v11-group_123.json"


def test_command_metadata_routes_require_authentication() -> None:
    protected_paths = {"/commands/completions", "/commands/tools"}
    routes = {route.path: route for route in router.routes if getattr(route, "path", None) in protected_paths}

    assert set(routes) == protected_paths
    for route in routes.values():
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        assert get_current_active_user in dependency_calls
