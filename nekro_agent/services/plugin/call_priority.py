from typing import Literal

from nekro_agent.core.config import CONFIG_PATH, config
from nekro_agent.services.config_service import ConfigService

PluginCallPriority = Literal["auto", "high", "medium", "low"]


def get_plugin_call_priority(module_name: str) -> PluginCallPriority:
    """获取插件调用优先级，未配置或配置异常时回退为自动。"""
    priority = (config.PLUGIN_CALL_PRIORITIES or {}).get(module_name, "auto")
    if priority not in {"auto", "high", "medium", "low"}:
        return "auto"
    return priority


def set_plugin_call_priority(module_name: str, priority: PluginCallPriority) -> tuple[bool, str | None]:
    """设置并持久化插件调用优先级；自动策略不保存覆盖项。"""
    previous_priorities = config.PLUGIN_CALL_PRIORITIES
    priorities = dict(previous_priorities or {})
    if priority == "auto":
        priorities.pop(module_name, None)
    else:
        priorities[module_name] = priority

    config.PLUGIN_CALL_PRIORITIES = priorities
    success, error = ConfigService.save_config(config, CONFIG_PATH)
    if not success:
        config.PLUGIN_CALL_PRIORITIES = previous_priorities
    return success, error


def build_plugin_call_priority_rules() -> str:
    """构建供大模型执行的插件调用优先级规则。"""
    return (
        "Plugin call priority is a preference only when multiple enabled plugins "
        "provide equivalent capabilities.\n"
        "- Explicit priorities rank equivalent plugins as high, then medium, then low. Within the same tier, "
        "choose by task fit.\n"
        "- Try the highest applicable explicit-priority plugin first. If that plugin is sleeping and its "
        "capability brief matches the task, activate it before selecting a lower-priority equivalent plugin.\n"
        "- If the selected plugin cannot complete the task, returns an error, cannot be activated, "
        "or lacks required capability or constraints, try the next applicable lower-priority plugin.\n"
        "- Do not redundantly call a lower-priority equivalent plugin after a higher-priority plugin "
        "has completed the task.\n"
        "- A plugin with call_priority=auto is selected by your own task-fit judgment and is not forced "
        "into the explicit ranking."
    )
