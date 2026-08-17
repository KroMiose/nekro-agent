"""Webhook 鉴权(fail-closed)与 CORS 来源严格解析测试"""

import pytest

from nekro_agent.core.cors_origins import parse_cors_origins


# ===================== CORS =====================


def test_cors_accepts_valid_origins():
    assert parse_cors_origins("http://127.0.0.1:8021, https://na.example.com") == [
        "http://127.0.0.1:8021",
        "https://na.example.com",
    ]


def test_cors_empty_means_disabled():
    assert parse_cors_origins("") == []
    assert parse_cors_origins(" , ") == []


@pytest.mark.parametrize("bad", ["*", " *, ", "http://a.com,*", "  *  "])
def test_cors_rejects_wildcard(bad: str):
    """通配符任何形式都必须在启动阶段拒绝(CWE-942 反射风险)"""
    with pytest.raises(ValueError, match="通配符"):
        parse_cors_origins(bad)


@pytest.mark.parametrize(
    "bad",
    [
        "ftp://a.com",  # 协议
        "a.com",  # 缺 scheme
        "http://user:pass@a.com",  # 用户信息
        "http://a.com/path",  # 路径
        "http://a.com/?q=1",  # 查询
        "http://a.com#frag",  # 片段
        "http://",  # 缺主机
    ],
)
def test_cors_rejects_malformed_origins(bad: str):
    with pytest.raises(ValueError, match="非法 Origin"):
        parse_cors_origins(bad)


# ===================== Webhook =====================


class _FakeRequest:
    def __init__(self, headers: dict[str, str] | None = None, query: dict[str, str] | None = None):
        self.headers = headers or {}
        self.query_params = query or {}


@pytest.fixture()
def _reset_env(monkeypatch: pytest.MonkeyPatch):
    """OsEnv 为类属性(导入时求值),直接还原属性而非环境变量"""
    from nekro_agent.core.os_env import OsEnv

    monkeypatch.setattr(OsEnv, "WEBHOOK_SECRET_KEY", "")
    monkeypatch.setattr(OsEnv, "ALLOW_UNAUTHENTICATED_WEBHOOKS", False)


def test_webhook_default_is_fail_closed(_reset_env):
    """默认(未配密钥、未开逃生开关)必须拒绝,而不是放行"""
    from nekro_agent.routers.webhook import _verify_webhook_token
    from nekro_agent.schemas.errors import UnauthorizedError

    with pytest.raises(UnauthorizedError):
        _verify_webhook_token(_FakeRequest())


def test_webhook_escape_hatch_opt_in(_reset_env, monkeypatch: pytest.MonkeyPatch):
    from nekro_agent.core.os_env import OsEnv
    from nekro_agent.routers.webhook import _verify_webhook_token

    monkeypatch.setattr(OsEnv, "ALLOW_UNAUTHENTICATED_WEBHOOKS", True)
    _verify_webhook_token(_FakeRequest())  # 显式逃生开关才放行


def test_webhook_requires_matching_header(_reset_env, monkeypatch: pytest.MonkeyPatch):
    from nekro_agent.core.os_env import OsEnv
    from nekro_agent.routers.webhook import _verify_webhook_token
    from nekro_agent.schemas.errors import UnauthorizedError

    monkeypatch.setattr(OsEnv, "WEBHOOK_SECRET_KEY", "s3cret")
    with pytest.raises(UnauthorizedError):
        _verify_webhook_token(_FakeRequest())
    with pytest.raises(UnauthorizedError):
        _verify_webhook_token(_FakeRequest(headers={"X-Webhook-Token": "wrong"}))
    _verify_webhook_token(_FakeRequest(headers={"X-Webhook-Token": "s3cret"}))


def test_webhook_query_param_token_no_longer_accepted(_reset_env, monkeypatch: pytest.MonkeyPatch):
    """查询参数令牌已移除:即使值正确也不得通过"""
    from nekro_agent.core.os_env import OsEnv
    from nekro_agent.routers.webhook import _verify_webhook_token
    from nekro_agent.schemas.errors import UnauthorizedError

    monkeypatch.setattr(OsEnv, "WEBHOOK_SECRET_KEY", "s3cret")
    with pytest.raises(UnauthorizedError):
        _verify_webhook_token(_FakeRequest(query={"webhook_token": "s3cret"}))
