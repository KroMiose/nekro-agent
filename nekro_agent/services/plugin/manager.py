"""插件管理服务

提供插件的管理相关功能，如获取插件列表、配置管理等。
"""

import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from nekro_agent.core import logger
from nekro_agent.core.config import CONFIG_PATH, config
from nekro_agent.core.core_utils import ConfigBase
from nekro_agent.services.config_service import ConfigService
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.plugin.schema import SandboxMethodType


async def get_all_ext_meta_data() -> List[dict]:
    """获取所有已注册插件的元数据"""
    plugins = plugin_collector.get_all_plugins()
    return [
        {
            "id": plugin.key,
            "name": plugin.name,
            "description": plugin.description,
            "version": plugin.version,
            "author": plugin.author,
            "enabled": plugin.is_enabled,
            "hasConfig": hasattr(plugin, "_Configs") and plugin._Configs != ConfigBase,  # noqa: SLF001
            "url": plugin.url or "",
            "isBuiltin": plugin.is_builtin,
            "isPackage": plugin.is_package,
        }
        for plugin in plugins
    ]


async def get_plugin_detail(plugin_id: str) -> Optional[dict]:
    """获取指定插件的详细信息"""
    plugin = plugin_collector.get_plugin(plugin_id)
    if not plugin:
        return None

    # 获取方法信息
    methods = [
        {
            "name": method.name,
            "type": method.method_type.value,
            "description": method.description or "",
        }
        for method in plugin.sandbox_methods
    ]

    # 获取 webhook 信息
    webhooks = [
        {
            "endpoint": endpoint,
            "name": method.name,
            "description": method.description or "",
        }
        for endpoint, method in plugin.webhook_methods.items()
    ]

    # 构建插件详情
    return {
        "name": plugin.name,
        "moduleName": plugin.module_name,
        "id": plugin.key,
        "version": plugin.version,
        "description": plugin.description,
        "author": plugin.author,
        "url": plugin.url or "",
        "enabled": plugin.is_enabled,
        "hasConfig": hasattr(plugin, "_Configs") and plugin._Configs != ConfigBase,  # noqa: SLF001
        "methods": methods,
        "webhooks": webhooks,
        "isBuiltin": plugin.is_builtin,
        "isPackage": plugin.is_package,
    }


async def enable_plugin(plugin_id: str) -> bool:
    """启用插件"""
    plugin = plugin_collector.get_plugin(plugin_id)
    if not plugin:
        return False

    if plugin.is_enabled:
        return True  # 已经启用，直接返回成功

    try:
        plugin.enable()
        if plugin.key not in config.PLUGIN_ENABLED:
            config.PLUGIN_ENABLED.append(plugin.key)
            ConfigService.save_config(config, CONFIG_PATH)
    except Exception as e:
        logger.error(f"启用插件失败: {plugin_id}, 错误: {e}")
        return False
    else:
        return True


async def disable_plugin(plugin_id: str) -> bool:
    """禁用插件"""
    plugin = plugin_collector.get_plugin(plugin_id)
    if not plugin:
        return False

    if not plugin.is_enabled:
        return True  # 已经禁用，直接返回成功

    try:
        plugin.disable()
        if plugin.key in config.PLUGIN_ENABLED:
            config.PLUGIN_ENABLED.remove(plugin.key)
            ConfigService.save_config(config, CONFIG_PATH)
    except Exception as e:
        logger.error(f"禁用插件失败: {plugin_id}, 错误: {e}")
        return False
    else:
        return True


async def get_plugin_config(plugin_id: str) -> Optional[List[Dict[str, Any]]]:
    """获取插件配置列表"""
    plugin = plugin_collector.get_plugin(plugin_id)
    if not plugin or not hasattr(plugin, "_Configs") or plugin._Configs == ConfigBase:  # noqa: SLF001
        return None

    try:
        config = plugin.get_config()
        if not config:
            return None

        # 使用配置服务获取配置列表
        return ConfigService.get_config_list(config)
    except Exception as e:
        logger.error(f"获取插件配置失败: {plugin_id}, 错误: {e}")
        return None


async def save_plugin_config(plugin_id: str, configs: Dict[str, str]) -> Tuple[bool, Optional[str]]:
    """保存插件配置

    Args:
        plugin_id: 插件ID
        configs: 配置项字典，键为配置项名称，值为字符串形式的配置值

    Returns:
        (成功状态, 错误信息)
    """
    plugin = plugin_collector.get_plugin(plugin_id)
    if not plugin or not hasattr(plugin, "_Configs") or plugin._Configs == ConfigBase:  # noqa: SLF001
        return False, f"插件 {plugin_id} 不存在或无配置"

    try:
        config = plugin.get_config()
        if not config:
            return False, f"插件 {plugin_id} 配置获取失败"

        # 使用配置服务批量更新配置
        success, error_msg = ConfigService.batch_update_config(config, configs)
        if not success:
            return False, error_msg

        # 保存配置
        success, error_msg = ConfigService.save_config(config, plugin._plugin_config_path)  # noqa: SLF001
        if not success:
            return False, f"保存配置失败: {error_msg}"

    except Exception as e:
        logger.error(f"保存插件配置失败: {plugin_id}, 错误: {e}")
        return False, f"保存失败: {e!s}"
    else:
        return True, None
