import asyncio

from nekro_agent.core.config import config
from nekro_agent.services.agent.templates.plugin import PluginPromptRenderUnit, render_plugin_prompt_unit
from nekro_agent.services.config_service import ConfigService
from nekro_agent.services.plugin.call_priority import (
    build_plugin_call_priority_rules,
    get_plugin_call_priority,
    set_plugin_call_priority,
)


def test_get_plugin_call_priority_defaults_to_auto(monkeypatch) -> None:
    monkeypatch.setattr(config, "PLUGIN_CALL_PRIORITIES", {})

    assert get_plugin_call_priority("example") == "auto"


def test_set_plugin_call_priority_persists_override(monkeypatch) -> None:
    saved: list[object] = []
    monkeypatch.setattr(config, "PLUGIN_CALL_PRIORITIES", {})
    monkeypatch.setattr(ConfigService, "save_config", lambda *_args: saved.append(True))

    set_plugin_call_priority("example", "high")

    assert config.PLUGIN_CALL_PRIORITIES == {"example": "high"}
    assert saved == [True]


def test_set_plugin_call_priority_auto_removes_override(monkeypatch) -> None:
    monkeypatch.setattr(config, "PLUGIN_CALL_PRIORITIES", {"example": "low"})
    monkeypatch.setattr(ConfigService, "save_config", lambda *_args: None)

    set_plugin_call_priority("example", "auto")

    assert config.PLUGIN_CALL_PRIORITIES == {}


def test_plugin_prompt_exposes_call_priority() -> None:
    prompt = asyncio.run(
        render_plugin_prompt_unit(
            PluginPromptRenderUnit(
                plugin_name="Example",
                module_name="example",
                state="always_awake",
                call_priority="high",
            ),
        ),
    )

    assert 'call_priority="high"' in prompt


def test_call_priority_rules_define_fallback_and_auto_semantics() -> None:
    rules = build_plugin_call_priority_rules()

    assert "high, then medium, then low" in rules
    assert "try the next applicable lower-priority plugin" in rules
    assert "call_priority=auto" in rules
