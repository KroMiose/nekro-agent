import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from tortoise import Tortoise

from nekro_agent.adapters.interface import collector as collector_mod
from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.platform import PlatformChannel, PlatformMessage, PlatformUser
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.schemas.errors import ConflictError
from nekro_agent.schemas.user import UserCreate
from nekro_agent.services.command.base import CommandPermission
from nekro_agent.services.user.util import user_register

_USER_ONLY_APPS = {"models": ["nekro_agent.models.db_user"]}

# 表结构与部署对齐，来源 migrations/models/0_20260209003607_init.py:222-235。
# 迁移链本身是 PostgreSQL 方言（SERIAL/TIMESTAMPTZ/JSONB）跑不到 SQLite 上，而
# .cursor/rules/backend-rules.mdc 明确禁止调用 generate_schemas()，故此处手写等价 DDL。
# 模型加了列而这里漏了，INSERT 会直接报错，不会静默放过。
_USER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS "user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "username" VARCHAR(128) NOT NULL,
    "password" VARCHAR(128) NOT NULL,
    "adapter_key" VARCHAR(64) NOT NULL,
    "platform_userid" VARCHAR(256) NOT NULL,
    "perm_level" INT NOT NULL,
    "login_time" TIMESTAMP NOT NULL,
    "ban_until" TIMESTAMP,
    "prevent_trigger_until" TIMESTAMP,
    "ext_data" JSON NOT NULL,
    "create_time" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture
async def user_db():
    await Tortoise.init(db_url="sqlite://:memory:", modules=_USER_ONLY_APPS)
    await Tortoise.get_connection("default").execute_script(_USER_TABLE_SQL)
    yield DBUser
    await Tortoise.close_connections()


async def _register(platform_userid: str) -> None:
    await user_register(
        UserCreate(username="群友A", password="", adapter_key="onebot_v11", platform_userid=platform_userid)
    )


async def _seed_duplicate_rows(db: Any, platform_userid: str) -> tuple[Any, Any]:
    now = datetime.now(timezone.utc)
    first = await db.create(
        username="第一次建档", password="", adapter_key="onebot_v11", platform_userid=platform_userid, perm_level=0, login_time=now
    )
    second = await db.create(
        username="第二次建档", password="", adapter_key="onebot_v11", platform_userid=platform_userid, perm_level=0, login_time=now
    )
    return first, second


async def test_concurrent_register_creates_single_user(user_db: Any) -> None:
    """同一平台用户的并发建档只允许留下一行，且落败方必须报 ConflictError"""
    results = await asyncio.gather(_register("10001"), _register("10001"), return_exceptions=True)

    rows = await user_db.filter(adapter_key="onebot_v11", platform_userid="10001")

    assert [r.username for r in rows] == ["群友A"], f"重复建档出了 {len(rows)} 行用户"
    # 落败方必须是 ConflictError：collector 只在这种情况下复用已存在的行，
    # 换成别的异常（如包装成 OperationFailedError）那条消息就会被直接丢掉。
    assert sum(result is None for result in results) == 1
    assert sum(isinstance(result, ConflictError) for result in results) == 1


async def test_union_lookup_returns_earliest_row_when_duplicates_exist(user_db: Any) -> None:
    """历史重复行不能让读取路径抛异常，必须确定性地返回最早那行"""
    first, _second = await _seed_duplicate_rows(user_db, "10002")

    user = await DBUser.get_by_union_id(adapter_key="onebot_v11", platform_userid="10002")

    assert user is not None
    assert user.id == first.id


async def test_register_reports_conflict_when_duplicates_exist(user_db: Any) -> None:
    """重复行存在时再次建档应当报“已存在”，而不是把 DB 异常抛给调用方"""
    await _seed_duplicate_rows(user_db, "10003")

    with pytest.raises(ConflictError):
        await _register("10003")


class _FakeAdapter:
    key = "onebot_v11"
    record_command_input = False

    def build_chat_key(self, channel_id: str) -> str:
        return f"onebot_v11:group:{channel_id}"

    def detect_command(self, content_text: str) -> Optional[tuple[str, str]]:
        del content_text
        return None

    async def get_user_command_permission(self, *args: Any) -> CommandPermission:
        return CommandPermission.USER

    async def set_user_command_permission(self, *args: Any, **kwargs: Any) -> None:
        return None


class _FakeChannel:
    chat_key = "onebot_v11:group:1"
    is_active = True
    channel_name = "G"
    workspace_id: Optional[int] = None


async def _push_collector_messages(user_db: Any, monkeypatch: pytest.MonkeyPatch, platform_userid: str, count: int) -> list[Any]:
    pushed: list[Any] = []

    async def fake_get_or_create(**kwargs: Any) -> _FakeChannel:
        del kwargs
        return _FakeChannel()

    async def fake_push_human_message(**kwargs: Any) -> None:
        pushed.append(kwargs["user"])

    monkeypatch.setattr(collector_mod.DBChatChannel, "get_or_create", fake_get_or_create)
    monkeypatch.setattr(collector_mod.message_service, "push_human_message", fake_push_human_message)

    async def one(index: int) -> None:
        await collect_message(
            _FakeAdapter(),
            PlatformChannel(channel_id="1", channel_name="G", channel_type=ChatType.GROUP),
            PlatformUser(platform_name="qq", user_id=platform_userid, user_name="群友A"),
            PlatformMessage(message_id=f"m{index}", sender_id=platform_userid, sender_name="群友A", content_text="你好"),
        )

    await asyncio.gather(*(one(i) for i in range(count)))
    return pushed


async def test_concurrent_messages_from_new_user_register_once(
    user_db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """新用户连发两条消息并发进管线：只建一行，且两条消息都不能被丢掉"""
    pushed = await _push_collector_messages(user_db, monkeypatch, "10005", 2)

    rows = await user_db.filter(adapter_key="onebot_v11", platform_userid="10005")
    user_ids = await user_db.all().values_list("id", flat=True)

    assert len(rows) == 1, f"并发建档留下 {len(rows)} 行（全表 {len(user_ids)} 行）"
    assert len(pushed) == 2
    assert {u.id for u in pushed} == {rows[0].id}



async def test_collect_message_survives_duplicate_user_rows(user_db: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """issue #312 的实际症状：存在重复行的用户一发言，整条消息处理链就抛错"""
    pushed: list[Any] = []

    async def fake_get_or_create(**kwargs: Any) -> _FakeChannel:
        del kwargs
        return _FakeChannel()

    async def fake_push_human_message(**kwargs: Any) -> None:
        pushed.append(kwargs["user"])

    monkeypatch.setattr(collector_mod.DBChatChannel, "get_or_create", fake_get_or_create)
    monkeypatch.setattr(collector_mod.message_service, "push_human_message", fake_push_human_message)

    first, _second = await _seed_duplicate_rows(user_db, "10004")

    await collect_message(
        _FakeAdapter(),
        PlatformChannel(channel_id="1", channel_name="G", channel_type=ChatType.GROUP),
        PlatformUser(platform_name="qq", user_id="10004", user_name="群友A"),
        PlatformMessage(message_id="m1", sender_id="10004", sender_name="群友A", content_text="你好"),
    )

    assert [u.id for u in pushed] == [first.id]


async def test_rejected_registration_keeps_a_log_line(user_db: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """昵称撞上保留名 admin 时建不了档，这条消息被丢弃必须留下日志，不能静默吞掉"""
    logs: list[str] = []

    def _record(msg: Any) -> None:
        logs.append(str(msg))

    monkeypatch.setattr(
        collector_mod,
        "logger",
        SimpleNamespace(info=_record, warning=_record, error=_record, exception=_record, debug=_record),
    )

    async def fake_get_or_create(**kwargs: Any) -> _FakeChannel:
        del kwargs
        return _FakeChannel()

    async def fake_push_human_message(**kwargs: Any) -> None:
        raise AssertionError("建档失败的用户不应进入人工消息管线")

    monkeypatch.setattr(collector_mod.DBChatChannel, "get_or_create", fake_get_or_create)
    monkeypatch.setattr(collector_mod.message_service, "push_human_message", fake_push_human_message)

    await collect_message(
        _FakeAdapter(),
        PlatformChannel(channel_id="1", channel_name="G", channel_type=ChatType.GROUP),
        PlatformUser(platform_name="qq", user_id="10006", user_name="admin"),
        PlatformMessage(message_id="m1", sender_id="10006", sender_name="admin", content_text="你好"),
    )

    assert await user_db.filter(adapter_key="onebot_v11", platform_userid="10006").count() == 0
    assert any("10006" in line for line in logs), f"消息被丢弃但没有任何日志: {logs}"
