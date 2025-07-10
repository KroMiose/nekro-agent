import re
from pathlib import Path
from types import ModuleType
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    cast,
)

import aiofiles
from fastapi import APIRouter

from nekro_agent.core import logger
from nekro_agent.core.core_utils import ConfigBase
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_plugin_data import DBPluginData
from nekro_agent.schemas.agent_ctx import AgentCtx

from .schema import PromptInjectMethod, SandboxMethod, SandboxMethodType, WebhookMethod

T = TypeVar("T", bound=ConfigBase)
CollectMethodsFunc = Callable[[AgentCtx], Coroutine[Any, Any, List[SandboxMethod]]]


class NekroPlugin:
    """Nekro 插件基类

    用于描述 Nekro 插件的基本信息和方法挂载功能。
    """

    _Configs: Type[ConfigBase] = ConfigBase
    _config: ConfigBase

    def __init__(
        self,
        name: str,
        module_name: str,
        description: str,
        version: str,
        author: str,
        url: str,
        support_adapter: Optional[List[str]] = None,
        is_builtin: bool = False,
        is_package: bool = False,
    ):
        self.init_method: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
        self.cleanup_method: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
        self.prompt_inject_method: Optional[PromptInjectMethod] = None
        self.on_reset_method: Optional[Callable[[AgentCtx], Coroutine[Any, Any, Any]]] = None
        self.on_message_method: Optional[Callable[[AgentCtx], Coroutine[Any, Any, Any]]] = None
        self.sandbox_methods: List[SandboxMethod] = []
        self.webhook_methods: Dict[str, WebhookMethod] = {}
        self.name = name
        self.module_name = _validate_name(module_name, "Module Name")
        self.description = description.strip()
        self.version = version.strip()
        self.author = _validate_name(author, "Author")
        self.url = url.strip()
        self.support_adapter = support_adapter or []
        self._is_enabled = True
        self._key = f"{self.author}.{self.module_name}"
        self._collect_methods_func: Optional[CollectMethodsFunc] = None
        self._is_builtin: bool = is_builtin  # 标记是否为内置插件
        self._is_package: bool = is_package  # 标记是否为包
        self._module: Optional["ModuleType"] = None  # 模块对象

        # 路由相关
        self._router_func: Optional[Callable[[], APIRouter]] = None
        self._router: Optional[APIRouter] = None

        self._plugin_config_path = Path(OsEnv.DATA_DIR) / "plugin_data" / self.key / "config.yaml"
        self._plugin_path = Path(OsEnv.DATA_DIR) / "plugin_data" / self.key
        self._store = PluginStore(self)

    def reset_methods(self) -> None:
        self.init_method = None
        self.cleanup_method = None
        self.prompt_inject_method = None
        self.on_reset_method = None
        self.sandbox_methods = []
        self.webhook_methods = {}
        self._collect_methods_func = None
        # 重置路由相关
        self._router_func = None
        self._router = None

    def mount_init_method(self) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
        """挂载初始化方法

        Returns:
            装饰器函数
        """

        def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
            self.init_method = func
            return func

        return decorator

    def mount_config(self) -> Callable[[Type[T]], Type[T]]:
        """挂载配置类

        用于挂载配置类，提供给 Nekro 插件使用。

        Returns:
            装饰器函数
        """

        def decorator(cls: Type[T]) -> Type[T]:
            if not issubclass(cls, ConfigBase):
                raise TypeError("Config class must inherit from ConfigBase")
            self._Configs = cls
            self.get_config()
            return cls

        return decorator

    def get_config(self, config_cls: Type[T] = ConfigBase) -> T:
        """获取插件配置

        Args:
            config_cls: 配置类型类，如果不提供则使用插件注册的配置类型

        Returns:
            配置实例，类型为指定的配置类型
        """
        self._plugin_config_path.parent.mkdir(parents=True, exist_ok=True)

        # 获取配置对象
        if not hasattr(self, "_config"):
            # 设置配置类的配置键和文件路径
            config_key = f"plugin_{self.key}"
            self._Configs.set_config_key(config_key)
            self._Configs.set_config_file_path(self._plugin_config_path)

            try:
                self._config = self._Configs.load_config(file_path=self._plugin_config_path, auto_register=True)
            except Exception:
                logger.exception(f"读取插件配置失败: {self.key} | 配置文件格式错误")
                raise
            self._config.dump_config(self._plugin_config_path)
        return cast(config_cls, self._config)

    def get_plugin_path(self) -> Path:
        self._plugin_path.mkdir(parents=True, exist_ok=True)
        return self._plugin_path

    def mount_router(self) -> Callable[[Callable[[], APIRouter]], Callable[[], APIRouter]]:
        """挂载路由生成方法

        用于挂载插件的自定义路由，提供完整的FastAPI路由功能。
        插件路由将挂载在 /plugins/{plugin_key} 路径下。

        Example:
            ```python
            @plugin.mount_router()
            def create_router():
                router = APIRouter()

                @router.get("/hello")
                async def hello():
                    return {"message": "Hello from plugin!"}

                @router.post("/data")
                async def create_data(data: dict):
                    return {"received": data}

                return router
            ```

        Returns:
            装饰器函数
        """

        def decorator(func: Callable[[], APIRouter]) -> Callable[[], APIRouter]:
            self._router_func = func
            # 清除缓存的路由实例，确保重新生成
            self._router = None
            logger.debug(f"插件 {self.name} 路由生成函数注册完成")
            return func

        return decorator

    def get_plugin_router(self) -> Optional[APIRouter]:
        """获取插件路由实例

        Returns:
            Optional[APIRouter]: 插件路由实例，如果插件没有注册路由则返回None
        """

        if not self._router_func:
            return None

        # 如果已有缓存的路由实例，直接返回
        if self._router is not None:
            return self._router

        try:
            # 调用路由生成函数
            self._router = self._router_func()

            if not isinstance(self._router, APIRouter):
                logger.error(f"插件 {self.name} 的路由生成函数必须返回 APIRouter 实例，实际返回: {type(self._router)}")
                return None
        except Exception as e:
            logger.exception(f"插件 {self.name} 生成路由时出错: {e}")
            return None
        else:
            logger.info(f"插件 {self.name} 路由生成成功，路由数量: {len(self._router.routes)}")
            return self._router

    def mount_sandbox_method(
        self,
        method_type: SandboxMethodType,
        name: str,
        description: str = "",
    ) -> Callable[[Callable], Callable]:
        """挂载沙盒方法

        用于挂载沙盒方法，提供给 Nekro 插件使用。

        Args:
            method_type (SandboxMethodType): 方法类型
            name (str): 方法名称
            description (str): 方法描述

        Returns:
            装饰器函数
        """

        def decorator(func: Callable) -> Callable:
            func._method_type = method_type  # noqa: SLF001
            self.sandbox_methods.append(SandboxMethod(method_type, name, description, func))
            # logger.debug(f"从插件 {self.name} 挂载沙盒方法 {name} 成功")
            return func

        return decorator

    def mount_prompt_inject_method(
        self,
        name: str,
        description: str = "",
    ) -> Callable[[Callable[[AgentCtx], Coroutine[Any, Any, str]]], Callable[[AgentCtx], Coroutine[Any, Any, str]]]:
        """挂载提示注入方法

        用于挂载提示注入方法，在对话开始前执行，返回内容会注入到对话提示中。

        Args:
            name (str): 挂载的提示注入方法的名称
            description (str): 挂载的提示注入方法的描述

        Returns:
            装饰器函数
        """

        def decorator(func: Callable[[AgentCtx], Coroutine[Any, Any, str]]) -> Callable[[AgentCtx], Coroutine[Any, Any, str]]:
            self.prompt_inject_method = PromptInjectMethod(name, description, func)
            return func

        return decorator

    def mount_on_channel_reset(
        self,
    ) -> Callable[[Callable[[AgentCtx], Coroutine[Any, Any, Any]]], Callable[[AgentCtx], Coroutine[Any, Any, Any]]]:
        """挂载重置会话回调方法

        用于挂载重置会话时的回调方法，在会话重置时执行。

        Returns:
            装饰器函数
        """

        def decorator(func: Callable[[AgentCtx], Coroutine[Any, Any, Any]]) -> Callable[[AgentCtx], Coroutine[Any, Any, Any]]:
            self.on_reset_method = func
            return func

        return decorator

    def mount_on_message(
        self,
    ) -> Callable[[Callable[[AgentCtx], Coroutine[Any, Any, Any]]], Callable[[AgentCtx], Coroutine[Any, Any, Any]]]:
        """挂载消息回调方法

        用于挂载消息回调方法，在收到消息时执行。

        Returns:
            装饰器函数
        """

        def decorator(func: Callable[[AgentCtx], Coroutine[Any, Any, Any]]) -> Callable[[AgentCtx], Coroutine[Any, Any, Any]]:
            self.on_message_method = func
            return func

        return decorator

    def mount_webhook_method(self, endpoint: str, name: str, description: str = "") -> Callable[[Callable], Callable]:
        """挂载 Webhook 方法

        用于挂载 Webhook 方法，提供 Webhook 事件触发能力

        Args:
            endpoint (str): 挂载的 Webhook 方法的端点
            name (str): 挂载的 Webhook 方法的名称
            description (str): 挂载的 Webhook 方法的描述

        Returns:
            装饰器函数
        """

        def decorator(func: Callable) -> Callable:
            self.webhook_methods[endpoint] = WebhookMethod(name, description, func)
            return func

        return decorator

    def mount_cleanup_method(
        self,
    ) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
        """挂载清理方法

        用于挂载清理方法，在插件卸载时执行。

        Returns:
            装饰器函数
        """

        def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
            self.cleanup_method = func
            return func

        return decorator

    async def collect_available_methods(self, ctx: AgentCtx) -> List[SandboxMethod]:
        """收集可用方法

        Args:
            ctx (AgentCtx): 上下文

        Returns:
            List[SandboxMethod]: 可用方法列表
        """
        if self._collect_methods_func:
            available_methods: List[SandboxMethod] = []
            for func in await self._collect_methods_func(ctx):
                if isinstance(func, SandboxMethod):
                    available_methods.append(func)
                else:
                    for method in self.sandbox_methods:
                        if method.func == func:
                            available_methods.append(method)
                            break
                    else:
                        raise ValueError(f"方法 {func.__name__} 未找到对应的沙盒方法。")
            return available_methods
        return self.sandbox_methods

    def mount_collect_methods(
        self,
    ) -> Callable:
        """挂载收集可用方法的重写函数

        此装饰器允许插件开发者自定义如何收集和过滤可用的方法，根据上下文决定哪些方法对当前用户可用。

        Returns:
            装饰器函数
        """

        def decorator(func: CollectMethodsFunc) -> CollectMethodsFunc:
            self._collect_methods_func = func
            return func

        return decorator

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    def enable(self) -> None:
        self._is_enabled = True

    def disable(self) -> None:
        self._is_enabled = False

    @property
    def key(self) -> str:
        return self._key

    async def render_inject_prompt(self, ctx: AgentCtx) -> str:
        """渲染提示注入提示词

        Returns:
            str: 插件提示
        """
        if self.prompt_inject_method:
            return await self.prompt_inject_method.func(ctx)
        return ""

    async def render_sandbox_methods_prompt(self, ctx: AgentCtx) -> str:
        """渲染沙盒方法提示词

        Returns:
            str: 沙盒方法提示
        """
        prompts: List[str] = []
        methods = await self.collect_available_methods(ctx) if self._collect_methods_func else self.sandbox_methods
        for method in methods:
            if not method.func.__doc__:
                logger.warning(f"方法 {method.func.__name__} 没有可用的文档注解。")
                continue
            if method.method_type in [SandboxMethodType.AGENT, SandboxMethodType.MULTIMODAL_AGENT]:
                prompts.append(
                    f"* {method.func.__name__} - **[AGENT METHOD - STOP AFTER CALL]**\n{method.func.__doc__.strip()}",
                )
            else:
                prompts.append(f"* {method.func.__name__}\n{method.func.__doc__.strip()}")
        return "\n".join(prompts)

    @property
    def store(self) -> "PluginStore":
        return PluginStore(self)

    def _update_plugin_type(self, is_builtin: bool, is_package: bool) -> None:
        if is_builtin:
            self._is_builtin = True
            self._is_package = False
        elif is_package:
            self._is_builtin = False
            self._is_package = True

    @property
    def is_builtin(self) -> bool:
        return self._is_builtin

    @property
    def is_package(self) -> bool:
        return self._is_package

    def get_vector_collection_name(self, key: str = "") -> str:
        """获取向量数据库集合名称

        Args:
            key (str): 向量数据库集合名称

        Returns:
            str: 向量数据库集合名称
        """
        return f"{self.key}-{key}" if key else self.key

    def _set_module(self, module: "ModuleType") -> None:
        """设置模块对象，由加载器调用"""
        self._module = module

    async def get_docs(self) -> Optional[str]:
        """获取插件文档

        优先级:
        1. 插件模块同级目录下的 README.md 文件
        2. 插件模块的 __doc__
        """
        if not self._module or not self._module.__file__:
            return None

        try:
            module_path = Path(self._module.__file__)
            readme_path = module_path.parent / "README.md"

            if readme_path.is_file():
                async with aiofiles.open(readme_path, "r", encoding="utf-8") as f:
                    return await f.read()

            if self._module.__doc__:
                return self._module.__doc__.strip()
        except Exception as e:
            logger.error(f"获取插件 {self.key} 文档失败: {e}")
            return f"获取文档失败: {e}"

        return None


class PluginStore:

    def __init__(self, plugin: NekroPlugin):
        self._plugin = plugin

    async def get(self, chat_key: str = "", user_key: str = "", store_key: str = "") -> Optional[str]:
        """获取插件存储

        Args:
            chat_key (str): 对话键
            user_key (str): 用户键
            store_key (str): 存储键

        Returns:
            Optional[str]: 存储值
        """
        query_result = await DBPluginData.filter(
            plugin_key=self._plugin.key,
            target_chat_key=chat_key,
            target_user_id=user_key,
            data_key=store_key,
        ).first()
        return query_result.data_value if query_result else None

    async def set(self, chat_key: str = "", user_key: str = "", store_key: str = "", value: str = "") -> Literal[0, 1]:
        """设置插件存储

        Args:
            chat_key (str): 对话键
            user_key (str): 用户键
            store_key (str): 存储键
            value (str): 存储值

        Returns:
            int: 设置状态: 0 表示创建成功，1 表示更新成功
        """
        if await DBPluginData.filter(
            plugin_key=self._plugin.key,
            target_chat_key=chat_key,
            target_user_id=user_key,
            data_key=store_key,
        ).first():
            await DBPluginData.filter(
                plugin_key=self._plugin.key,
                target_chat_key=chat_key,
                target_user_id=user_key,
                data_key=store_key,
            ).update(data_value=value)
            return 1
        await DBPluginData.create(
            plugin_key=self._plugin.key,
            target_chat_key=chat_key,
            target_user_id=user_key,
            data_key=store_key,
            data_value=value,
        )
        return 0

    async def delete(self, chat_key: str = "", user_key: str = "", store_key: str = "") -> Literal[0, 1]:
        """删除插件存储

        Args:
            chat_key (str): 对话键
            user_key (str): 用户键
            store_key (str): 存储键

        Returns:
            int: 删除状态: 0 表示删除成功，1 表示删除失败
        """
        record = await DBPluginData.filter(
            plugin_key=self._plugin.key,
            target_chat_key=chat_key,
            target_user_id=user_key,
            data_key=store_key,
        ).first()
        if record:
            await record.delete()
            return 0
        return 1


def _validate_name(name: str, field_name: str) -> str:
    """命名检查，必须由英文字母、数字、下划线组成，且不能以数字开头"""
    name = name.strip()
    if not name:
        raise ValueError(f"{field_name} cannot be empty")
    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        raise ValueError(f"{field_name} must contain only letters, numbers, and underscores")
    if re.match(r"^\d", name):
        raise ValueError(f"{field_name} must not start with a number")
    return name
