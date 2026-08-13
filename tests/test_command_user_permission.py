from typing import Any

import pytest

from nekro_agent.adapters.interface.collector import (
    _persist_registered_user_command_permission,
    _try_handle_command,
    collect_message,
)
from nekro_agent.adapters.interface.schemas.platform import PlatformChannel, PlatformMessage, PlatformUser
from nekro_agent.adapters.onebot_v11.adapter import OnebotV11Adapter
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.schemas.i18n import i18n_text
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.built_in.user import GrantAdvancedCommand, RevokeAdvancedCommand
from nekro_agent.services.command.schemas import CommandExecutionContext, CommandResponse


class _PermissionCommand(BaseCommand):
    def __init__(self, permission: CommandPermission):
        self._permission = permission

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name=f"test_permission_{self._permission.value}",
            description="test permission",
            i18n_description=i18n_text(zh_CN="测试权限", en_US="Test permission"),
            permission=self._permission,
        )

    async def execute(self, context: CommandExecutionContext, **kwargs: Any) -> CommandResponse:
        del context, kwargs
        raise NotImplementedError


class _FakeAdapter:
    key = "fake"

    def __init__(
        self,
        permission: CommandPermission,
        *,
        command_detected: bool = True,
        wait_consumed: bool = True,
    ):
        self.permission = permission
        self.command_detected = command_detected
        self.wait_consumed = wait_consumed
        self.executed_kwargs: dict[str, Any] | None = None
        self.wait_kwargs: dict[str, Any] | None = None
        self.granted: tuple[str, CommandPermission | str, str, str | None] | None = None
        self.permission_lookup_count = 0

    async def get_user_command_permission(
        self,
        platform_user: PlatformUser,
        platform_channel: PlatformChannel,
        platform_message: PlatformMessage,
    ) -> CommandPermission:
        del platform_user, platform_channel, platform_message
        self.permission_lookup_count += 1
        return self.permission

    def detect_command(self, content_text: str) -> tuple[str, str] | None:
        del content_text
        if not self.command_detected:
            return None
        return "test", "raw"

    async def execute_command(self, **kwargs: Any) -> None:
        self.executed_kwargs = kwargs

    async def try_handle_wait_input(self, **kwargs: Any) -> bool:
        self.wait_kwargs = kwargs
        return self.wait_consumed

    async def set_user_command_permission(
        self,
        platform_userid: str,
        permission: CommandPermission | str,
        *,
        source: str = "manual",
        channel_id: str | None = None,
    ) -> CommandPermission:
        self.granted = (platform_userid, permission, source, channel_id)
        return permission if isinstance(permission, CommandPermission) else CommandPermission(permission)


class _PermissionGrantAdapter:
    def __init__(self):
        self.granted: tuple[str, CommandPermission | str] | None = None
        self.reset_userid: str | None = None

    async def set_user_command_permission(
        self,
        platform_userid: str,
        permission: CommandPermission | str,
    ) -> CommandPermission:
        self.granted = (platform_userid, permission)
        return permission if isinstance(permission, CommandPermission) else CommandPermission(permission)

    async def reset_user_command_permission(self, platform_userid: str) -> None:
        self.reset_userid = platform_userid


class _OneBotRoleBot:
    def __init__(self, role: str):
        self.role = role
        self.calls: list[dict[str, Any]] = []

    async def get_group_member_info(self, **kwargs: Any) -> dict[str, str]:
        self.calls.append(kwargs)
        return {"role": self.role}


def _context(*, is_super_user: bool, is_advanced_user: bool) -> CommandExecutionContext:
    return CommandExecutionContext(
        user_id="platform-user",
        chat_key="fake-channel",
        username="tester",
        adapter_key="fake",
        is_super_user=is_super_user,
        is_advanced_user=is_advanced_user,
    )


@pytest.mark.asyncio
async def test_super_user_can_execute_advanced_permission() -> None:
    command = _PermissionCommand(CommandPermission.ADVANCED)

    ok, err = await command.check_permission(_context(is_super_user=True, is_advanced_user=False))

    assert ok is True
    assert err is None


@pytest.mark.asyncio
async def test_advanced_user_cannot_execute_super_user_permission() -> None:
    command = _PermissionCommand(CommandPermission.SUPER_USER)

    ok, err = await command.check_permission(_context(is_super_user=False, is_advanced_user=True))

    assert ok is False
    assert err is not None


@pytest.mark.asyncio
async def test_command_manager_persists_user_permission(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.services.command import manager as manager_mod

    monkeypatch.setattr(manager_mod, "COMMAND_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(manager_mod, "COMMAND_CHANNEL_STATE_DIR", str(tmp_path / "channels"))
    monkeypatch.setattr(manager_mod, "COMMAND_CHANNEL_PERMISSION_DIR", str(tmp_path / "channel_permissions"))
    monkeypatch.setattr(manager_mod, "COMMAND_SYSTEM_STATE_FILE", str(tmp_path / "system.json"))
    monkeypatch.setattr(manager_mod, "COMMAND_SYSTEM_PERMISSION_FILE", str(tmp_path / "system_permissions.json"))
    monkeypatch.setattr(manager_mod, "COMMAND_USER_PERMISSION_FILE", str(tmp_path / "user_permissions.json"))

    manager = manager_mod.CommandManager()

    assert manager.get_user_permission("fake", "u1") == CommandPermission.USER

    await manager.set_user_permission("fake", "u1", CommandPermission.ADVANCED)
    assert manager.get_user_permission("fake", "u1") == CommandPermission.ADVANCED

    await manager.set_user_permission(
        "fake",
        "u1",
        CommandPermission.ADVANCED,
        source="platform",
        channel_id="group_1",
    )
    record = manager.get_user_permission_record("fake", "u1")
    assert record.permission == CommandPermission.ADVANCED
    assert record.source == "platform"
    assert record.channel_id == "group_1"

    await manager.reset_user_permission("fake", "u1")
    assert manager.get_user_permission("fake", "u1") == CommandPermission.USER


@pytest.mark.asyncio
async def test_grant_advanced_command_uses_adapter_permission_interface(monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.adapters.utils import adapter_utils

    adapter = _PermissionGrantAdapter()
    monkeypatch.setattr(adapter_utils, "get_adapter", lambda adapter_key: adapter)
    command = GrantAdvancedCommand()

    response = await command.execute(_context(is_super_user=True, is_advanced_user=True), "u1", "fake")

    assert response.data == {
        "adapter_key": "fake",
        "platform_userid": "u1",
        "permission": CommandPermission.ADVANCED.value,
    }
    assert adapter.granted == ("u1", CommandPermission.ADVANCED)


@pytest.mark.asyncio
async def test_revoke_advanced_command_uses_adapter_permission_interface(monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.adapters.utils import adapter_utils

    adapter = _PermissionGrantAdapter()
    monkeypatch.setattr(adapter_utils, "get_adapter", lambda adapter_key: adapter)
    command = RevokeAdvancedCommand()

    response = await command.execute(_context(is_super_user=True, is_advanced_user=True), "u1", "fake")

    assert response.data == {
        "adapter_key": "fake",
        "platform_userid": "u1",
        "permission": CommandPermission.USER.value,
    }
    assert adapter.reset_userid == "u1"


@pytest.mark.asyncio
async def test_collector_maps_adapter_advanced_permission_to_command_context() -> None:
    adapter = _FakeAdapter(CommandPermission.ADVANCED)
    channel = PlatformChannel(channel_id="channel", channel_name="Channel", channel_type=ChatType.GROUP)
    user = PlatformUser(platform_name="fake", user_id="advanced-user", user_name="Advanced User")
    message = PlatformMessage(
        message_id="msg",
        sender_id="advanced-user",
        sender_name="Advanced User",
        content_text="/test raw",
    )

    consumed = await _try_handle_command(adapter, "fake-channel", channel, user, message, message.content_text)

    assert consumed is True
    assert adapter.executed_kwargs is not None
    assert adapter.executed_kwargs["is_super_user"] is False
    assert adapter.executed_kwargs["is_advanced_user"] is True


@pytest.mark.asyncio
async def test_collector_reuses_adapter_permission_for_wait_input() -> None:
    from nekro_agent.services.command.wait_manager import wait_manager

    adapter = _FakeAdapter(CommandPermission.ADVANCED, command_detected=False)
    channel = PlatformChannel(channel_id="channel", channel_name="Channel", channel_type=ChatType.GROUP)
    user = PlatformUser(platform_name="fake", user_id="advanced-user", user_name="Advanced User")
    message = PlatformMessage(
        message_id="msg",
        sender_id="advanced-user",
        sender_name="Advanced User",
        content_text="confirm",
    )

    await wait_manager.create_session("fake-channel", "advanced-user", "callback")
    try:
        consumed = await _try_handle_command(adapter, "fake-channel", channel, user, message, message.content_text)
    finally:
        wait_manager.cancel("fake-channel", "advanced-user")

    assert consumed is True
    assert adapter.wait_kwargs is not None
    assert adapter.wait_kwargs["is_super_user"] is False
    assert adapter.wait_kwargs["is_advanced_user"] is True


@pytest.mark.asyncio
async def test_collector_skips_permission_lookup_for_plain_message_without_wait() -> None:
    adapter = _FakeAdapter(CommandPermission.ADVANCED, command_detected=False, wait_consumed=False)
    channel = PlatformChannel(channel_id="channel", channel_name="Channel", channel_type=ChatType.GROUP)
    user = PlatformUser(platform_name="fake", user_id="advanced-user", user_name="Advanced User")
    message = PlatformMessage(
        message_id="msg",
        sender_id="advanced-user",
        sender_name="Advanced User",
        content_text="plain message",
    )

    consumed = await _try_handle_command(adapter, "fake-channel", channel, user, message, message.content_text)

    assert consumed is False
    assert adapter.permission_lookup_count == 0
    assert adapter.wait_kwargs is None


@pytest.mark.asyncio
async def test_registered_user_adapter_permission_is_persisted_as_platform_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nekro_agent.adapters.interface import collector as collector_mod
    from nekro_agent.services.command.manager import USER_PERMISSION_SOURCE_PLATFORM

    class _FakeDbChatChannel:
        chat_key = "fake-channel"
        is_active = True
        channel_name = "Channel"
        channel_status = "active"
        workspace_id = "workspace"

    class _FakeDbUser:
        is_active = True
        is_prevent_trigger = False
        ban_until = None

    async def fake_get_or_create(**kwargs: Any) -> _FakeDbChatChannel:
        del kwargs
        return _FakeDbChatChannel()

    user_lookup_count = 0

    async def fake_get_by_union_id(**kwargs: Any) -> _FakeDbUser | None:
        nonlocal user_lookup_count
        del kwargs
        user_lookup_count += 1
        return None if user_lookup_count == 1 else _FakeDbUser()

    async def fake_user_register(*args: Any, **kwargs: Any) -> None:
        del args, kwargs

    pushed_messages: list[Any] = []

    async def fake_push_human_message(**kwargs: Any) -> None:
        pushed_messages.append(kwargs)

    monkeypatch.setattr(collector_mod.DBChatChannel, "get_or_create", fake_get_or_create)
    monkeypatch.setattr(collector_mod.DBUser, "get_by_union_id", fake_get_by_union_id)
    monkeypatch.setattr(collector_mod, "user_register", fake_user_register)
    monkeypatch.setattr(collector_mod.message_service, "push_human_message", fake_push_human_message)

    adapter = _FakeAdapter(CommandPermission.ADVANCED, command_detected=False, wait_consumed=False)
    channel = PlatformChannel(channel_id="channel", channel_name="Channel", channel_type=ChatType.GROUP)
    user = PlatformUser(platform_name="fake", user_id="advanced-user", user_name="Advanced User")
    message = PlatformMessage(
        message_id="msg",
        sender_id="advanced-user",
        sender_name="Advanced User",
        content_text="hello",
    )

    await collect_message(adapter, channel, user, message)

    assert adapter.granted == ("advanced-user", CommandPermission.ADVANCED, USER_PERMISSION_SOURCE_PLATFORM, "channel")
    assert pushed_messages


@pytest.mark.asyncio
async def test_platform_permission_registration_clamps_super_user_to_advanced(monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.core.config import config
    from nekro_agent.services.command.manager import USER_PERMISSION_SOURCE_PLATFORM

    monkeypatch.setattr(config, "SUPER_USERS", [])

    adapter = _FakeAdapter(CommandPermission.SUPER_USER, command_detected=False)
    channel = PlatformChannel(channel_id="channel", channel_name="Channel", channel_type=ChatType.GROUP)
    user = PlatformUser(platform_name="fake", user_id="platform-owner", user_name="Platform Owner")
    message = PlatformMessage(
        message_id="msg",
        sender_id="platform-owner",
        sender_name="Platform Owner",
        content_text="hello",
    )

    await _persist_registered_user_command_permission(adapter, channel, user, message)

    assert adapter.granted == ("platform-owner", CommandPermission.ADVANCED, USER_PERMISSION_SOURCE_PLATFORM, "channel")


def test_user_manager_super_users_override_persisted_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.core.config import config
    from nekro_agent.routers import user_manager

    monkeypatch.setattr(config, "SUPER_USERS", ["3305587173"])
    monkeypatch.setattr(
        user_manager.command_manager,
        "get_user_permission",
        lambda adapter_key, platform_userid: CommandPermission.ADVANCED,
    )

    permission = user_manager._resolve_effective_command_permission("onebot_v11", "3305587173")

    assert permission == CommandPermission.SUPER_USER


@pytest.mark.asyncio
async def test_onebot_group_admin_gets_advanced_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.adapters.onebot_v11 import adapter as onebot_adapter_mod
    from nekro_agent.services.command import manager as manager_mod
    from nekro_agent.services.command.manager import UserPermissionRecord

    bot = _OneBotRoleBot("admin")
    monkeypatch.setattr(onebot_adapter_mod, "get_bot", lambda: bot)
    monkeypatch.setattr(
        manager_mod.command_manager,
        "get_user_permission_record",
        lambda adapter_key, platform_userid: UserPermissionRecord(CommandPermission.USER),
    )
    adapter = OnebotV11Adapter.__new__(OnebotV11Adapter)

    permission = await adapter.get_user_command_permission(
        PlatformUser(platform_name="qq", user_id="10001", user_name="Admin"),
        PlatformChannel(channel_id="group_20002", channel_name="Group", channel_type=ChatType.GROUP),
        PlatformMessage(message_id="msg", sender_id="10001", sender_name="Admin"),
    )

    assert permission == CommandPermission.ADVANCED
    assert bot.calls == [{"group_id": 20002, "user_id": 10001, "no_cache": False}]


@pytest.mark.asyncio
async def test_onebot_group_owner_gets_advanced_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.adapters.onebot_v11 import adapter as onebot_adapter_mod
    from nekro_agent.services.command import manager as manager_mod
    from nekro_agent.services.command.manager import UserPermissionRecord

    monkeypatch.setattr(onebot_adapter_mod, "get_bot", lambda: _OneBotRoleBot("owner"))
    monkeypatch.setattr(
        manager_mod.command_manager,
        "get_user_permission_record",
        lambda adapter_key, platform_userid: UserPermissionRecord(CommandPermission.USER),
    )
    adapter = OnebotV11Adapter.__new__(OnebotV11Adapter)

    permission = await adapter.get_user_command_permission(
        PlatformUser(platform_name="qq", user_id="10001", user_name="Owner"),
        PlatformChannel(channel_id="group_20002", channel_name="Group", channel_type=ChatType.GROUP),
        PlatformMessage(message_id="msg", sender_id="10001", sender_name="Owner"),
    )

    assert permission == CommandPermission.ADVANCED


@pytest.mark.asyncio
async def test_onebot_group_member_keeps_user_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.adapters.onebot_v11 import adapter as onebot_adapter_mod
    from nekro_agent.services.command import manager as manager_mod
    from nekro_agent.services.command.manager import UserPermissionRecord

    monkeypatch.setattr(onebot_adapter_mod, "get_bot", lambda: _OneBotRoleBot("member"))
    monkeypatch.setattr(
        manager_mod.command_manager,
        "get_user_permission_record",
        lambda adapter_key, platform_userid: UserPermissionRecord(CommandPermission.USER),
    )
    adapter = OnebotV11Adapter.__new__(OnebotV11Adapter)

    permission = await adapter.get_user_command_permission(
        PlatformUser(platform_name="qq", user_id="10001", user_name="Member"),
        PlatformChannel(channel_id="group_20002", channel_name="Group", channel_type=ChatType.GROUP),
        PlatformMessage(message_id="msg", sender_id="10001", sender_name="Member"),
    )

    assert permission == CommandPermission.USER


@pytest.mark.asyncio
async def test_onebot_private_chat_does_not_query_group_role(monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.adapters.onebot_v11 import adapter as onebot_adapter_mod
    from nekro_agent.services.command import manager as manager_mod
    from nekro_agent.services.command.manager import UserPermissionRecord

    bot = _OneBotRoleBot("owner")
    monkeypatch.setattr(onebot_adapter_mod, "get_bot", lambda: bot)
    monkeypatch.setattr(
        manager_mod.command_manager,
        "get_user_permission_record",
        lambda adapter_key, platform_userid: UserPermissionRecord(CommandPermission.USER),
    )
    adapter = OnebotV11Adapter.__new__(OnebotV11Adapter)

    permission = await adapter.get_user_command_permission(
        PlatformUser(platform_name="qq", user_id="10001", user_name="Private User"),
        PlatformChannel(channel_id="private_10001", channel_name="Private", channel_type=ChatType.PRIVATE),
        PlatformMessage(message_id="msg", sender_id="10001", sender_name="Private User"),
    )

    assert permission == CommandPermission.USER
    assert bot.calls == []


@pytest.mark.asyncio
async def test_onebot_manual_advanced_permission_works_in_private_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.adapters.onebot_v11 import adapter as onebot_adapter_mod
    from nekro_agent.services.command import manager as manager_mod
    from nekro_agent.services.command.manager import UserPermissionRecord

    bot = _OneBotRoleBot("member")
    monkeypatch.setattr(onebot_adapter_mod, "get_bot", lambda: bot)
    monkeypatch.setattr(
        manager_mod.command_manager,
        "get_user_permission_record",
        lambda adapter_key, platform_userid: UserPermissionRecord(CommandPermission.ADVANCED, source="manual"),
    )
    adapter = OnebotV11Adapter.__new__(OnebotV11Adapter)

    permission = await adapter.get_user_command_permission(
        PlatformUser(platform_name="qq", user_id="10001", user_name="Private User"),
        PlatformChannel(channel_id="private_10001", channel_name="Private", channel_type=ChatType.PRIVATE),
        PlatformMessage(message_id="msg", sender_id="10001", sender_name="Private User"),
    )

    assert permission == CommandPermission.ADVANCED
    assert bot.calls == []


@pytest.mark.asyncio
async def test_onebot_platform_permission_is_cleared_when_group_role_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nekro_agent.adapters.onebot_v11 import adapter as onebot_adapter_mod
    from nekro_agent.services.command import manager as manager_mod
    from nekro_agent.services.command.manager import UserPermissionRecord

    reset_calls: list[dict[str, Any]] = []

    async def fake_reset_user_permission(*args: Any, **kwargs: Any) -> None:
        reset_calls.append({"args": args, "kwargs": kwargs})

    bot = _OneBotRoleBot("member")
    monkeypatch.setattr(onebot_adapter_mod, "get_bot", lambda: bot)
    monkeypatch.setattr(
        manager_mod.command_manager,
        "get_user_permission_record",
        lambda adapter_key, platform_userid: UserPermissionRecord(
            CommandPermission.ADVANCED,
            source="platform",
            channel_id="group_20002",
        ),
    )
    monkeypatch.setattr(manager_mod.command_manager, "reset_user_permission", fake_reset_user_permission)
    adapter = OnebotV11Adapter.__new__(OnebotV11Adapter)

    permission = await adapter.get_user_command_permission(
        PlatformUser(platform_name="qq", user_id="10001", user_name="Member"),
        PlatformChannel(channel_id="group_20002", channel_name="Group", channel_type=ChatType.GROUP),
        PlatformMessage(message_id="msg", sender_id="10001", sender_name="Member"),
    )

    assert permission == CommandPermission.USER
    assert reset_calls == [{
        "args": ("onebot_v11", "10001"),
        "kwargs": {"source": "platform", "channel_id": "group_20002"},
    }]


@pytest.mark.asyncio
async def test_onebot_platform_permission_does_not_cross_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    from nekro_agent.adapters.onebot_v11 import adapter as onebot_adapter_mod
    from nekro_agent.services.command import manager as manager_mod
    from nekro_agent.services.command.manager import UserPermissionRecord

    bot = _OneBotRoleBot("member")
    monkeypatch.setattr(onebot_adapter_mod, "get_bot", lambda: bot)
    monkeypatch.setattr(
        manager_mod.command_manager,
        "get_user_permission_record",
        lambda adapter_key, platform_userid: UserPermissionRecord(
            CommandPermission.ADVANCED,
            source="platform",
            channel_id="group_20003",
        ),
    )
    adapter = OnebotV11Adapter.__new__(OnebotV11Adapter)

    permission = await adapter.get_user_command_permission(
        PlatformUser(platform_name="qq", user_id="10001", user_name="Owner"),
        PlatformChannel(channel_id="group_20002", channel_name="Group", channel_type=ChatType.GROUP),
        PlatformMessage(message_id="msg", sender_id="10001", sender_name="Owner"),
    )

    assert permission == CommandPermission.USER
    assert bot.calls == [{"group_id": 20002, "user_id": 10001, "no_cache": False}]
