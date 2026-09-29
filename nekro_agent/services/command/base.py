"""命令基类与元数据定义

包含命令权限枚举、命令元数据模型、命令基类及插件命令适配器。
"""

import inspect
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any, Callable, Optional, Union

import regex
from pydantic import BaseModel, model_validator

from nekro_agent.schemas.i18n import I18nDict, SupportedLang, get_text, t
from nekro_agent.services.command.schemas import (
    CommandExecutionContext,
    CommandRequest,
    CommandResponse,
    CommandResponseStatus,
)

BUILT_IN_SOURCE = "built_in"
"""内置命令的 source / namespace 标识符，用于与插件命令来源区分。"""


def compile_command_regex_patterns(
    patterns: list[str],
    parameter_names: set[str],
    required_parameter_names: set[str],
    command_name: str,
) -> list[regex.Pattern[str]]:
    """编译命令正则，并校验命名组与命令参数是否一致。"""
    compiled_patterns: list[regex.Pattern[str]] = []
    for pattern in patterns:
        try:
            compiled = regex.compile(pattern)
        except regex.error as e:
            raise ValueError(f"命令 {command_name} 的正则表达式无效: {pattern!r}: {e}") from e

        capture_names = set(compiled.groupindex)
        unknown_names = sorted(capture_names - parameter_names)
        if unknown_names:
            raise ValueError(
                f"命令 {command_name} 的正则表达式 {pattern!r} 包含未知命名组: {', '.join(unknown_names)}"
            )

        missing_names = sorted(required_parameter_names - capture_names)
        if missing_names:
            raise ValueError(
                f"命令 {command_name} 的正则表达式 {pattern!r} 未提供必填参数: {', '.join(missing_names)}"
            )

        compiled_patterns.append(compiled)

    return compiled_patterns


class CommandPermission(str, Enum):
    PUBLIC = "public"
    USER = "user"
    ADVANCED = "advanced"
    SUPER_USER = "super_user"


class CommandMetadata(BaseModel):
    name: str
    namespace: str = BUILT_IN_SOURCE  # 命名空间（内置命令为 BUILT_IN_SOURCE，插件命令自动填充为插件 key）
    aliases: list[str] = []
    regex_patterns: list[str] = []  # 无前缀普通消息的全文匹配规则
    description: str
    i18n_description: Optional[I18nDict] = None  # 国际化描述
    usage: str = ""
    i18n_usage: Optional[I18nDict] = None  # 国际化用法说明
    permission: CommandPermission = CommandPermission.PUBLIC
    category: str = "general"
    i18n_category: Optional[I18nDict] = None  # 国际化分类
    source: str = BUILT_IN_SOURCE  # BUILT_IN_SOURCE | 插件 key
    tags: list[str] = []  # 标签 (便于 Agent 检索)
    params_schema: Optional[dict] = None  # 自动生成的 JSON Schema (用于 Agent Tool-Use)
    internal: bool = False  # 内部命令 (不在帮助列表和补全中显示, 如 wait 的 callback_cmd)
    requires_advanced_command: bool = False  # 是否需要显式开启高风险管理命令

    def get_description(self, lang: SupportedLang = SupportedLang.ZH_CN) -> str:
        return get_text(self.i18n_description, self.description, lang)

    def get_category(self, lang: SupportedLang = SupportedLang.ZH_CN) -> str:
        return get_text(self.i18n_category, self.category, lang)

    def get_usage(self, lang: SupportedLang = SupportedLang.ZH_CN) -> str:
        return get_text(self.i18n_usage, self.usage, lang)


class BaseCommand(ABC):
    """命令基类

    子类实现方式一 (简单命令，直接返回):
        async def execute(self, ctx, **kwargs) -> CommandResponse

    子类实现方式二 (流式命令，yield 控制流):
        async def execute(self, ctx, **kwargs) -> AsyncIterator[CommandResponse]
    """

    @property
    @abstractmethod
    def metadata(self) -> CommandMetadata: ...

    def _auto_params_schema(self) -> Optional[dict]:
        """从 execute 方法签名自动生成 params_schema"""
        from nekro_agent.services.command.parser import ArgumentParser

        return ArgumentParser.extract_params_schema(self.execute)

    @abstractmethod
    async def execute(
        self,
        context: CommandExecutionContext,
        **kwargs: Any,
    ) -> Union[CommandResponse, AsyncIterator[CommandResponse]]: ...

    async def check_permission(
        self,
        context: CommandExecutionContext,
    ) -> tuple[bool, Optional[str]]:
        """默认权限检查，子类可覆盖"""
        from nekro_agent.services.command.manager import command_manager

        meta = self.metadata
        if meta.requires_advanced_command:
            from nekro_agent.core.config import config

            if not config.ENABLE_ADVANCED_COMMAND:
                return False, t(
                    zh_CN="高级管理命令未启用，请先在系统配置中开启",
                    en_US="Advanced admin commands are disabled; enable them in system settings first",
                )

        perm = command_manager.get_command_permission(meta.name, meta.permission, context.chat_key)
        if perm == CommandPermission.PUBLIC:
            return True, None
        if perm == CommandPermission.SUPER_USER:
            return (
                (True, None)
                if context.is_super_user
                else (False, t(zh_CN="此命令仅限超级用户使用", en_US="This command is for super users only"))
            )
        if perm == CommandPermission.ADVANCED:
            ok = context.is_advanced_user or context.is_super_user
            return (
                (True, None)
                if ok
                else (False, t(zh_CN="此命令仅限高级用户使用", en_US="This command is for advanced users only"))
            )
        if perm == CommandPermission.USER:
            return True, None  # 已登录用户均可
        return True, None

    async def handle(
        self,
        request: CommandRequest,
    ) -> AsyncIterator[CommandResponse]:
        """完整处理流程: 权限检查 -> 参数解析 -> 执行 -> 消费输出流"""
        has_perm, err = await self.check_permission(request.context)
        if not has_perm:
            yield CommandResponse(
                status=CommandResponseStatus.UNAUTHORIZED,
                message=err or t(zh_CN="权限不足", en_US="Permission denied"),
            )
            return

        try:
            # 解析参数
            parsed_kwargs = self._parse_args(
                request.raw_args,
                request.context.lang,
                matched_args=request.matched_args,
            )
            result_or_gen = self.execute(request.context, **parsed_kwargs)

            # 子类 execute 可能是 async generator (用 yield) 或普通 coroutine (用 return)
            if inspect.isasyncgen(result_or_gen):
                async for response in result_or_gen:  # type: ignore[union-attr]
                    yield response
            else:
                result = await result_or_gen
                if isinstance(result, CommandResponse):
                    yield result
                else:
                    async for response in result:
                        yield response

        except ValueError as e:
            yield CommandResponse(
                status=CommandResponseStatus.INVALID_ARGS,
                message=t(zh_CN="参数错误: ", en_US="Invalid argument: ") + str(e),
            )
        except Exception as e:
            yield CommandResponse(
                status=CommandResponseStatus.ERROR,
                message=t(zh_CN="命令执行出错: ", en_US="Command execution error: ") + str(e),
            )

    def _parse_args(
        self,
        raw_args: str,
        lang: SupportedLang = SupportedLang.ZH_CN,
        *,
        matched_args: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """根据 execute 方法的类型注解解析参数"""
        from nekro_agent.services.command.parser import ArgumentParser

        return ArgumentParser.parse(self.execute, raw_args, lang=lang, matched_args=matched_args)

    def get_parameter_names(self) -> tuple[set[str], set[str]]:
        """返回命令处理函数的全部参数名与必填参数名。"""
        from nekro_agent.services.command.parser import ArgumentParser

        return ArgumentParser.get_parameter_names(self.execute)


class PluginCommand(BaseModel):
    """插件命令数据（由 NekroPlugin.mount_command 收集）"""

    name: str
    description: str
    i18n_description: Optional[I18nDict] = None
    aliases: list[str] = []
    regex_patterns: list[str] = []
    permission: CommandPermission = CommandPermission.PUBLIC
    usage: str = ""
    i18n_usage: Optional[I18nDict] = None
    category: str = "plugin"
    i18n_category: Optional[I18nDict] = None
    source: str = ""
    namespace: str = ""
    tags: list[str] = []
    internal: bool = False
    execute_func: Callable

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def validate_regex_patterns(self) -> "PluginCommand":
        """在插件导入阶段提前拒绝无效正则命令。"""
        from nekro_agent.services.command.parser import ArgumentParser

        parameter_names, required_parameter_names = ArgumentParser.get_parameter_names(self.execute_func)
        compile_command_regex_patterns(
            self.regex_patterns,
            parameter_names,
            required_parameter_names,
            f"{self.namespace}:{self.name}",
        )
        return self


class PluginCommandAdapter(BaseCommand):
    """将 PluginCommand 适配为 BaseCommand 接口"""

    def __init__(self, plugin_cmd: PluginCommand):
        self._cmd = plugin_cmd
        self._params_schema = self._extract_schema()

    def _extract_schema(self) -> Optional[dict]:
        from nekro_agent.services.command.parser import ArgumentParser

        try:
            return ArgumentParser.extract_params_schema(self._cmd.execute_func)
        except Exception:
            return None

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name=self._cmd.name,
            namespace=self._cmd.namespace,
            aliases=self._cmd.aliases,
            regex_patterns=self._cmd.regex_patterns,
            description=self._cmd.description,
            i18n_description=self._cmd.i18n_description,
            usage=self._cmd.usage,
            i18n_usage=self._cmd.i18n_usage,
            permission=self._cmd.permission,
            category=self._cmd.category,
            i18n_category=self._cmd.i18n_category,
            source=self._cmd.source,
            tags=self._cmd.tags,
            internal=self._cmd.internal,
            params_schema=self._params_schema,
        )

    async def execute(self, context: CommandExecutionContext, **kwargs: Any):
        result = self._cmd.execute_func(context, **kwargs)
        if inspect.isasyncgen(result):
            return result
        return await result

    def _parse_args(
        self,
        raw_args: str,
        lang: SupportedLang = SupportedLang.ZH_CN,
        *,
        matched_args: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """根据原始插件函数的类型注解解析参数"""
        from nekro_agent.services.command.parser import ArgumentParser

        return ArgumentParser.parse(
            self._cmd.execute_func,
            raw_args,
            lang=lang,
            matched_args=matched_args,
        )

    def get_parameter_names(self) -> tuple[set[str], set[str]]:
        """返回插件命令函数的全部参数名与必填参数名。"""
        from nekro_agent.services.command.parser import ArgumentParser

        return ArgumentParser.get_parameter_names(self._cmd.execute_func)
