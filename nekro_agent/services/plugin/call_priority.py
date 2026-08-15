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


def set_plugin_call_priority(module_name: str, priority: PluginCallPriority) -> None:
    """设置插件调用优先级；自动策略不保存覆盖项。"""
    priorities = dict(config.PLUGIN_CALL_PRIORITIES or {})
    if priority == "auto":
        priorities.pop(module_name, None)
    else:
        priorities[module_name] = priority
    config.PLUGIN_CALL_PRIORITIES = priorities
    ConfigService.save_config(config, CONFIG_PATH)


def build_plugin_call_priority_rules() -> str:
    """构建供大模型执行的插件调用优先级规则。"""
    return (
        "Plugin call priority is a preference only when multiple available plugins "
        "provide equivalent capabilities.\n"
        "- Explicit priorities rank equivalent plugins as high, then medium, then low.\n"
        "- Try the highest applicable explicit-priority plugin first. If it cannot complete the task, "
        "returns an error, "
        "or lacks required capability or constraints, try the next applicable lower-priority plugin.\n"
        "- Do not redundantly call a lower-priority equivalent plugin after a higher-priority plugin "
        "has completed the task.\n"
        "- A plugin with call_priority=auto is selected by your own task-fit judgment and is not forced "
        "into the explicit ranking."
    )
