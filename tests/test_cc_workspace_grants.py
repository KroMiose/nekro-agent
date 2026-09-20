import asyncio
import importlib
import sys
from pathlib import Path
from typing import Optional

import pytest

_PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins"
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

cc_plugin = importlib.import_module("builtin.cc_workspace.plugin")
cc_main = importlib.import_module("builtin.cc_workspace.main")


class _FakeWorkspace:
    def __init__(self, status: str = "stopped", last_error: str = "") -> None:
        self.id = 1
        self.name = "cc-ws"
        self.status = status
        self.last_error = last_error
        self.metadata: dict[str, object] = {}


class _FakeCtx:
    def __init__(self, workspace: Optional[_FakeWorkspace]) -> None:
        self.chat_key = "onebot_v11:1"
        self.from_chat_key = "onebot_v11:1"
        self._workspace = workspace

    async def get_bound_workspace(self) -> Optional[_FakeWorkspace]:
        return self._workspace


def _set_grants(monkeypatch: pytest.MonkeyPatch, create: bool, start: bool) -> None:
    monkeypatch.setattr(cc_main.cc_config, "ALLOW_AUTO_CREATE_WORKSPACE", create)
    monkeypatch.setattr(cc_main.cc_config, "ALLOW_AUTO_START_SANDBOX", start)


def _visible_method_names(
    monkeypatch: pytest.MonkeyPatch, create: bool, start: bool, workspace: Optional[_FakeWorkspace]
) -> list[str]:
    _set_grants(monkeypatch, create, start)
    methods = asyncio.run(cc_main._collect_cc_methods(_FakeCtx(workspace)))
    return [str(m.__name__) for m in methods]


# ---------------------------------------------------------------------------
# 配置字段：两轴独立 + 老配置兼容
# ---------------------------------------------------------------------------


def test_start_grant_follows_legacy_create_grant_when_absent() -> None:
    legacy_on = cc_plugin.CCWorkspaceConfig.model_validate({"ALLOW_AUTO_CREATE_WORKSPACE": True})
    legacy_off = cc_plugin.CCWorkspaceConfig.model_validate({"ALLOW_AUTO_CREATE_WORKSPACE": False})
    fresh = cc_plugin.CCWorkspaceConfig.model_validate({})

    assert legacy_on.ALLOW_AUTO_START_SANDBOX is True
    assert legacy_off.ALLOW_AUTO_START_SANDBOX is False
    assert fresh.ALLOW_AUTO_START_SANDBOX is False


def test_start_grant_keeps_explicit_value_independent_of_create_grant() -> None:
    cfg = cc_plugin.CCWorkspaceConfig.model_validate({"ALLOW_AUTO_CREATE_WORKSPACE": False, "ALLOW_AUTO_START_SANDBOX": True})

    assert cfg.ALLOW_AUTO_CREATE_WORKSPACE is False
    assert cfg.ALLOW_AUTO_START_SANDBOX is True


def test_start_grant_is_plain_boolean_for_webui_switch() -> None:
    schema = cc_plugin.CCWorkspaceConfig.model_json_schema()["properties"]["ALLOW_AUTO_START_SANDBOX"]

    assert schema["type"] == "boolean"
    assert "anyOf" not in schema


# ---------------------------------------------------------------------------
# 方法可见性：create 轴只管状态1，start 轴只管状态2
# ---------------------------------------------------------------------------


def test_unbound_channel_exposes_create_only_when_create_granted(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _visible_method_names(monkeypatch, True, False, None) == ["create_and_bind_workspace"]
    assert _visible_method_names(monkeypatch, False, True, None) == []


def test_stopped_workspace_exposes_start_only_when_start_granted(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = _FakeWorkspace(status="stopped")

    assert _visible_method_names(monkeypatch, False, True, workspace) == ["start_cc_sandbox"]
    assert _visible_method_names(monkeypatch, True, False, workspace) == []


def test_active_workspace_hides_create_and_start(monkeypatch: pytest.MonkeyPatch) -> None:
    names = _visible_method_names(monkeypatch, True, True, _FakeWorkspace(status="active"))

    assert "create_and_bind_workspace" not in names
    assert "start_cc_sandbox" not in names
    assert "delegate_to_cc" in names


# ---------------------------------------------------------------------------
# 提示词注入：不得引导 AI 去调用未授权的方法
# ---------------------------------------------------------------------------


def test_unbound_prompt_omits_create_hint_when_create_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_grants(monkeypatch, False, True)

    prompt = asyncio.run(cc_main.cc_workspace_status(_FakeCtx(None)))

    assert "create_and_bind_workspace" not in prompt
    assert "start_cc_sandbox" not in prompt
    assert "workspace management page" in prompt


def test_unbound_prompt_keeps_create_hint_when_create_granted(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_grants(monkeypatch, True, True)

    prompt = asyncio.run(cc_main.cc_workspace_status(_FakeCtx(None)))

    assert "create_and_bind_workspace" in prompt


def test_unbound_prompt_omits_start_hint_when_only_start_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_grants(monkeypatch, True, False)

    prompt = asyncio.run(cc_main.cc_workspace_status(_FakeCtx(None)))

    assert "create_and_bind_workspace" in prompt
    assert "workspace management page" in prompt
    assert "start_cc_sandbox" not in prompt


def test_stopped_prompt_omits_start_hint_when_start_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_grants(monkeypatch, True, False)

    prompt = asyncio.run(cc_main.cc_workspace_status(_FakeCtx(_FakeWorkspace(status="stopped"))))

    assert "start_cc_sandbox" not in prompt
    assert "workspace management page" in prompt


def test_stopped_prompt_keeps_start_hint_when_start_granted(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_grants(monkeypatch, False, True)

    prompt = asyncio.run(cc_main.cc_workspace_status(_FakeCtx(_FakeWorkspace(status="stopped"))))

    assert "start_cc_sandbox" in prompt


# ---------------------------------------------------------------------------
# 运行时复查：可见性门可被 RPC 绕过，函数体须自行拒绝
# ---------------------------------------------------------------------------


def test_create_method_raises_when_create_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_grants(monkeypatch, False, True)

    with pytest.raises(PermissionError, match="工作区管理页面"):
        asyncio.run(cc_main.create_and_bind_workspace(_FakeCtx(None)))


def test_start_method_raises_when_start_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_grants(monkeypatch, True, False)

    with pytest.raises(PermissionError, match="工作区管理页面"):
        asyncio.run(cc_main.start_cc_sandbox(_FakeCtx(None)))
