"""旧版 OneBot 命令系统兼容层。"""

import inspect
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, Any, Optional

from nekro_agent.api.core import config
from nekro_agent.api.plugin import (
    Arg,
    CmdCtl,
    CommandExecutionContext,
    CommandPermission,
    CommandResponse,
    NekroPlugin,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.command.schemas import CommandResponseStatus

logger = get_sub_logger("adapter.onebot_v11.legacy_command")


class LegacyCommandFinished(Exception):
    """旧命令提前终止载体。"""

    def __init__(self, response: Optional[CommandResponse] = None):
        super().__init__(response.message if response else "")
        self.response = response


class LegacyBotUnavailable:
    """缺少 OneBot Bot 时的兜底对象。"""

    async def call_api(self, api: str, **kwargs: Any) -> Any:
        raise RuntimeError(f"OneBot V11 Bot 不可用，无法调用 API: {api}({kwargs})")

    def __getattr__(self, name: str) -> Any:
        raise RuntimeError(f"OneBot V11 Bot 不可用，无法访问属性: {name}")


class LegacyMessage:
    """旧命令参数对象的最小兼容实现。"""

    def __init__(self, text: str = ""):
        self._text = text

    def extract_plain_text(self) -> str:
        return self._text

    def __str__(self) -> str:
        return self._text


@dataclass(slots=True)
class LegacySender:
    user_id: str
    nickname: str
    card: str
    role: str


class LegacyMessageEvent:
    """旧版 MessageEvent 的最小兼容实现。"""

    def __init__(self, context: CommandExecutionContext, raw_args: str):
        self._context = context
        self._chat_key = _normalize_chat_key(context)
        self._chat_type = _resolve_chat_type(self._chat_key)
        self.user_id = context.user_id
        self.message = LegacyMessage(raw_args)
        self.original_message = LegacyMessage(raw_args)
        self.message_type = _chat_type_to_message_type(self._chat_type)
        self.group_id = _extract_group_id(self._chat_key)
        self.sender = LegacySender(
            user_id=context.user_id,
            nickname=context.username,
            card=context.username,
            role=_infer_sender_role(context),
        )

    @property
    def chat_key(self) -> str:
        return self._chat_key

    @property
    def chat_type(self) -> ChatType:
        return self._chat_type

    @property
    def context(self) -> CommandExecutionContext:
        return self._context

    def get_user_id(self) -> str:
        return str(self.user_id)

    def get_plaintext(self) -> str:
        return self.message.extract_plain_text()


class LegacyMatcher:
    """旧版 Matcher 的最小兼容实现。"""

    def __init__(self):
        self._pending_responses: list[CommandResponse] = []

    async def send(self, message: str = "", data: Optional[dict[str, Any]] = None) -> None:
        self._pending_responses.append(CmdCtl.message(message, data))

    async def finish(
        self,
        message: str = "",
        *,
        data: Optional[dict[str, Any]] = None,
        status: CommandResponseStatus = CommandResponseStatus.SUCCESS,
    ) -> None:
        response: Optional[CommandResponse] = None
        if message or data is not None or status != CommandResponseStatus.SUCCESS:
            if status == CommandResponseStatus.SUCCESS:
                response = CmdCtl.success(message, data)
            elif status == CommandResponseStatus.ERROR:
                response = CmdCtl.failed(message, data)
            else:
                response = CommandResponse(status=status, message=message, data=data)
        raise LegacyCommandFinished(response)

    def drain(self) -> list[CommandResponse]:
        responses = list(self._pending_responses)
        self._pending_responses.clear()
        return responses


class LegacyCommandRegistration:
    """兼容 nonebot `on_command(...).handle()` 的注册器。"""

    def __init__(
        self,
        name: str,
        aliases: Optional[set[str] | list[str] | tuple[str, ...]] = None,
    ):
        self._name = name
        self._aliases = _normalize_aliases(aliases)

    def handle(self, *args: Any, **kwargs: Any):
        del args, kwargs

        def decorator(func: Any) -> Any:
            plugin = _find_plugin(func.__globals__)
            if plugin is None:
                raise RuntimeError(
                    f"旧命令 `{self._name}` 注册失败：未在模块中找到 `plugin` 实例，无法挂接到当前命令系统。"
                )

            description = _extract_description(func, self._name)

            @plugin.mount_command(
                name=self._name,
                description=description,
                aliases=self._aliases,
                permission=CommandPermission.PUBLIC,
                usage=self._name,
            )
            async def _legacy_command_wrapper(
                context: CommandExecutionContext,
                raw_text: Annotated[str, Arg("命令原始参数", positional=True, greedy=True)] = "",
            ) -> AsyncIterator[CommandResponse]:
                matcher = LegacyMatcher()
                event = LegacyMessageEvent(context, raw_text)
                bot = _resolve_legacy_bot()
                arg = LegacyMessage(raw_text)

                try:
                    result = await _invoke_legacy_handler(
                        func,
                        matcher=matcher,
                        event=event,
                        bot=bot,
                        arg=arg,
                    )
                except LegacyCommandFinished as exc:
                    for response in matcher.drain():
                        yield response
                    if exc.response is not None:
                        yield exc.response
                    return

                for response in matcher.drain():
                    yield response

                async for response in _coerce_handler_result(result):
                    yield response

            return func

        return decorator


def on_command(
    name: str,
    aliases: Optional[set[str] | list[str] | tuple[str, ...]] = None,
    *args: Any,
    **kwargs: Any,
) -> LegacyCommandRegistration:
    """兼容旧版 `on_command`，底层注册到当前插件命令系统。"""
    del args, kwargs
    return LegacyCommandRegistration(name=name, aliases=aliases)


async def finish_with(matcher: LegacyMatcher, message: str) -> None:
    """旧版 finish_with 兼容入口。"""
    await matcher.finish(message=message)


async def command_guard(
    event: LegacyMessageEvent,
    bot: Any,
    arg: LegacyMessage,
    matcher: LegacyMatcher,
    trigger_on_off: bool = False,
    require_advanced_command: bool = False,
) -> tuple[str, str, str, ChatType]:
    """旧版命令前置校验。"""
    del bot

    chat_key = event.chat_key
    chat_type = event.chat_type
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)

    if not db_chat_channel.is_active and not trigger_on_off:
        await matcher.finish()

    username = event.context.username

    if not _is_legacy_super_user(event.context):
        logger.warning(f"用户 {username} 不在允许的管理用户中")
        if getattr(config, "ENABLE_COMMAND_UNAUTHORIZED_OUTPUT", False):
            await matcher.finish(
                message=f"用户 [{event.get_user_id()}]{username} 不在允许的管理用户中",
                status=CommandResponseStatus.UNAUTHORIZED,
            )
        await matcher.finish()

    if require_advanced_command:
        try:
            config.require_advanced_command()
        except PermissionError:
            await matcher.finish(
                message="当前未启用高级管理命令，无法执行此命令",
                status=CommandResponseStatus.UNAUTHORIZED,
            )

    cmd_content = arg.extract_plain_text().strip()
    return username, cmd_content, chat_key, chat_type


async def reset_command_guard(
    event: LegacyMessageEvent,
    bot: Any,
    arg: LegacyMessage,
    matcher: LegacyMatcher,
) -> tuple[str, str, str, ChatType]:
    """旧版 reset 命令鉴权。"""

    chat_key = event.chat_key
    chat_type = event.chat_type
    username = event.context.username
    cmd_content = arg.extract_plain_text().strip()

    if _is_legacy_super_user(event.context):
        return username, cmd_content, chat_key, chat_type

    if cmd_content and chat_key != cmd_content:
        logger.warning(f"用户 {username} 尝试越权操作其他聊天")
        if getattr(config, "ENABLE_COMMAND_UNAUTHORIZED_OUTPUT", False):
            await matcher.finish(
                message="您只能操作当前聊天",
                status=CommandResponseStatus.UNAUTHORIZED,
            )
        await matcher.finish()

    if chat_type == ChatType.PRIVATE:
        return username, cmd_content, chat_key, chat_type

    if chat_type == ChatType.GROUP and await _is_group_admin_or_owner(event, bot):
        return username, cmd_content, chat_key, chat_type

    logger.warning(f"用户 {username} 不在允许的管理用户中")
    if getattr(config, "ENABLE_COMMAND_UNAUTHORIZED_OUTPUT", False):
        await matcher.finish(
            message=f"用户 [{event.get_user_id()}]{username} 不在允许的管理用户中",
            status=CommandResponseStatus.UNAUTHORIZED,
        )
    await matcher.finish()
    raise RuntimeError("reset_command_guard 无法继续执行")


async def _is_group_admin_or_owner(event: LegacyMessageEvent, bot: Any) -> bool:
    if event.sender.role in {"admin", "owner"}:
        return True

    if event.group_id is None or isinstance(bot, LegacyBotUnavailable):
        return False

    try:
        member_info = await bot.get_group_member_info(
            group_id=event.group_id,
            user_id=int(event.get_user_id()),
            no_cache=False,
        )
    except Exception as exc:
        logger.debug(f"查询群成员角色失败，回退为普通成员: {exc}")
        return False

    return str(member_info.get("role", "member")) in {"admin", "owner"}


async def _invoke_legacy_handler(
    func: Any,
    *,
    matcher: LegacyMatcher,
    event: LegacyMessageEvent,
    bot: Any,
    arg: LegacyMessage,
) -> Any:
    mapping = {
        "matcher": matcher,
        "event": event,
        "bot": bot,
        "arg": arg,
    }
    signature = inspect.signature(func)
    kwargs: dict[str, Any] = {}

    for name, parameter in signature.parameters.items():
        if name in mapping:
            kwargs[name] = mapping[name]
            continue

        if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        if parameter.default is inspect.Parameter.empty:
            raise TypeError(f"旧命令处理函数包含未支持的必填参数: {name}")

    call_result = func(**kwargs)
    if inspect.isasyncgen(call_result):
        return call_result
    if inspect.isawaitable(call_result):
        return await call_result
    return call_result


async def _coerce_handler_result(result: Any) -> AsyncIterator[CommandResponse]:
    if result is None:
        return

    if inspect.isasyncgen(result):
        async for item in result:
            async for response in _coerce_handler_result(item):
                yield response
        return

    if isinstance(result, CommandResponse):
        yield result
        return

    if isinstance(result, str):
        if result:
            yield CmdCtl.success(result)
        return

    if isinstance(result, (list, tuple)):
        for item in result:
            async for response in _coerce_handler_result(item):
                yield response
        return

    yield CmdCtl.success(str(result))


def _find_plugin(globals_dict: dict[str, Any]) -> Optional[NekroPlugin]:
    plugin = globals_dict.get("plugin")
    if isinstance(plugin, NekroPlugin):
        return plugin

    for value in globals_dict.values():
        if isinstance(value, NekroPlugin):
            return value
    return None


def _extract_description(func: Any, command_name: str) -> str:
    doc = inspect.getdoc(func)
    if doc:
        first_line = doc.strip().splitlines()[0].strip()
        if first_line:
            return first_line
    return f"兼容旧命令 {command_name}"


def _normalize_aliases(aliases: Optional[set[str] | list[str] | tuple[str, ...]]) -> list[str]:
    if not aliases:
        return []
    if isinstance(aliases, set):
        return sorted(aliases)
    return list(aliases)


def _normalize_chat_key(context: CommandExecutionContext) -> str:
    if "-" in context.chat_key:
        return context.chat_key
    return f"{context.adapter_key}-{context.chat_key}"


def _resolve_chat_type(chat_key: str) -> ChatType:
    channel_part = chat_key.split("-", 1)[1] if "-" in chat_key else chat_key
    if channel_part.startswith("group_"):
        return ChatType.GROUP
    if channel_part.startswith("private_"):
        return ChatType.PRIVATE
    return ChatType.UNKNOWN


def _extract_group_id(chat_key: str) -> Optional[int]:
    channel_part = chat_key.split("-", 1)[1] if "-" in chat_key else chat_key
    if not channel_part.startswith("group_"):
        return None
    group_id = channel_part.split("_", 1)[1]
    return int(group_id) if group_id.isdigit() else None


def _chat_type_to_message_type(chat_type: ChatType) -> str:
    if chat_type == ChatType.GROUP:
        return "group"
    if chat_type == ChatType.PRIVATE:
        return "private"
    return "unknown"


def _infer_sender_role(context: CommandExecutionContext) -> str:
    if context.is_super_user:
        return "owner"
    if context.is_advanced_user:
        return "admin"
    return "member"


def _is_legacy_super_user(context: CommandExecutionContext) -> bool:
    configured_super_users = {str(user_id) for user_id in getattr(config, "SUPER_USERS", [])}
    return context.is_super_user or str(context.user_id) in configured_super_users


def _resolve_legacy_bot() -> Any:
    try:
        from nekro_agent.adapters.onebot_v11.core.bot import get_bot

        return get_bot()
    except Exception as exc:
        logger.debug(f"获取 OneBot V11 Bot 失败，使用兼容占位对象: {exc}")
        return LegacyBotUnavailable()


__all__ = [
    "LegacyCommandFinished",
    "LegacyMatcher",
    "LegacyMessage",
    "LegacyMessageEvent",
    "command_guard",
    "finish_with",
    "on_command",
    "reset_command_guard",
]
