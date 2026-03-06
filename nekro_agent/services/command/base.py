"""命令基类与元数据定义

包含命令权限枚举、命令元数据模型、命令基类及插件命令适配器。
"""

import inspect
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any, Callable, Optional, Union

from pydantic import BaseModel

from nekro_agent.services.command.schemas import (
    CommandExecutionContext,
    CommandRequest,
    CommandResponse,
    CommandResponseStatus,
)


class CommandPermission(str, Enum):
    PUBLIC = "public"
    USER = "user"
    ADVANCED = "advanced"
    SUPER_USER = "super_user"


class CommandMetadata(BaseModel):
    name: str
    namespace: str = "built_in"  # 命名空间（内置命令为 "built_in"，插件命令自动填充为插件 key）
    aliases: list[str] = []
    description: str
    usage: str = ""
    permission: CommandPermission = CommandPermission.PUBLIC
    category: str = "general"
    source: str = "built_in"  # "built_in" | 插件 key
    tags: list[str] = []  # 标签 (便于 Agent 检索)
    params_schema: Optional[dict] = None  # 自动生成的 JSON Schema (用于 Agent Tool-Use)
    internal: bool = False  # 内部命令 (不在帮助列表和补全中显示, 如 wait 的 callback_cmd)


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
        perm = self.metadata.permission
        if perm == CommandPermission.PUBLIC:
            return True, None
        if perm == CommandPermission.SUPER_USER:
            return (True, None) if context.is_super_user else (False, "此命令仅限超级用户使用")
        if perm == CommandPermission.ADVANCED:
            ok = context.is_advanced_user or context.is_super_user
            return (True, None) if ok else (False, "此命令仅限高级用户使用")
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
            yield CommandResponse(status=CommandResponseStatus.UNAUTHORIZED, message=err or "权限不足")
            return

        try:
            # 解析参数
            parsed_kwargs = self._parse_args(request.raw_args)
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
            yield CommandResponse(status=CommandResponseStatus.INVALID_ARGS, message=f"参数错误: {e}")
        except Exception as e:
            yield CommandResponse(status=CommandResponseStatus.ERROR, message=f"命令执行出错: {e}")

    def _parse_args(self, raw_args: str) -> dict[str, Any]:
        """根据 execute 方法的类型注解解析参数"""
        from nekro_agent.services.command.parser import ArgumentParser

        return ArgumentParser.parse(self.execute, raw_args)


class PluginCommand(BaseModel):
    """插件命令数据（由 NekroPlugin.mount_command 收集）"""

    name: str
    description: str
    aliases: list[str] = []
    permission: CommandPermission = CommandPermission.PUBLIC
    usage: str = ""
    category: str = "plugin"
    source: str = ""
    namespace: str = ""
    tags: list[str] = []
    internal: bool = False
    execute_func: Callable

    model_config = {"arbitrary_types_allowed": True}


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
            description=self._cmd.description,
            usage=self._cmd.usage,
            permission=self._cmd.permission,
            category=self._cmd.category,
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

    def _parse_args(self, raw_args: str) -> dict[str, Any]:
        """根据原始插件函数的类型注解解析参数"""
        from nekro_agent.services.command.parser import ArgumentParser

        return ArgumentParser.parse(self._cmd.execute_func, raw_args)
