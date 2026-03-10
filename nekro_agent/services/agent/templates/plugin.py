from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel

from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.plugin.base import NekroPlugin
from nekro_agent.services.plugin.prompt_activation import build_prompt_disclosure_view

from .base import PromptTemplate, env, register_template


@register_template("plugin.j2", "plugin_prompt")
class PluginPrompt(PromptTemplate):
    plugin_name: str
    module_name: str
    state: str
    rounds_left: Optional[int] = None
    activation_hint: str = ""
    plugin_brief: str = ""
    plugin_injected_prompt: str = ""
    plugin_method_prompt: str = ""


class PluginPromptRenderUnit(BaseModel):
    plugin_name: str
    module_name: str
    state: str
    rounds_left: Optional[int] = None
    activation_hint: str = ""
    plugin_brief: str = ""
    plugin_injected_prompt: str = ""
    plugin_method_prompt: str = ""


@dataclass
class RenderedPluginPrompts:
    system_prompt: str
    runtime_prompt: str


async def _render_plugin_prompt(unit: PluginPromptRenderUnit) -> str:
    return PluginPrompt(
        plugin_name=unit.plugin_name,
        module_name=unit.module_name,
        state=unit.state,
        rounds_left=unit.rounds_left,
        activation_hint=unit.activation_hint,
        plugin_brief=unit.plugin_brief,
        plugin_injected_prompt=unit.plugin_injected_prompt,
        plugin_method_prompt=unit.plugin_method_prompt,
    ).render(env)


def _render_plugin_runtime_prompt(units: List[PluginPromptRenderUnit]) -> str:
    sections: List[str] = []
    for unit in units:
        if not unit.plugin_injected_prompt.strip():
            continue
        sections.append(
            "\n".join(
                [
                    f'<plugin_runtime_context name="{unit.plugin_name}" module_name="{unit.module_name}">',
                    unit.plugin_injected_prompt,
                    "</plugin_runtime_context>",
                ],
            ),
        )
    return "\n\n".join(sections)


def _sort_plugin_units_for_cache(units: List[PluginPromptRenderUnit]) -> List[PluginPromptRenderUnit]:
    # Static-only plugin docs first; plugins with runtime injected context later.
    return sorted(
        units,
        key=lambda unit: (
            bool(unit.plugin_injected_prompt.strip()),
            unit.state != "always_awake",
            unit.module_name,
        ),
    )


async def render_plugin_prompt_unit(unit: PluginPromptRenderUnit) -> str:
    return await _render_plugin_prompt(unit)


async def render_plugins_prompt_legacy(plugins: List[NekroPlugin], ctx: AgentCtx) -> RenderedPluginPrompts:
    units: List[PluginPromptRenderUnit] = []
    for plugin in plugins:
        if len(plugin.support_adapter) != 0 and ctx.adapter_key not in plugin.support_adapter:
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
    units = _sort_plugin_units_for_cache(units)
    return RenderedPluginPrompts(
        system_prompt="\n\n".join(
            [
                await _render_plugin_prompt(unit.model_copy(update={"plugin_injected_prompt": ""}))
                for unit in units
            ],
        ),
        runtime_prompt=_render_plugin_runtime_prompt(units),
    )


async def render_plugins_prompt(
    plugins: List[NekroPlugin],
    ctx: AgentCtx,
    activation_enabled: bool = True,
) -> RenderedPluginPrompts:
    if not activation_enabled:
        return await render_plugins_prompt_legacy(plugins, ctx)

    units = await build_prompt_disclosure_view(plugins, ctx)
    units = _sort_plugin_units_for_cache(units)
    return RenderedPluginPrompts(
        system_prompt="\n\n".join(
            [
                await _render_plugin_prompt(unit.model_copy(update={"plugin_injected_prompt": ""}))
                for unit in units
            ],
        ),
        runtime_prompt=_render_plugin_runtime_prompt(units),
    )
