from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel

from nekro_agent.core.config import CONFIG_PATH, config
from nekro_agent.models.db_plugin_data import DBPluginData
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.config_service import ConfigService
from nekro_agent.services.plugin.base import NekroPlugin

_STORE_PLUGIN_KEY = "__prompt_activation__"
_STORE_KEY = "module_rounds"
DEFAULT_ACTIVE_ROUNDS = 3
MAX_ACTIVE_ROUNDS = 20
PluginActivationStrategy = Literal["auto", "allow_sleep", "forbid_sleep"]


class PluginActivationState(BaseModel):
    module_rounds: Dict[str, int] = {}


def get_plugin_activation_strategy(module_name: str) -> PluginActivationStrategy:
    strategy = (config.PLUGIN_ACTIVATION_STRATEGIES or {}).get(module_name, "auto")
    if strategy not in {"auto", "allow_sleep", "forbid_sleep"}:
        return "auto"
    return strategy


def set_plugin_activation_strategy(module_name: str, strategy: PluginActivationStrategy) -> None:
    strategies = dict(config.PLUGIN_ACTIVATION_STRATEGIES or {})
    if strategy == "auto":
        strategies.pop(module_name, None)
    else:
        strategies[module_name] = strategy
    config.PLUGIN_ACTIVATION_STRATEGIES = strategies
    ConfigService.save_config(config, CONFIG_PATH)


def plugin_supports_sleep(plugin: NekroPlugin) -> bool:
    return bool(plugin.sleep_brief.strip())


def plugin_strategy_is_protected(plugin: NekroPlugin) -> bool:
    return plugin.allow_sleep is False


def plugin_strategy_can_change(plugin: NekroPlugin) -> bool:
    return not plugin_strategy_is_protected(plugin)


def is_sleep_effective(plugin: NekroPlugin) -> bool:
    if plugin_strategy_is_protected(plugin):
        return False
    strategy = get_plugin_activation_strategy(plugin.module_name)
    if strategy == "forbid_sleep":
        return False
    if strategy == "allow_sleep":
        return plugin_supports_sleep(plugin)
    return plugin.allow_sleep is True


async def get_activation_state(chat_key: str) -> PluginActivationState:
    record = await DBPluginData.filter(
        plugin_key=_STORE_PLUGIN_KEY,
        target_chat_key=chat_key,
        target_user_id="",
        data_key=_STORE_KEY,
    ).first()
    if not record or not record.data_value:
        return PluginActivationState()
    try:
        return PluginActivationState.model_validate_json(record.data_value)
    except Exception:
        return PluginActivationState()


async def save_activation_state(chat_key: str, state: PluginActivationState) -> None:
    value = state.model_dump_json()
    record = await DBPluginData.filter(
        plugin_key=_STORE_PLUGIN_KEY,
        target_chat_key=chat_key,
        target_user_id="",
        data_key=_STORE_KEY,
    ).first()
    if record:
        await DBPluginData.filter(id=record.id).update(data_value=value)
        return
    await DBPluginData.create(
        plugin_key=_STORE_PLUGIN_KEY,
        target_chat_key=chat_key,
        target_user_id="",
        data_key=_STORE_KEY,
        data_value=value,
    )


def normalize_rounds(rounds: int | None) -> int:
    if rounds is None:
        return DEFAULT_ACTIVE_ROUNDS
    return max(1, min(int(rounds), MAX_ACTIVE_ROUNDS))


async def activate_module_for_chat(chat_key: str, module_name: str, rounds: int | None = None) -> int:
    state = await get_activation_state(chat_key)
    final_rounds = normalize_rounds(rounds)
    state.module_rounds[module_name] = final_rounds
    await save_activation_state(chat_key, state)
    return final_rounds


async def extend_module_for_chat(chat_key: str, module_name: str, rounds: int | None = None) -> int:
    state = await get_activation_state(chat_key)
    extra_rounds = normalize_rounds(rounds)
    current = max(0, state.module_rounds.get(module_name, 0))
    state.module_rounds[module_name] = min(current + extra_rounds, MAX_ACTIVE_ROUNDS)
    await save_activation_state(chat_key, state)
    return state.module_rounds[module_name]


def build_plugin_activation_rules() -> str:
    return (
        "Plugin visibility may be scheduled.\n"
        "- Only rely on fully rendered plugin blocks as currently available capabilities.\n"
        "- Sleeping plugin blocks are summaries, not full capability details."
    )


def get_plugin_brief(plugin: NekroPlugin) -> str:
    return plugin.sleep_brief or plugin.description


async def render_plugin_prompt_for_agent(plugin: NekroPlugin, ctx: AgentCtx, rounds_left: int | None = None) -> str:
    from nekro_agent.services.agent.templates.plugin import (
        PluginPromptRenderUnit,
        render_plugin_prompt_unit,
    )

    return await render_plugin_prompt_unit(
        PluginPromptRenderUnit(
            plugin_name=plugin.name,
            module_name=plugin.module_name,
            state="active",
            rounds_left=rounds_left,
            activation_hint=(
                f"Last visible run. Call extend_plugin_activation('{plugin.module_name}') now if you still need it next run."
                if rounds_left == 1
                else ""
            ),
            plugin_injected_prompt=await plugin.render_inject_prompt(ctx),
            plugin_method_prompt=await plugin.render_sandbox_methods_prompt(ctx),
        ),
    )


async def build_prompt_disclosure_view(plugins: List[NekroPlugin], ctx: AgentCtx) -> List[BaseModel]:
    from nekro_agent.services.agent.templates.plugin import PluginPromptRenderUnit

    state = await get_activation_state(ctx.chat_key)
    rounds_snapshot = {module_name: rounds for module_name, rounds in state.module_rounds.items() if rounds > 0}
    consumed = False
    units: List[PluginPromptRenderUnit] = []
    valid_sleepable_modules: set[str] = set()

    for plugin in plugins:
        if len(plugin.support_adapter) != 0 and ctx.adapter_key not in plugin.support_adapter:
            continue

        if is_sleep_effective(plugin):
            valid_sleepable_modules.add(plugin.module_name)

        is_sleeping = is_sleep_effective(plugin) and rounds_snapshot.get(plugin.module_name, 0) <= 0
        if is_sleep_effective(plugin):
            brief = get_plugin_brief(plugin)
            if is_sleeping:
                units.append(
                    PluginPromptRenderUnit(
                        plugin_name=plugin.name,
                        module_name=plugin.module_name,
                        state="sleeping",
                        rounds_left=0,
                        plugin_brief=brief,
                    ),
                )
                continue

            units.append(
                PluginPromptRenderUnit(
                    plugin_name=plugin.name,
                    module_name=plugin.module_name,
                    state="active",
                    rounds_left=rounds_snapshot.get(plugin.module_name, 0),
                    activation_hint=(
                        f"Last visible run. Call extend_plugin_activation('{plugin.module_name}') now if you still need it next run."
                        if rounds_snapshot.get(plugin.module_name, 0) == 1
                        else ""
                    ),
                    plugin_injected_prompt=await plugin.render_inject_prompt(ctx),
                    plugin_method_prompt=await plugin.render_sandbox_methods_prompt(ctx),
                ),
            )
            consumed = True
            continue

        units.append(
            PluginPromptRenderUnit(
                plugin_name=plugin.name,
                module_name=plugin.module_name,
                state="always_awake",
                plugin_injected_prompt=await plugin.render_inject_prompt(ctx),
                plugin_method_prompt=await plugin.render_sandbox_methods_prompt(ctx),
            ),
        )

    cleaned_snapshot = {
        module_name: rounds
        for module_name, rounds in rounds_snapshot.items()
        if module_name in valid_sleepable_modules
    }
    if consumed:
        next_state = PluginActivationState(
            module_rounds={
                module_name: rounds - 1
                for module_name, rounds in cleaned_snapshot.items()
                if rounds - 1 > 0
            },
        )
        await save_activation_state(ctx.chat_key, next_state)
    elif state.module_rounds != cleaned_snapshot:
        await save_activation_state(ctx.chat_key, PluginActivationState(module_rounds=cleaned_snapshot))

    return units
