import inspect
import re
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    cast,
    overload,
)

from nekro_agent.core import logger
from nekro_agent.core.core_utils import ConfigBase
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_plugin_data import DBPluginData
from nekro_agent.schemas.agent_ctx import AgentCtx

from .schema import PromptInjectMethod, SandboxMethod, SandboxMethodType, WebhookMethod

T = TypeVar("T", bound=ConfigBase)


class NekroPlugin(Generic[T]):
    """Nekro 插件基类

    用于描述 Nekro 插件的基类，提供插件的基本信息和方法挂载功能。
    """

    _Configs: Type[ConfigBase] = ConfigBase
    _config: ConfigBase

    def __init__(self, name: str, module_name: str, description: str, version: str, author: str, url: str):
        self.init_method: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
        self.cleanup_method: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
        self.prompt_inject_method: Optional[PromptInjectMethod] = None
        self.sandbox_methods: List[SandboxMethod] = []
        self.webhook_methods: Dict[str, WebhookMethod] = {}
        self.name = name
        self.module_name = _validate_name(module_name, "Module Name")
        self.description = description.strip()
        self.version = version.strip()
        self.author = _validate_name(author, "Author")
        self.url = url.strip()
        self._is_enabled = True
        self._key = f"{self.author}.{self.module_name}"

        self._plugin_config_path = Path(OsEnv.DATA_DIR) / "plugins" / self.name / "config.yaml"
        self._plugin_path = Path(OsEnv.DATA_DIR) / "plugins" / self.name
        self._store = PluginStore(self)

    def reset_methods(self):
        self.init_method = None
        self.cleanup_method = None
        self.prompt_inject_method = None
        self.sandbox_methods = []
        self.webhook_methods = {}

    def mount_config(self):
        """挂载配置类

        用于挂载配置类，提供给 Nekro 插件使用。
        """

        def decorator(cls: Type[T]) -> T:
            if not issubclass(cls, ConfigBase):
                raise TypeError("Config class must inherit from ConfigBase")
            self._Configs = cls
            return cls  # type: ignore

        return decorator

    @overload
    def get_config(self) -> ConfigBase: ...

    @overload
    def get_config(self, config_cls: Type) -> Any: ...

    def get_config(self, config_cls=None):  # type: ignore
        """获取插件配置

        Args:
            config_cls: 配置类型类，如果不提供则使用插件注册的配置类型

        Returns:
            配置实例，类型为指定的配置类型
        """
        self._plugin_config_path.parent.mkdir(parents=True, exist_ok=True)

        # 获取配置对象
        if hasattr(self, "_config"):
            config = self._config
        else:
            config = self._Configs.load_config(file_path=self._plugin_config_path)

        # 如果提供了类型，则进行类型转换
        if config_cls is not None:
            return cast(config_cls, config)  # type: ignore
        return config

    def get_plugin_path(self) -> Path:
        return self._plugin_path

    def mount_sandbox_method(self, method_type: SandboxMethodType, name: str, description: str = ""):
        """挂载沙盒方法

        用于挂载沙盒方法，提供给 Nekro 插件使用。

        Args:
            method_type (SandboxMethodType): 方法类型
            name (str): 方法名称
            description (str): 方法描述
        """

        def decorator(func):
            func._method_type = method_type  # noqa: SLF001
            self.sandbox_methods.append(SandboxMethod(method_type, name, description, func))
            logger.debug(f"从插件 {self.name} 挂载沙盒方法 {name} 成功")
            return func

        return decorator

    def mount_prompt_inject_method(self, name: str, description: str = ""):
        """挂载提示注入方法

        用于挂载提示注入方法，在对话开始前执行，返回内容会注入到对话提示中。

        Args:
            name (str): 挂载的提示注入方法的名称
            description (str): 挂载的提示注入方法的描述
        """

        def decorator(func):
            self.prompt_inject_method = PromptInjectMethod(name, description, func)
            return func

        return decorator

    def mount_webhook_method(self, endpoint: str, name: str, description: str = ""):
        """挂载 Webhook 方法

        用于挂载 Webhook 方法，提供 Webhook 事件触发能力

        Args:
            endpoint (str): 挂载的 Webhook 方法的端点
            name (str): 挂载的 Webhook 方法的名称
            description (str): 挂载的 Webhook 方法的描述
        """

        def decorator(func):
            self.webhook_methods[endpoint] = WebhookMethod(name, description, func)
            return func

        return decorator

    def mount_cleanup_method(self):
        def decorator(func):
            self.cleanup_method = func
            return func

        return decorator

    @property
    def is_enabled(self):
        return self._is_enabled

    def enable(self):
        self._is_enabled = True

    def disable(self):
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

    async def render_sandbox_methods_prompt(self) -> str:
        """渲染沙盒方法提示词

        Returns:
            str: 沙盒方法提示
        """
        prompts: List[str] = []

        for method in self.sandbox_methods:
            if not method.func.__doc__:
                logger.warning(f"方法 {method.func.__name__} 没有可用的文档注解。")
                continue
            if method.method_type in [SandboxMethodType.AGENT, SandboxMethodType.MULTIMODAL_AGENT]:
                prompts.append(f"* {method.func.__name__} - [AGENT METHOD - STOP AFTER CALL] {method.func.__doc__.strip()}")
            else:
                prompts.append(f"* {method.func.__name__} - {method.func.__doc__.strip()}")
        return "\n".join(prompts)

    @property
    def store(self) -> "PluginStore":
        return PluginStore(self)


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
