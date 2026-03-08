"""插件激活调度器

用于控制允许休眠的插件在当前会话中的提示词展开状态，降低长工具清单造成的上下文膨胀。
"""

from nekro_agent.api import i18n
from nekro_agent.api.plugin import NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.plugin.prompt_activation import (
    activate_module_for_chat,
    extend_module_for_chat,
    is_sleep_effective,
    render_plugin_prompt_for_agent,
)

plugin = NekroPlugin(
    name="插件激活调度器",
    module_name="plugin_activation",
    description="控制允许休眠的插件在当前会话中的完整提示词披露状态",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="插件激活调度器",
        en_US="Plugin Activation Scheduler",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="控制允许休眠的插件在当前会话中的完整提示词披露状态",
        en_US="Controls full prompt disclosure of sleepable plugins in the current session",
    ),
    allow_sleep=False,
    sleep_brief="用于管理其他插件的提示词激活状态，通常保持常驻，不建议休眠。",
)


@plugin.mount_prompt_inject_method("plugin_activation_prompt")
async def plugin_activation_prompt(_ctx: AgentCtx) -> str:
    return (
        "Plugin visibility is dynamically scheduled to reduce prompt size.\n"
        "- If a plugin block is fully visible, treat it as available now.\n"
        "- If a plugin block is sleeping, you only know its brief summary.\n"
        "- When a sleeping plugin is clearly needed, call `activate_plugin(module_name)`.\n"
        "- `activate_plugin` is an AGENT method and immediately returns the full plugin block.\n"
        "- If you will keep using that plugin across future runs, call `extend_plugin_activation(module_name, rounds)`."
    )


def _get_sleepable_plugin(module_name: str) -> NekroPlugin | None:
    target = plugin_collector.get_plugin_by_module_name(module_name)
    if not target or not target.is_enabled or not is_sleep_effective(target):
        return None
    return target


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    name="激活插件提示词",
    description="按 module_name 激活一个允许休眠的插件，并立即返回其完整提示词块",
)
async def activate_plugin(_ctx: AgentCtx, module_name: str, rounds: int = 3) -> str:
    """Activate a sleeping plugin and return its full prompt block immediately.

    Args:
        module_name (str): Target plugin module_name.
        rounds (int): Visible runs to keep after activation.
    """
    target = _get_sleepable_plugin(module_name)
    if not target:
        return f"Plugin `{module_name}` is missing, disabled, or not managed by activation scheduling."

    final_rounds = await activate_module_for_chat(_ctx.chat_key, module_name, rounds)
    plugin_block = await render_plugin_prompt_for_agent(target, _ctx, rounds_left=final_rounds)
    return (
        f"Plugin `{module_name}` is now activated for the next {final_rounds} runs. "
        "The full plugin block is returned below and is now the source of truth for this capability. "
        "Stop here and continue in the next agent step.\n\n"
        f"{plugin_block}"
    )


@plugin.mount_sandbox_method(
    SandboxMethodType.BEHAVIOR,
    name="续期插件提示词激活",
    description="按 module_name 延长一个已接管插件的完整可见轮数",
)
async def extend_plugin_activation(_ctx: AgentCtx, module_name: str, rounds: int = 2) -> str:
    """Extend the visible lifetime of an already managed plugin.

    Args:
        module_name (str): Target plugin module_name.
        rounds (int): Additional visible runs to append.
    """
    target = _get_sleepable_plugin(module_name)
    if not target:
        return f"Plugin `{module_name}` is missing, disabled, or not managed by activation scheduling."

    final_rounds = await extend_module_for_chat(_ctx.chat_key, module_name, rounds)
    return f"Plugin `{module_name}` visibility extended. {final_rounds} runs remain."


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
