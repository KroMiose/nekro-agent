from typing import List

from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.plugin.base import NekroPlugin

from .base import PromptTemplate, env, register_template


@register_template("plugin.j2", "plugin_prompt")
class PluginPrompt(PromptTemplate):
    plugin_name: str
    plugin_injected_prompt: str
    plugin_method_prompt: str


async def _render_plugin_prompt(plugin: NekroPlugin, ctx: AgentCtx) -> str:
    return PluginPrompt(
        plugin_name=plugin.name,
        plugin_injected_prompt=await plugin.render_inject_prompt(ctx),
        plugin_method_prompt=await plugin.render_sandbox_methods_prompt(ctx),
    ).render(env)


async def render_plugins_prompt(plugins: List[NekroPlugin], ctx: AgentCtx) -> str:
    return "\n\n".join(
        [
            await _render_plugin_prompt(plugin, ctx)
            for plugin in plugins
            if len(plugin.support_adapter) == 0 or ctx.adapter_key in plugin.support_adapter
        ],
    )
