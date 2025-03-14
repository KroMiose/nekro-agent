"""插件收集器

负责插件的加载和管理功能。
"""

import sys
from importlib import import_module
from pathlib import Path
from typing import Any, Awaitable, Callable, Coroutine, Dict, List, Optional, Tuple

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import BUILTIN_PLUGIN_DIR, WORKDIR_PLUGIN_DIR

from .base import NekroPlugin
from .schema import SandboxMethod


class PluginCollector:
    """插件收集器，用于管理所有已加载的插件"""

    def __init__(self):
        """初始化插件收集器"""
        # 存储已加载的插件
        self.loaded_plugins: Dict[str, NekroPlugin] = {}

        # 初始化插件目录
        self.builtin_plugin_dir = Path(BUILTIN_PLUGIN_DIR)
        self.builtin_plugin_dir.mkdir(parents=True, exist_ok=True)

        self.workdir_plugin_dir = None
        if WORKDIR_PLUGIN_DIR:
            self.workdir_plugin_dir = Path(WORKDIR_PLUGIN_DIR)
            self.workdir_plugin_dir.mkdir(parents=True, exist_ok=True)

    def init_plugins(self) -> None:
        """初始化并加载所有插件"""
        # 将插件目录添加到 Python 路径
        parent_dir = self.builtin_plugin_dir.parent
        if str(parent_dir.absolute()) not in sys.path:
            sys.path.insert(0, str(parent_dir.absolute()))

        # 加载内置插件
        if self.builtin_plugin_dir.exists():
            for item in self.builtin_plugin_dir.iterdir():
                self._try_load_plugin(item)

        # 加载工作目录插件
        if self.workdir_plugin_dir and self.workdir_plugin_dir.exists():
            for item in self.workdir_plugin_dir.iterdir():
                self._try_load_plugin(item)

    def _try_load_plugin(self, item_path: Path) -> None:
        """尝试加载插件

        Args:
            item_path: 插件路径（可能是文件或目录）
        """
        # 如果是Python文件
        if item_path.is_file() and item_path.suffix == ".py" and item_path.name != "__init__.py":
            module_path = f"{item_path.parent.name}.{item_path.stem}"
            self._load_plugin_module(module_path, item_path)

        # 如果是目录且包含 __init__.py（Python包）
        elif item_path.is_dir() and (item_path / "__init__.py").exists():
            module_path = f"{item_path.parent.name}.{item_path.name}"
            self._load_plugin_module(module_path, item_path)

    def _load_plugin_module(self, module_path: str, path: Path) -> None:
        """加载插件模块

        Args:
            module_path: 模块导入路径
            path: 文件或目录路径（用于日志）
        """
        logger.info(f"正在加载插件: {module_path} 从 {path}")
        try:
            module = import_module(module_path)

            if hasattr(module, "plugin"):
                plugin = module.plugin

                if isinstance(plugin, NekroPlugin):
                    logger.success(
                        f'插件加载成功: "[{plugin.key}] {plugin.name}" by "{plugin.author or "未知"}"',
                    )
                    self.loaded_plugins[plugin.key] = plugin
                else:
                    logger.warning(f"插件实例类型错误: {path}")
            else:
                logger.warning(f"模块未找到插件实例: {path}")
        except Exception as e:
            logger.exception(f"加载插件失败 {path}: {e}")

    def get_plugin(self, key: str) -> Optional[NekroPlugin]:
        """根据插件键获取插件实例

        Args:
            key: 插件键，格式为 "作者.插件名"

        Returns:
            Optional[NekroPlugin]: 插件实例，如果不存在则返回 None
        """
        return self.loaded_plugins.get(key)

    def get_all_plugins(self) -> List[NekroPlugin]:
        """获取所有已加载的插件

        Returns:
            List[NekroPlugin]: 插件列表
        """
        return list(self.loaded_plugins.values())

    def get_method(self, method_name: str) -> Optional[Callable[..., Coroutine[Any, Any, Any]]]:
        """获取指定方法

        Args:
            method_name: 方法名

        Returns:
            Optional[Callable]: 方法实例，如果不存在则返回 None
        """
        for plugin in self.loaded_plugins.values():
            for method in plugin.sandbox_methods:
                if method.func.__name__ == method_name:
                    return method.func
        return None

    def get_all_sandbox_methods(self) -> List[SandboxMethod]:
        """获取所有沙盒方法

        Returns:
            List[SandboxMethod]: 沙盒方法列表
        """
        methods: List[SandboxMethod] = []
        for plugin in self.loaded_plugins.values():
            if plugin.is_enabled and plugin.sandbox_methods:
                methods.extend(plugin.sandbox_methods)
        logger.debug(f"获取到 {len(methods)} 个沙盒方法")
        return methods

    def get_webhook_method(self, plugin_key: str, endpoint: str) -> Optional[Callable[..., Coroutine[Any, Any, Any]]]:
        """获取指定插件的webhook方法

        Args:
            plugin_key: 插件键
            endpoint: webhook端点路径

        Returns:
            Optional[Callable]: webhook方法实例，如果不存在则返回 None
        """
        plugin = self.get_plugin(plugin_key)
        if not plugin or not plugin.is_enabled:
            return None

        if endpoint in plugin.webhook_methods:
            return plugin.webhook_methods[endpoint].func
        return None

    def get_webhook_methods_by_endpoint(self, endpoint: str) -> List[Tuple[str, Callable[..., Coroutine[Any, Any, Any]]]]:
        """获取所有注册了指定endpoint的webhook方法

        Args:
            endpoint: webhook端点路径

        Returns:
            List[Tuple[str, Callable]]: 包含插件键和webhook方法的元组列表
        """
        methods: List[Tuple[str, Callable[..., Coroutine[Any, Any, Any]]]] = []
        for plugin_key, plugin in self.loaded_plugins.items():
            if not plugin.is_enabled:
                continue

            if endpoint in plugin.webhook_methods:
                methods.append((plugin_key, plugin.webhook_methods[endpoint].func))

        logger.debug(f"获取到 {len(methods)} 个处理 {endpoint} 的webhook方法")
        return methods

    def get_all_webhook_methods(self) -> Dict[str, Dict[str, Callable[..., Coroutine[Any, Any, Any]]]]:
        """获取所有webhook方法

        Returns:
            Dict[str, Dict[str, Callable]]: 以插件键和endpoint为键的webhook方法字典
        """
        webhook_methods: Dict[str, Dict[str, Callable[..., Coroutine[Any, Any, Any]]]] = {}
        for plugin_key, plugin in self.loaded_plugins.items():
            if plugin.is_enabled and plugin.webhook_methods:
                webhook_methods[plugin_key] = {endpoint: method.func for endpoint, method in plugin.webhook_methods.items()}
        logger.debug(f"获取到 {sum(len(methods) for methods in webhook_methods.values())} 个webhook方法")
        return webhook_methods


# 全局插件收集器实例
plugin_collector = PluginCollector()


def init_plugins() -> None:
    """初始化并加载所有插件"""
    plugin_collector.init_plugins()
