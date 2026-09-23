from types import SimpleNamespace
from typing import Any, Optional

import pytest

from nekro_agent.adapters.interface import collector as collector_module
from nekro_agent.adapters.interface.base import BaseAdapter
from nekro_agent.adapters.interface.collector import _try_handle_command
from nekro_agent.adapters.interface.schemas.platform import PlatformChannel, PlatformMessage, PlatformUser
from nekro_agent.core.config import config
from nekro_agent.routers.commands import CommandStateResponse
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.command import registry as registry_module
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission, PluginCommand
from nekro_agent.services.command.manager import command_manager
from nekro_agent.services.command.registry import CommandRegexMatch, CommandRegistry
from nekro_agent.services.command.schemas import (
    CommandExecutionContext,
    CommandRequest,
    CommandResponse,
    CommandResponseStatus,
)
from nekro_agent.services.command.wait_manager import wait_manager


class _RegexCommand(BaseCommand):
    def __init__(
        self,
        name: str,
        patterns: list[str],
        *,
        source: str = "built_in",
        namespace: str = "built_in",
        permission: CommandPermission = CommandPermission.PUBLIC,
    ) -> None:
        self._name = name
        self._patterns = patterns
        self._source = source
        self._namespace = namespace
        self._permission = permission
        self.calls: list[tuple[str, int, bool]] = []

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name=self._name,
            namespace=self._namespace,
            description="regex test",
            regex_patterns=self._patterns,
            permission=self._permission,
            source=self._source,
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        location: str,
        days: int = 1,
        enabled: bool = False,
    ) -> CommandResponse:
        del context
        self.calls.append((location, days, enabled))
        return CommandResponse(status=CommandResponseStatus.SUCCESS, message="ok")


class _NoArgsRegexCommand(BaseCommand):
    def __init__(self, name: str, patterns: list[str]) -> None:
        self._name = name
        self._patterns = patterns

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(name=self._name, description="regex test", regex_patterns=self._patterns)

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        del context
        return CommandResponse(status=CommandResponseStatus.SUCCESS, message="ok")


class _CollectorAdapter:
    key = "fake"
    record_command_input = False

    def __init__(
        self,
        *,
        command: Optional[tuple[str, str]] = None,
        regex_match: Optional[CommandRegexMatch] = None,
        wait_consumed: bool = False,
    ) -> None:
        self.command = command
        self.regex_match = regex_match
        self.wait_consumed = wait_consumed
        self.command_system_enabled = True
        self.events: list[str] = []
        self.executed_kwargs: Optional[dict[str, Any]] = None

    def detect_command(self, text: str) -> Optional[tuple[str, str]]:
        del text
        self.events.append("command")
        return self.command

    def is_command_system_enabled(self) -> bool:
        return self.command_system_enabled

    def detect_regex_command(self, text: str, chat_key: str) -> Optional[CommandRegexMatch]:
        del text, chat_key
        self.events.append("regex")
        return self.regex_match

    async def try_handle_wait_input(self, **kwargs: Any) -> bool:
        del kwargs
        self.events.append("wait")
        return self.wait_consumed

    async def execute_command(self, **kwargs: Any) -> None:
        self.events.append("execute")
        self.executed_kwargs = kwargs

    async def get_user_command_permission(
        self,
        platform_user: PlatformUser,
        platform_channel: PlatformChannel,
        platform_message: PlatformMessage,
    ) -> CommandPermission:
        del platform_user, platform_channel, platform_message
        return CommandPermission.USER


def _allow_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(command_manager, "is_command_enabled_for_meta", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        command_manager,
        "get_command_permission",
        lambda command_name, default_permission, chat_key=None: default_permission,
    )


def _context() -> CommandExecutionContext:
    return CommandExecutionContext(
        user_id="user",
        chat_key="fake-channel",
        username="tester",
        adapter_key="fake",
    )


def _platform_context() -> tuple[PlatformChannel, PlatformUser, PlatformMessage]:
    return (
        PlatformChannel(channel_id="channel", channel_name="Channel", channel_type=ChatType.GROUP),
        PlatformUser(platform_name="fake", user_id="user", user_name="Tester"),
        PlatformMessage(message_id="message", sender_id="user", sender_name="Tester", content_text="hello"),
    )


async def _plugin_regex_handler(context: CommandExecutionContext, location: str) -> CommandResponse:
    del context, location
    return CommandResponse(status=CommandResponseStatus.SUCCESS, message="ok")


def test_regex_registry_fullmatches_unicode_and_inline_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_commands(monkeypatch)
    registry = CommandRegistry()
    command = _RegexCommand(
        "weather",
        [r"天气(?P<location>.+)", r"(?i)forecast (?P<location>.+)"],
    )
    registry.register(command)

    chinese_match = registry.match_regex("天气上海", "fake-channel")
    english_match = registry.match_regex("FORECAST Tokyo", "fake-channel")

    assert chinese_match is not None
    assert chinese_match.matched_args == {"location": "上海"}
    assert english_match is not None
    assert english_match.matched_args == {"location": "Tokyo"}
    assert registry.match_regex("请问天气上海怎么样", "fake-channel") is None


@pytest.mark.asyncio
async def test_regex_named_groups_use_existing_type_conversion(monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_commands(monkeypatch)
    registry = CommandRegistry()
    command = _RegexCommand(
        "forecast",
        [r"预报(?P<location>.+?)(?P<days>\d+)天(?:启用(?P<enabled>true|false))?"],
    )
    registry.register(command)
    matched = registry.match_regex("预报上海3天启用true", "fake-channel")
    assert matched is not None

    responses = [
        response
        async for response in registry.execute(
            CommandRequest(
                context=_context(),
                command_name=matched.command_name,
                matched_args=matched.matched_args,
            )
        )
    ]

    assert [response.status for response in responses] == [CommandResponseStatus.SUCCESS]
    assert command.calls == [("上海", 3, True)]


@pytest.mark.asyncio
async def test_regex_optional_group_uses_parameter_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_commands(monkeypatch)
    registry = CommandRegistry()
    command = _RegexCommand(
        "forecast",
        [r"预报(?P<location>.+?)(?:启用(?P<enabled>true|false))?"],
    )
    registry.register(command)
    matched = registry.match_regex("预报上海", "fake-channel")
    assert matched is not None

    responses = [
        response
        async for response in registry.execute(
            CommandRequest(
                context=_context(),
                command_name=matched.command_name,
                matched_args=matched.matched_args,
            )
        )
    ]

    assert [response.status for response in responses] == [CommandResponseStatus.SUCCESS]
    assert command.calls == [("上海", 1, False)]


@pytest.mark.asyncio
async def test_regex_conversion_failure_returns_invalid_args(monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_commands(monkeypatch)
    registry = CommandRegistry()
    command = _RegexCommand("toggle", [r"切换(?P<location>.+?)(?P<enabled>\w+)"])
    registry.register(command)
    matched = registry.match_regex("切换沙盒maybe", "fake-channel")
    assert matched is not None

    responses = [
        response
        async for response in registry.execute(
            CommandRequest(
                context=_context(),
                command_name=matched.command_name,
                matched_args=matched.matched_args,
            )
        )
    ]

    assert [response.status for response in responses] == [CommandResponseStatus.INVALID_ARGS]
    assert command.calls == []


@pytest.mark.asyncio
async def test_regex_command_still_checks_user_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_commands(monkeypatch)
    registry = CommandRegistry()
    command = _RegexCommand(
        "weather",
        [r"天气(?P<location>.+)"],
        permission=CommandPermission.SUPER_USER,
    )
    registry.register(command)
    matched = registry.match_regex("天气上海", "fake-channel")
    assert matched is not None

    responses = [
        response
        async for response in registry.execute(
            CommandRequest(
                context=_context(),
                command_name=matched.command_name,
                matched_args=matched.matched_args,
            )
        )
    ]

    assert [response.status for response in responses] == [CommandResponseStatus.UNAUTHORIZED]
    assert command.calls == []


@pytest.mark.parametrize(
    ("patterns", "error_text"),
    [
        ([r"天气(?P<unknown>.+)"], "未知命名组"),
        ([r"天气.*"], "未提供必填参数"),
        ([r"("], "正则表达式无效"),
    ],
)
def test_regex_registration_validates_patterns(patterns: list[str], error_text: str) -> None:
    registry = CommandRegistry()

    with pytest.raises(ValueError, match=error_text):
        registry.register(_RegexCommand("invalid", patterns))


def test_plugin_regex_is_validated_during_plugin_command_creation() -> None:
    with pytest.raises(ValueError, match="未知命名组"):
        PluginCommand(
            name="weather",
            description="weather",
            regex_patterns=[r"天气(?P<unknown>.+)"],
            execute_func=_plugin_regex_handler,
        )


def test_regex_same_command_uses_first_matching_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_commands(monkeypatch)
    registry = CommandRegistry()
    registry.register(_RegexCommand("weather", [r"(?P<location>上海)", r"(?P<location>.+)"]))

    matched = registry.match_regex("上海", "fake-channel")

    assert matched is not None
    assert matched.pattern == r"(?P<location>上海)"


def test_regex_conflict_does_not_select_a_command(monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_commands(monkeypatch)
    registry = CommandRegistry()
    registry.register(_RegexCommand("first", [r"(?P<location>.+)"]))
    registry.register(_RegexCommand("second", [r"(?P<location>.+)"]))

    assert registry.match_regex("上海", "fake-channel") is None


def test_disabled_regex_command_does_not_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(command_manager, "is_command_enabled_for_meta", lambda *args, **kwargs: False)
    registry = CommandRegistry()
    registry.register(_RegexCommand("weather", [r"天气(?P<location>.+)"]))

    assert registry.match_regex("天气上海", "fake-channel") is None


def test_regex_timeout_is_treated_as_no_match(monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_commands(monkeypatch)
    monkeypatch.setattr(registry_module, "REGEX_MATCH_TIMEOUT_SECONDS", 1e-9)
    registry = CommandRegistry()
    registry.register(_RegexCommand("slow", [r"(?P<location>(a+)+)"]))

    assert registry.match_regex("a" * 5000 + "!", "fake-channel") is None


def test_unregister_plugin_command_removes_regex_index(monkeypatch: pytest.MonkeyPatch) -> None:
    _allow_commands(monkeypatch)
    registry = CommandRegistry()
    registry.register(
        _RegexCommand(
            "weather",
            [r"天气(?P<location>.+)"],
            source="plugin-key",
            namespace="plugin_module",
        )
    )
    assert registry.match_regex("天气上海", "fake-channel") is not None

    registry.unregister_plugin_commands("plugin-key")

    assert registry.match_regex("天气上海", "fake-channel") is None


def test_base_adapter_regex_detection_respects_command_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = SimpleNamespace(
        supports_regex_commands=True,
        config=SimpleNamespace(COMMAND_ENABLED=True),
    )
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        registry_module.command_registry,
        "match_regex",
        lambda text, chat_key: calls.append((text, chat_key)),
    )
    monkeypatch.setattr(config, "COMMAND_ENABLED", False)

    assert BaseAdapter.detect_regex_command(adapter, "天气上海", "fake-channel") is None
    assert calls == []

    monkeypatch.setattr(config, "COMMAND_ENABLED", True)
    adapter.config.COMMAND_ENABLED = False
    assert BaseAdapter.detect_regex_command(adapter, "天气上海", "fake-channel") is None
    assert calls == []


@pytest.mark.asyncio
async def test_command_routing_prefers_explicit_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wait_manager, "has_pending", lambda chat_key, user_id: True)
    adapter = _CollectorAdapter(
        command=("help", ""),
        regex_match=CommandRegexMatch("built_in:weather", {"location": "上海"}, "天气.+"),
        wait_consumed=True,
    )
    channel, user, message = _platform_context()

    consumed = await _try_handle_command(adapter, "fake-channel", channel, user, message, "/help", "/help")

    assert consumed is True
    assert adapter.events == ["command", "execute"]
    assert adapter.executed_kwargs is not None
    assert adapter.executed_kwargs["command_name"] == "help"


@pytest.mark.asyncio
async def test_command_routing_prefers_wait_over_regex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wait_manager, "has_pending", lambda chat_key, user_id: True)
    adapter = _CollectorAdapter(
        regex_match=CommandRegexMatch("built_in:weather", {"location": "上海"}, "天气.+"),
        wait_consumed=True,
    )
    channel, user, message = _platform_context()

    consumed = await _try_handle_command(adapter, "fake-channel", channel, user, message, "天气上海", "天气上海")

    assert consumed is True
    assert adapter.events == ["command", "wait"]


@pytest.mark.asyncio
async def test_disabled_command_system_skips_wait_and_regex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wait_manager, "has_pending", lambda chat_key, user_id: True)
    adapter = _CollectorAdapter(
        regex_match=CommandRegexMatch("built_in:weather", {"location": "上海"}, "天气.+"),
        wait_consumed=True,
    )
    adapter.command_system_enabled = False
    channel, user, message = _platform_context()

    consumed = await _try_handle_command(adapter, "fake-channel", channel, user, message, "天气上海", "天气上海")

    assert consumed is False
    assert adapter.events == ["command"]


@pytest.mark.asyncio
async def test_command_routing_executes_regex_after_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wait_manager, "has_pending", lambda chat_key, user_id: False)
    adapter = _CollectorAdapter(
        regex_match=CommandRegexMatch("built_in:weather", {"location": "上海"}, "天气.+"),
    )
    channel, user, message = _platform_context()

    consumed = await _try_handle_command(adapter, "fake-channel", channel, user, message, "天气上海", " 天气上海 ")

    assert consumed is True
    assert adapter.events == ["command", "regex", "execute"]
    assert adapter.executed_kwargs is not None
    assert adapter.executed_kwargs["command_name"] == "built_in:weather"
    assert adapter.executed_kwargs["matched_args"] == {"location": "上海"}


@pytest.mark.asyncio
async def test_regex_command_input_is_recorded_when_adapter_requires_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wait_manager, "has_pending", lambda chat_key, user_id: False)
    recorded_messages: list[tuple[Any, Any]] = []

    async def record_human_message(message: Any, db_chat_channel: Any) -> None:
        recorded_messages.append((message, db_chat_channel))

    monkeypatch.setattr(collector_module.message_service, "record_human_message", record_human_message)
    adapter = _CollectorAdapter(
        regex_match=CommandRegexMatch("built_in:weather", {"location": "上海"}, "天气.+"),
    )
    adapter.record_command_input = True
    channel, user, message = _platform_context()
    message.content_text = " 天气上海 "
    db_chat_channel = SimpleNamespace(chat_key="fake-channel")

    consumed = await _try_handle_command(
        adapter,
        "fake-channel",
        channel,
        user,
        message,
        "天气上海",
        message.content_text,
        db_chat_channel,
    )

    assert consumed is True
    assert len(recorded_messages) == 1
    assert recorded_messages[0][0].content_text == " 天气上海 "
    assert recorded_messages[0][1] is db_chat_channel


@pytest.mark.asyncio
async def test_command_routing_leaves_unmatched_message_for_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wait_manager, "has_pending", lambda chat_key, user_id: False)
    adapter = _CollectorAdapter()
    channel, user, message = _platform_context()

    consumed = await _try_handle_command(adapter, "fake-channel", channel, user, message, "普通聊天", "普通聊天")

    assert consumed is False
    assert adapter.events == ["command", "regex"]


def test_command_state_response_exposes_regex_patterns() -> None:
    response = CommandStateResponse(
        name="weather",
        namespace="plugin",
        aliases=[],
        regex_patterns=[r"天气(?P<location>.+)"],
        description="weather",
        usage="weather",
        permission="public",
        default_permission="public",
        category="plugin",
        source="plugin",
        source_display_name="Plugin",
        enabled=True,
        has_channel_override=False,
        has_permission_override=False,
    )

    assert response.regex_patterns == [r"天气(?P<location>.+)"]


def test_no_args_regex_command_can_register() -> None:
    registry = CommandRegistry()

    registry.register(_NoArgsRegexCommand("ping", [r"ping"]))
