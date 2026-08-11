"""wechat_ilink_multi 实例生命周期相关回归测试。

覆盖两个问题：
1. 实例被软删除后，入站消息仍会触发 Agent；
2. 会话行的"读后写"在并发下会插出多条记录。
"""

import asyncio
from types import SimpleNamespace

import pytest

from nekro_agent.adapters.wechat_ilink_multi import bot_connection as bc_module
from nekro_agent.adapters.wechat_ilink_multi.bot_connection import BotConnection


def _make_connection(monkeypatch, instance_status: str, enabled: bool = True):
    """构造一个只填了 _handle_message 所需字段的 BotConnection。

    直接绕过 __init__：真实构造需要 SDK client 与配置，与本测试关注的分支无关。
    """
    conn = object.__new__(BotConnection)
    conn.adapter = SimpleNamespace(key="wechat_ilink_multi")
    # instance_key 是只读 property，取自 self.instance
    conn.instance = SimpleNamespace(instance_key="wx-01")
    conn._stopped = asyncio.Event()

    stored = SimpleNamespace(status=instance_status, enabled=enabled)

    async def fake_get_instance(adapter_key: str, instance_key: str):
        assert adapter_key == "wechat_ilink_multi"
        assert instance_key == "wx-01"
        return stored

    monkeypatch.setattr(
        bc_module.adapter_instance_service,
        "get_instance",
        fake_get_instance,
    )
    return conn


@pytest.mark.asyncio
async def test_inbound_message_dropped_after_instance_deleted(monkeypatch) -> None:
    """实例已软删除时，入站消息不得再投递给 Agent。"""
    conn = _make_connection(monkeypatch, instance_status="deleted")

    delivered = []
    monkeypatch.setattr(bc_module, "collect_message", lambda **kw: delivered.append(kw))

    assert await conn._instance_still_active() is False
    assert delivered == []
    # 残留连接应被要求退出，避免删除后长轮询空转
    assert conn._stopped.is_set()


@pytest.mark.asyncio
async def test_inbound_message_dropped_when_instance_disabled(monkeypatch) -> None:
    """实例被禁用时同样不应继续接收消息。"""
    conn = _make_connection(monkeypatch, instance_status="online", enabled=False)

    assert await conn._instance_still_active() is False
    assert conn._stopped.is_set()


@pytest.mark.asyncio
async def test_inbound_message_kept_when_instance_active(monkeypatch) -> None:
    """正常在线的实例不受影响，连接也不应被误停。"""
    conn = _make_connection(monkeypatch, instance_status="online")

    assert await conn._instance_still_active() is True
    assert not conn._stopped.is_set()


@pytest.mark.asyncio
async def test_ensure_session_row_tolerates_concurrent_insert(monkeypatch) -> None:
    """并发创建时，落败方应回落为读取既有行，而不是抛错或插出第二条。"""
    from tortoise.exceptions import IntegrityError

    from nekro_agent.services import adapter_instance_service as svc_module

    created = []

    async def fake_exists(**kwargs) -> bool:
        return False

    async def fake_create(**kwargs):
        # 模拟唯一约束在并发下拒绝了本次插入
        created.append(kwargs)
        raise IntegrityError("duplicate key value violates unique constraint")

    monkeypatch.setattr(svc_module.DBAdapterInstanceSession, "exists", fake_exists)
    monkeypatch.setattr(svc_module.DBAdapterInstanceSession, "create", fake_create)

    # 不应把 IntegrityError 抛给调用方：唯一约束已保证最终只有一行
    await svc_module.AdapterInstanceService._ensure_session_row(1)
    assert len(created) == 1
