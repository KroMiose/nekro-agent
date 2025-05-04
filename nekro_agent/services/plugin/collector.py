"""插件收集器

负责插件的加载和管理功能。
"""

import json
import shutil
import sys
from datetime import datetime
from importlib import import_module, reload
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Literal, Optional, Set, Tuple

import git
from pydantic import BaseModel

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import BUILTIN_PLUGIN_DIR, PACKAGES_DIR, WORKDIR_PLUGIN_DIR
from nekro_agent.schemas.agent_ctx import AgentCtx

from .base import NekroPlugin
from .schema import SandboxMethod


class PackageInfo(BaseModel):
    """插件包信息"""

    module_name: str
    git_url: str
    remote_id: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None


class PackageData(BaseModel):
    """插件包信息"""

    packages: List[PackageInfo]
    latest_updated: str

    def get_package_by_module(self, module_name: str) -> Optional[PackageInfo]:
        """根据模块名获取插件包信息"""
        for package in self.packages:
            if package.module_name == module_name:
                return package
        return None

    def add_package(self, package: PackageInfo) -> None:
        """添加插件包信息"""
        if self.get_package_by_module(package.module_name):
            raise ValueError(f"插件包 `{package.module_name}` 已存在")
        self.packages.append(package)
        self.save()

    def remove_package(self, module_name: str) -> None:
        """删除插件包信息"""
        if not self.get_package_by_module(module_name):
            raise ValueError(f"插件包 `{module_name}` 不存在")
        self.packages = [package for package in self.packages if package.module_name != module_name]
        self.save()

    def get_remote_ids(self) -> List[str]:
        """获取所有插件包的远程ID"""
        return [package.remote_id for package in self.packages if package.remote_id]

    def save(self) -> None:
        """保存插件包信息"""
        PACKAGE_DATA_PATH.write_text(json.dumps(self.model_dump(), indent=2, ensure_ascii=False))


PACKAGE_DATA_PATH = Path(PACKAGES_DIR) / "package_data.json"


class PluginCollector:
    """插件收集器，用于管理所有已加载的插件"""

    def __init__(self):
        """初始化插件收集器"""
        # 存储已加载的插件
        self.loaded_plugins: Dict[str, NekroPlugin] = {}
        self.loaded_module_names: Set[str] = set()

        # 初始化插件目录
        self.builtin_plugin_dir = Path(BUILTIN_PLUGIN_DIR)
        self.builtin_plugin_dir.mkdir(parents=True, exist_ok=True)

        self.workdir_plugin_dir = Path(WORKDIR_PLUGIN_DIR)
        self.workdir_plugin_dir.mkdir(parents=True, exist_ok=True)

        self.packages_dir = Path(PACKAGES_DIR)
        self.packages_dir.mkdir(parents=True, exist_ok=True)

        if PACKAGE_DATA_PATH.exists():
            self.package_data: PackageData = PackageData.model_validate_json(PACKAGE_DATA_PATH.read_text())
        else:
            self.package_data = PackageData(packages=[], latest_updated=datetime.now().isoformat())

    async def init_plugins(self) -> None:
        """初始化并加载所有插件"""
        # 将插件目录添加到 Python 路径
        if str(self.builtin_plugin_dir.parent.absolute()) not in sys.path:
            sys.path.insert(0, str(self.builtin_plugin_dir.parent.absolute()))

        # 添加工作目录到 Python 路径
        if str(self.workdir_plugin_dir.parent.absolute()) not in sys.path:
            sys.path.insert(0, str(self.workdir_plugin_dir.parent.absolute()))

        # 添加 packages 目录到 Python 路径
        if str(self.packages_dir.parent.absolute()) not in sys.path:
            sys.path.insert(0, str(self.packages_dir.parent.absolute()))

        # 加载内置插件
        for item in self.builtin_plugin_dir.iterdir():
            await self._try_load_plugin(item, is_builtin=True)

        # 加载工作目录插件
        for item in self.workdir_plugin_dir.iterdir():
            await self._try_load_plugin(item, is_builtin=False)

        # 加载packages插件
        for item in self.packages_dir.iterdir():
            await self._try_load_plugin(item, is_package=True)

    async def unload_plugin_by_module_name(self, module_name: str, scope: Literal["all", "package", "local"] = "all") -> None:
        """卸载指定插件

        Args:
            module_name: 插件模块名
            scope: 卸载范围，可选值：all(所有)、package(仅插件包)、local(仅本地插件)
        """
        if module_name.endswith(".py"):
            module_name = module_name[: -len(".py")]
        if module_name.endswith("/__init__"):
            module_name = module_name[: -len("/__init__")]
        if "/" in module_name:
            raise ValueError(f"插件模块名 `{module_name}` 不在合法的加载目录中")

        plugin = self.get_plugin_by_module_name(module_name)
        if not plugin:
            logger.warning(f"插件 `{module_name}` 不存在")
            return

        # 根据scope限制卸载范围
        if scope == "package" and not plugin.is_package:
            logger.warning(f"插件 {plugin.name} 不是插件包，跳过卸载")
            return

        if scope == "local" and (plugin.is_builtin or plugin.is_package):
            logger.warning(f"插件 {plugin.name} 不是本地插件，跳过卸载")
            return

        if scope != "all" and plugin.is_builtin:
            logger.warning(f"插件 {plugin.name} 是内置插件，跳过卸载")
            return

        if plugin.cleanup_method:
            await plugin.cleanup_method()
            logger.info(f"插件 {plugin.name} 清理完成")

        if plugin.key in self.loaded_plugins:
            del self.loaded_plugins[plugin.key]

        if plugin.module_name in self.loaded_module_names:
            self.loaded_module_names.remove(plugin.module_name)

        logger.info(f"插件 {plugin.name} 卸载完成")

    def _check_module_exists(self, path: Path) -> bool:
        """检查模块是否存在"""
        if path.is_dir():
            return (path / "__init__.py").exists()
        return path.with_suffix(".py").exists()

    def _to_load_path(self, path: Path) -> Path:
        """转换为加载路径"""
        if path.is_dir():
            return path / "__init__.py"
        return path.with_suffix(".py")

    async def reload_plugin_by_module_name(self, module_name: str, is_builtin: bool = False, is_package: bool = False):
        """重新加载指定插件"""
        fixed_module_name = module_name
        if module_name.endswith(".py"):
            fixed_module_name = module_name[: -len(".py")]
        if module_name.endswith("/__init__.py"):
            fixed_module_name = module_name[: -len("/__init__.py")]
        if "/" in module_name:
            raise ValueError(f"插件模块名 `{module_name}` 不在合法的加载目录中")

        builtin_plugin_path = self.builtin_plugin_dir / module_name
        workdir_plugin_path = self.workdir_plugin_dir / module_name
        package_path = self.packages_dir / module_name

        exists_paths = [
            self._to_load_path(p)
            for p in [builtin_plugin_path, workdir_plugin_path, package_path]
            if self._check_module_exists(p)
        ]
        if len(exists_paths) == 0:
            raise ValueError(f"插件 `{module_name}` 不存在")

        if len(exists_paths) > 1:
            logger.warning(
                f"在多个加载目录中发现了重复插件 `{module_name}`，将按照以下优先级加载：内置插件 > 工作目录插件 > 云端插件包",
            )

        real_path = exists_paths[0]

        loaded_plugin = self.get_plugin_by_module_name(fixed_module_name)
        if loaded_plugin:
            logger.info(f"插件 `{module_name}` 已加载，正在重载...")
            if loaded_plugin.cleanup_method:
                await loaded_plugin.cleanup_method()
                logger.info(f"插件 {loaded_plugin.name} 清理完成")
            if loaded_plugin.key in self.loaded_plugins:
                del self.loaded_plugins[loaded_plugin.key]
            if loaded_plugin.module_name in self.loaded_module_names:
                self.loaded_module_names.remove(loaded_plugin.module_name)
            # 卸载旧插件模块，保证后续重新 import 执行最新代码
            # 从 loaded_module_names 中找到原始模块路径
            orig_mod = next((m for m in self.loaded_module_names if m.endswith(f".{fixed_module_name}")), None)
            if orig_mod and orig_mod in sys.modules:
                logger.debug(f"卸载旧插件模块 {orig_mod}")
                sys.modules.pop(orig_mod, None)
                self.loaded_module_names.discard(orig_mod)
            else:
                logger.warning(f"未找到原始模块 {fixed_module_name}，无法卸载旧模块")

        # logger.debug(f"尝试加载插件: {real_path} 从 {fixed_module_name}")
        await self._try_load_plugin(real_path, is_builtin=is_builtin, is_package=is_package)

    async def clone_package(
        self,
        module_name: str,
        git_url: str,
        remote_id: str,
        auto_load: bool = False,
    ) -> None:
        """克隆插件包

        Args:
            module_name: 插件包模块名
            git_url: 插件包Git URL
            remote_id: 插件包远程ID
            version: 插件包版本
            auto_load: 是否自动加载插件
        """
        package_dir = self.packages_dir / module_name
        if package_dir.exists():
            raise ValueError(f"插件包 `{module_name}` 已存在")

        env = {}
        if config.PLUGIN_UPDATE_USE_PROXY and config.DEFAULT_PROXY:
            env["HTTP_PROXY"] = config.DEFAULT_PROXY
            env["HTTPS_PROXY"] = config.DEFAULT_PROXY
            logger.info(f"使用代理 {config.DEFAULT_PROXY} 克隆插件包 {module_name} 从 {git_url}")

        git.Repo.clone_from(git_url, package_dir, env=env)
        self.package_data.add_package(
            PackageInfo(module_name=module_name, git_url=git_url, remote_id=remote_id),
        )
        if auto_load:
            await self.reload_plugin_by_module_name(module_name)

    async def update_package(self, module_name: str, auto_reload: bool = False) -> None:
        """更新插件包

        Args:
            module_name: 插件包模块名
            auto_reload: 是否自动重新加载插件
        """
        package_dir = self.packages_dir / module_name
        if not package_dir.exists():
            raise ValueError(f"插件包 `{module_name}` 不存在")

        try:
            repo = git.Repo(package_dir)
            env = {}
            if config.PLUGIN_UPDATE_USE_PROXY and config.DEFAULT_PROXY:
                env["HTTP_PROXY"] = config.DEFAULT_PROXY
                env["HTTPS_PROXY"] = config.DEFAULT_PROXY
                logger.info(f"使用代理 {config.DEFAULT_PROXY} 更新插件包 {module_name}")
            # 使用 repo.git.pull 并传递 env
            repo.git.pull("origin", env=env)
        except Exception as e:
            logger.error(f"更新插件包 `{module_name}` 失败: {e}")
            raise

        if auto_reload:
            await self.reload_plugin_by_module_name(module_name, is_package=True)

    async def remove_package(self, module_name: str) -> None:
        """删除插件包

        Args:
            module_name: 插件包模块名
        """
        package_dir = self.packages_dir / module_name
        if not package_dir.exists():
            raise ValueError(f"插件包 `{module_name}` 不存在")

        # 先卸载插件，从插件收集器中移除，限制只卸载插件包
        await self.unload_plugin_by_module_name(module_name, scope="package")

        # 然后删除文件和包信息
        shutil.rmtree(package_dir)
        self.package_data.remove_package(module_name)

    async def _try_load_plugin(self, item_path: Path, is_builtin: bool = False, is_package: bool = False) -> bool:
        """尝试加载插件

        Args:
            item_path: 插件路径（可能是文件或目录）
            is_builtin: 是否为内置插件
            is_package: 是否为插件包
        """
        if item_path.is_dir() and item_path.name == "__pycache__":
            return False
        # 如果是Python文件
        if item_path.is_file() and item_path.suffix == ".py" and item_path.name != "__init__.py":
            module_path = f"{item_path.parent.name}.{item_path.stem}"
            await self._load_plugin_module(module_path, item_path, is_builtin, is_package)
            return True
        # 如果是目录且包含 __init__.py（Python包）
        if item_path.is_dir() and (item_path / "__init__.py").exists():
            module_path = f"{item_path.parent.name}.{item_path.name}"
            await self._load_plugin_module(module_path, item_path, is_builtin, is_package)
            return True
        # 如果目录已经是完整的 __init__.py 文件
        if item_path.is_file() and item_path.suffix == ".py" and item_path.name == "__init__.py":
            module_path = f"{item_path.parent.parent.name}.{item_path.parent.name}"
            await self._load_plugin_module(module_path, item_path, is_builtin, is_package)
            return True
        return False

    async def _load_plugin_module(
        self,
        module_path: str,
        path: Path,
        is_builtin: bool = False,
        is_package: bool = False,
    ) -> None:
        """加载插件模块

        Args:
            module_path: 模块导入路径
            path: 文件或目录路径（用于日志）
            is_builtin: 是否为内置插件
            is_package: 是否为插件包
        """
        # logger.info(f"正在加载插件: {module_path} 从 {path}")
        try:
            module = import_module(module_path)
        except Exception as e:
            logger.exception(f"加载插件失败 {path}: {e}")
            return

        if hasattr(module, "plugin"):
            plugin = module.plugin

            if isinstance(plugin, NekroPlugin):
                # 直接设置内置插件标识
                try:
                    if plugin.init_method:
                        await plugin.init_method()
                except Exception as e:
                    logger.exception(f'插件 "{plugin.name}" 初始化失败 {path}: {e}')
                    return

                logger.success(
                    f'插件加载成功: "{plugin.name}" by "{plugin.author or "未知"}"{" [内置]" if is_builtin else ""}{" [云端]" if is_package else ""}',
                )
                plugin._update_plugin_type(is_builtin, is_package)  # noqa: SLF001
                if plugin.key not in config.PLUGIN_ENABLED:
                    plugin.disable()
                self.loaded_plugins[plugin.key] = plugin
                self.loaded_module_names.add(module_path)
            else:
                logger.error(f"插件实例类型错误: {path}")
        else:
            logger.error(f"模块未找到插件实例: {path}")

    def get_plugin(self, key: str) -> Optional[NekroPlugin]:
        """根据插件键获取插件实例

        Args:
            key: 插件键，格式为 "作者.插件名"

        Returns:
            Optional[NekroPlugin]: 插件实例，如果不存在则返回 None
        """
        return self.loaded_plugins.get(key)

    def get_plugin_by_module_name(self, module_name: str) -> Optional[NekroPlugin]:
        """根据模块名获取插件实例

        Args:
            module_name: 插件模块名
        """
        for plugin in self.loaded_plugins.values():
            if plugin.module_name == module_name:
                return plugin
        return None

    def get_all_plugins(self) -> List[NekroPlugin]:
        """获取所有已加载的插件

        Returns:
            List[NekroPlugin]: 插件列表
        """
        return list(self.loaded_plugins.values())

    def get_all_package_plugins(self) -> List[NekroPlugin]:
        """获取所有已加载的插件包插件

        Returns:
            List[NekroPlugin]: 插件列表
        """
        return [plugin for plugin in self.loaded_plugins.values() if plugin.is_package]

    def get_all_active_plugins(self) -> List[NekroPlugin]:
        """获取所有已加载且启用的插件

        Returns:
            List[NekroPlugin]: 插件列表
        """
        return [plugin for plugin in self.loaded_plugins.values() if plugin.is_enabled]

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

    async def get_all_sandbox_methods(self, ctx: Optional[AgentCtx] = None) -> List[SandboxMethod]:
        """获取所有沙盒方法

        Returns:
            List[SandboxMethod]: 沙盒方法列表
        """
        methods: List[SandboxMethod] = []
        for plugin in self.loaded_plugins.values():
            if plugin.is_enabled:
                if ctx:
                    methods.extend(await plugin.collect_available_methods(ctx))
                else:
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

    async def chat_channel_on_reset(self, ctx: AgentCtx) -> None:
        """聊天频道重置时执行"""
        for plugin in self.loaded_plugins.values():
            if plugin.is_enabled and plugin.on_reset_method:
                await plugin.on_reset_method(ctx.model_copy())


# 全局插件收集器实例
plugin_collector = PluginCollector()


async def init_plugins() -> None:
    """初始化并加载所有插件"""
    await plugin_collector.init_plugins()
