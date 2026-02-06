import asyncio
import re
from pathlib import Path
from types import ModuleType
from typing import (
    Any,
    AsyncGenerator,
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
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_plugin_data import DBPluginData
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.schemas.chat_message import ChatMessage
from nekro_agent.schemas.i18n import I18nDict, SupportedLang, get_text
from nekro_agent.schemas.signal import MsgSignal
from nekro_agent.services.plugin.task import TaskRunner

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
        i18n_name: Optional[I18nDict] = None,
        i18n_description: Optional[I18nDict] = None,
    ):
        """
        Args:
            name: 插件名称（默认）
            module_name: 插件模块名
            description: 插件描述（默认）
            version: 插件版本
            author: 插件作者
            url: 插件地址
            support_adapter: 支持的适配器
            i18n_name: 插件名称国际化
            i18n_description: 插件描述国际化

        可用回调方法:
            init_method: 初始化方法
            collect_methods_func: 收集可用方法的重写函数
            prompt_inject_method: 提示注入方法
            on_user_message_method: 消息回调方法
            on_system_message_method: 系统消息回调方法
            sandbox_methods: 沙盒方法
            on_reset_method: 重置频道回调方法
            cleanup_method: 清理方法
            mount_router: 挂载路由方法
        """

        # 回调方法
        self.init_method: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
        self.cleanup_method: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
        self.prompt_inject_method: Optional[PromptInjectMethod] = None
        self.on_reset_method: Optional[Callable[[AgentCtx], Coroutine[Any, Any, Any]]] = None
        self.on_user_message_method: Optional[Callable[[AgentCtx, ChatMessage], Coroutine[Any, Any, MsgSignal | None]]] = None
        self.on_system_message_method: Optional[Callable[[AgentCtx, str], Coroutine[Any, Any, MsgSignal | None]]] = None

        self.sandbox_methods: List[SandboxMethod] = []
        self.webhook_methods: Dict[str, WebhookMethod] = {}
        self.name = name
        self.module_name = _validate_name(module_name, "Module Name")
        self.description = description.strip()
        self.version = version.strip()
        self.author = _validate_name(author, "Author")
        self.url = url.strip()
        self.support_adapter = support_adapter or []
        self.i18n_name = i18n_name
        self.i18n_description = i18n_description
        self._is_enabled = True
        self._key = f"{self.author}.{self.module_name}"

        # 插件子 logger：用于前端按插件过滤日志
        # 约定字段：
        # - subsystem="plugin"
        # - plugin_key=author.module_name
        self.logger = get_sub_logger("plugin", log_name=f"plugin.{self._key}", plugin_key=self._key)
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

        # 生命周期回调存储
        self._on_enabled_callbacks: List[Callable[[], Coroutine[Any, Any, None]]] = []
        self._on_disabled_callbacks: List[Callable[[], Coroutine[Any, Any, None]]] = []

        # 异步任务注册
        self._async_tasks: Dict[str, Callable[..., AsyncGenerator[Any, None]]] = {}

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
        # 重置异步任务
        self._async_tasks = {}

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
                self.logger.exception(f"读取插件配置失败: {self.key} | 配置文件格式错误")
                raise
            self._config.dump_config(self._plugin_config_path)
        return cast(config_cls, self._config)  # pyright: ignore[reportInvalidTypeForm]

    def save_config(self, config: ConfigBase) -> None:
        """保存插件配置

        Args:
            config: 配置实例，必须是已注册的配置类型的实例

        Raises:
            TypeError: 当传入的配置实例类型与注册的配置类型不匹配时
            Exception: 当配置保存失败时
        """
        if not isinstance(config, self._Configs):
            raise TypeError("存入的配置项类型有误")

        self._plugin_config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 更新内部配置实例
            self._config = config
            # 保存配置到文件
            config.dump_config(self._plugin_config_path)
            self.logger.debug(f"插件 {self.key} 配置保存成功")
        except Exception:
            self.logger.exception(f"保存插件配置失败: {self.key} | 配置文件写入错误")
            raise

    def get_plugin_path(self) -> Path:
        """获取插件路径
        
        .. deprecated:: 
            使用 get_plugin_data_dir() 代替，语义更明确
        """
        import warnings
        warnings.warn(
            "get_plugin_path() 已弃用，请使用 get_plugin_data_dir() 代替",
            DeprecationWarning,
            stacklevel=2,
        )
        self._plugin_path.mkdir(parents=True, exist_ok=True)
        return self._plugin_path
    
    def get_plugin_data_dir(self) -> Path:
        """获取插件数据目录
        
        返回插件专属的数据存储目录，用于存储插件的运行时数据、日志、缓存等。
        目录位于 DATA_DIR/plugin_data/{author}.{module_name}/
        
        Returns:
            Path: 插件数据目录的 Path 对象，目录会自动创建
            
        Example:
            ```python
            data_dir = plugin.get_plugin_data_dir()
            log_file = data_dir / "logs" / "app.log"
            ```
        """
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
            self.logger.debug(f"插件 {self.name} 路由生成函数注册完成")
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
                self.logger.error(f"插件 {self.name} 的路由生成函数必须返回 APIRouter 实例，实际返回: {type(self._router)}")
                return None
        except Exception:
            self.logger.exception(f"插件 {self.name} 生成路由时出错")
            return None
        else:
            self.logger.info(f"插件 {self.name} 路由生成成功，路由数量: {len(self._router.routes)}")
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
            func._method_type = method_type  # noqa: SLF001  # pyright: ignore[reportFunctionMemberAccess]
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
        """挂载重置频道回调方法

        用于挂载重置频道时的回调方法，在频道重置时执行。

        Returns:
            装饰器函数
        """

        def decorator(func: Callable[[AgentCtx], Coroutine[Any, Any, Any]]) -> Callable[[AgentCtx], Coroutine[Any, Any, Any]]:
            self.on_reset_method = func
            return func

        return decorator

    def mount_on_user_message(
        self,
    ) -> Callable[
        [Callable[[AgentCtx, ChatMessage], Coroutine[Any, Any, MsgSignal | None]]],
        Callable[[AgentCtx, ChatMessage], Coroutine[Any, Any, MsgSignal | None]],
    ]:
        """挂载消息回调方法

        用于挂载消息回调方法，在收到消息时执行。

        Returns:
            装饰器函数
        """

        def decorator(
            func: Callable[[AgentCtx, ChatMessage], Coroutine[Any, Any, MsgSignal | None]],
        ) -> Callable[[AgentCtx, ChatMessage], Coroutine[Any, Any, MsgSignal | None]]:
            self.on_user_message_method = func
            return func

        return decorator

    def mount_on_system_message(
        self,
    ) -> Callable[
        [Callable[[AgentCtx, str], Coroutine[Any, Any, MsgSignal | None]]],
        Callable[[AgentCtx, str], Coroutine[Any, Any, MsgSignal | None]],
    ]:
        """挂载系统消息回调方法"""

        def decorator(
            func: Callable[[AgentCtx, str], Coroutine[Any, Any, MsgSignal | None]],
        ) -> Callable[[AgentCtx, str], Coroutine[Any, Any, MsgSignal | None]]:
            self.on_system_message_method = func
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
    
        用于挂载清理方法,在插件卸载时执行。
    
        Returns:
            装饰器函数
        """
    
        def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
            self.cleanup_method = func
            return func
    
        return decorator

    def mount_async_task(
        self,
        task_type: str,
    ) -> Callable[[Callable[..., AsyncGenerator[Any, None]]], Callable[..., AsyncGenerator[Any, None]]]:
        """挂载异步任务

        用于注册异步任务函数，任务函数通过 yield TaskCtl 报告状态，
        通过 AsyncTaskHandle.wait() 暂停等待外部信号。

        Args:
            task_type: 任务类型标识，用于启动和查询任务

        Returns:
            装饰器函数

        Example:
            ```python
            @plugin.mount_async_task("video_gen")
            async def video_generation(handle: AsyncTaskHandle, prompt: str):
                yield TaskCtl.report_progress("等待审批")
                approved = await handle.wait("approval", timeout=3600)
                if approved:
                    yield TaskCtl.success("完成", data=url)
                else:
                    yield TaskCtl.fail("审批被拒绝")
            ```
        """
        def decorator(func: Callable[..., AsyncGenerator[Any, None]]) -> Callable[..., AsyncGenerator[Any, None]]:
            self._async_tasks[task_type] = func
            # 注册到全局 TaskRunner
            TaskRunner().register_task_type(task_type, func)
            self.logger.debug(f"插件 {self.name} 注册异步任务: {task_type}")
            return func

        return decorator
    
    def on_enabled(self) -> Callable[[Callable[[], Coroutine[Any, Any, None]]], Callable[[], Coroutine[Any, Any, None]]]:
        """装饰器：注册插件启用时的回调函数
    
        回调将在插件状态变更为启用后立即执行（在配置保存和路由挂载之前）。
    
        Returns:
            装饰器函数
    
        Example:
            ```python
            @plugin.on_enabled()
            async def handle_enabled():
                print("插件已启用")
            ```
        """
    
        def decorator(func: Callable[[], Coroutine[Any, Any, None]]) -> Callable[[], Coroutine[Any, Any, None]]:
            self._on_enabled_callbacks.append(func)
            return func
    
        return decorator
    
    def on_disabled(self) -> Callable[[Callable[[], Coroutine[Any, Any, None]]], Callable[[], Coroutine[Any, Any, None]]]:
        """装饰器：注册插件禁用时的回调函数
    
        回调将在插件状态变更为禁用后立即执行（在配置保存之前）。
    
        Returns:
            装饰器函数
    
        Example:
            ```python
            @plugin.on_disabled()
            async def handle_disabled():
                print("插件已禁用")
            ```
        """
    
        def decorator(func: Callable[[], Coroutine[Any, Any, None]]) -> Callable[[], Coroutine[Any, Any, None]]:
            self._on_disabled_callbacks.append(func)
            return func
    
        return decorator
    
    async def trigger_callbacks(self, event_type: Literal["enabled", "disabled"]) -> None:
        """触发回调函数
    
        并行执行所有已注册的回调函数，异常会被捕获并记录日志。
        此方法由插件管理器在启用/禁用插件时调用。
    
        Args:
            event_type: 事件类型（"enabled" 或 "disabled"）
        """
        callbacks = self._on_enabled_callbacks if event_type == "enabled" else self._on_disabled_callbacks
    
        if not callbacks:
            return
    
        self.logger.debug(f"插件 {self.name} 触发 {event_type} 回调，共 {len(callbacks)} 个")
    
        # 并行执行所有回调
        results = await asyncio.gather(*[cb() for cb in callbacks], return_exceptions=True)
    
        # 记录异常
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"插件 {self.name} 的 {event_type} 回调执行失败 (回调索引 {i}): {result}")

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

    async def enable(self) -> None:
        """启用插件并触发相应的回调函数
        
        此方法是启用插件的统一入口，确保无论从何处调用，
        都会自动执行状态变更和触发回调事件。
        """
        if self._is_enabled:
            return  # 已经启用，无需重复操作
        
        self._is_enabled = True
        # 自动触发启用回调
        await self.trigger_callbacks("enabled")

    async def disable(self) -> None:
        """禁用插件并触发相应的回调函数
        
        此方法是禁用插件的统一入口，确保无论从何处调用，
        都会自动执行状态变更和触发回调事件。
        """
        if not self._is_enabled:
            return  # 已经禁用，无需重复操作
        
        self._is_enabled = False
        # 自动触发禁用回调
        await self.trigger_callbacks("disabled")

    @property
    def key(self) -> str:
        return self._key

    def get_name(self, lang: SupportedLang = SupportedLang.ZH_CN) -> str:
        """获取本地化插件名称

        Args:
            lang: 目标语言

        Returns:
            本地化插件名称，如果无对应翻译则返回默认名称
        """
        return get_text(self.i18n_name, self.name, lang)

    def get_description(self, lang: SupportedLang = SupportedLang.ZH_CN) -> str:
        """获取本地化插件描述

        Args:
            lang: 目标语言

        Returns:
            本地化插件描述，如果无对应翻译则返回默认描述
        """
        return get_text(self.i18n_description, self.description, lang)

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
                self.logger.warning(f"方法 {method.func.__name__} 没有可用的文档注解。")
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
            self.logger.exception(f"获取插件 {self.key} 文档失败")
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
