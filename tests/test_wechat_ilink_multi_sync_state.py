"""sync_state_json 字段语义回归测试。

该列是 SyncState 的序列化载体，此前 set_session_state(payload=...) 会把绑定态
（bind_session_id / qr_url）覆盖写入，导致运行阶段 _load_sync_state() 解析失败、
消息监控无法启动。
"""

from types import SimpleNamespace

from nekro_agent.adapters.wechat_ilink_multi.bot_connection import BotConnection
from nekro_agent.adapters.wechat_ilink_multi.schemas import SyncState


def _conn_with_sync_state(raw: str) -> BotConnection:
    """构造仅填充 _load_sync_state 所需字段的 BotConnection。"""
    conn = object.__new__(BotConnection)
    conn.instance = SimpleNamespace(instance_key="wx-01")
    conn.session = SimpleNamespace(sync_state_json=raw)
    return conn


def test_sync_state_rejects_bind_payload_shape() -> None:
    """SyncState 是 extra=forbid：绑定态字段确实会让校验失败（问题前提）。"""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SyncState.model_validate_json(
            '{"bind_session_id": "wechatbot-1", "qr_url": "https://example.com/q/x"}',
        )


def test_load_sync_state_tolerates_polluted_legacy_value() -> None:
    """存量脏数据不得让监控启动失败，应退回空游标继续。"""
    conn = _conn_with_sync_state(
        '{"bind_session_id": "wechatbot-1", "qr_url": "https://example.com/q/x"}',
    )

    state = conn._load_sync_state()

    assert isinstance(state, SyncState)
    assert state.cursor is None
    assert state.sequence is None


def test_load_sync_state_reads_valid_value() -> None:
    """正常的 SyncState 仍按原样解析，不受容错分支影响。"""
    conn = _conn_with_sync_state('{"cursor": "AARzJWAF", "sequence": 7}')

    state = conn._load_sync_state()

    assert state.cursor == "AARzJWAF"
    assert state.sequence == 7


def test_load_sync_state_handles_empty() -> None:
    """空值走快速路径，返回全新的空状态。"""
    assert _conn_with_sync_state("")._load_sync_state().cursor is None


def test_load_sync_state_warning_does_not_echo_raw_value(monkeypatch) -> None:
    """容错日志不得回显原始内容：脏数据里可能是扫码绑定凭据。"""
    from nekro_agent.adapters.wechat_ilink_multi import bot_connection as module

    secret = "https://example.com/q/SECRET-QR-TOKEN"
    records: list[str] = []
    # 整体替换模块级 logger：loguru 的 Logger 用了 __slots__，无法直接改其 warning 属性
    monkeypatch.setattr(module, "logger", SimpleNamespace(warning=lambda msg: records.append(str(msg))))

    conn = _conn_with_sync_state(f'{{"bind_session_id": "wechatbot-1", "qr_url": "{secret}"}}')
    conn._load_sync_state()

    assert records, "解析失败时应留下告警"
    joined = "\n".join(records)
    assert secret not in joined
    assert "SECRET-QR-TOKEN" not in joined
    assert "wechatbot-1" not in joined
    # 但要保留足以定位问题的信息：实例标识与出错字段名
    assert "wx-01" in joined
    assert "qr_url" in joined


def test_set_session_state_no_longer_accepts_payload() -> None:
    """set_session_state 不应再暴露会覆盖 sync_state_json 的 payload 参数。"""
    import inspect

    from nekro_agent.services.adapter_instance_service import AdapterInstanceService

    params = inspect.signature(AdapterInstanceService.set_session_state).parameters
    assert "payload" not in params
