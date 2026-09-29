"""命令注册表 - 命名空间路由与冲突检测"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Optional

import regex
from nonebot import logger

from nekro_agent.services.command.base import (
    BaseCommand,
    CommandMetadata,
    PluginCommand,
    PluginCommandAdapter,
    compile_command_regex_patterns,
)
from nekro_agent.services.command.schemas import (
    CommandRequest,
    CommandResponse,
    CommandResponseStatus,
)

REGEX_MATCH_TIMEOUT_SECONDS = 0.05


@dataclass(frozen=True)
class CommandRegexMatch:
    """普通消息正则命中结果。"""

    command_name: str
    matched_args: dict[str, str]
    pattern: str


@dataclass(frozen=True)
class _RegexCommandEntry:
    full_name: str
    pattern: str
    compiled: regex.Pattern[str]


class CommandRegistry:
    def __init__(self):
        self._commands: dict[str, BaseCommand] = {}  # 完整名 -> 命令
        self._short_names: dict[str, list[str]] = {}  # 短名 -> [完整名列表]
        self._aliases: dict[str, str] = {}  # 别名完整名 -> 命令完整名
        self._normalized_short_names: dict[str, list[str]] = {}  # 规范化短名 -> [完整名列表]
        self._normalized_full_names: dict[str, list[str]] = {}  # 规范化完整名 -> [完整名列表]
        self._regex_entries: list[_RegexCommandEntry] = []

    @staticmethod
    def _is_hyphen_folding_enabled() -> bool:
        from nekro_agent.core.config import config

        return config.COMMAND_MATCH_ALLOW_HYPHEN_FOR_UNDERSCORE

    @staticmethod
    def _normalize_name(name: str) -> str:
        namespace, separator, command = name.partition(":")
        if not separator:
            return name.replace("-", "_")
        return f"{namespace}:{command.replace('-', '_')}"

    @staticmethod
    def _append_unique(index: dict[str, list[str]], key: str, target: str) -> None:
        bucket = index.setdefault(key, [])
        if target not in bucket:
            bucket.append(target)

    def _register_short_name(self, short_name: str, full_name: str) -> None:
        self._append_unique(self._short_names, short_name, full_name)
        self._append_unique(self._normalized_short_names, self._normalize_name(short_name), full_name)

    def _register_full_name(self, full_name: str) -> None:
        self._append_unique(self._normalized_full_names, self._normalize_name(full_name), full_name)

    def _resolve_normalized(self, name: str) -> Optional[BaseCommand]:
        if not self._is_hyphen_folding_enabled():
            return None

        normalized_name = self._normalize_name(name)
        full_candidates = self._normalized_full_names.get(normalized_name, [])
        if len(full_candidates) == 1:
            return self._commands[full_candidates[0]]

        short_candidates = self._normalized_short_names.get(normalized_name, [])
        if len(short_candidates) == 1:
            return self._commands[short_candidates[0]]

        return None

    def get_conflicting_candidates(self, name: str) -> list[str]:
        exact_candidates = self._short_names.get(name, [])
        if len(exact_candidates) > 1:
            return exact_candidates

        if not self._is_hyphen_folding_enabled():
            return []

        normalized_name = self._normalize_name(name)
        normalized_full_candidates = self._normalized_full_names.get(normalized_name, [])
        if len(normalized_full_candidates) > 1:
            return normalized_full_candidates

        normalized_short_candidates = self._normalized_short_names.get(normalized_name, [])
        if len(normalized_short_candidates) > 1:
            return normalized_short_candidates

        return []

    def _full_name(self, namespace: str, name: str) -> str:
        """生成完整命令名: namespace:name"""
        return f"{namespace}:{name}"

    def register(self, command: BaseCommand) -> None:
        """注册命令"""
        meta = command.metadata
        full = self._full_name(meta.namespace, meta.name)
        regex_entries = self._compile_regex_entries(command, full)

        if full in self._commands:
            logger.warning(f"命令 {full} 已注册，将被覆盖")
            self._commands[full] = command
            self._rebuild_short_names()
            logger.debug(f"已注册命令: {full} (别名: {meta.aliases}, 正则: {meta.regex_patterns})")
            return

        self._commands[full] = command
        self._register_full_name(full)

        # 短名索引
        self._register_short_name(meta.name, full)

        # 别名索引
        for alias in meta.aliases:
            alias_full = self._full_name(meta.namespace, alias)
            self._aliases[alias_full] = full
            self._register_full_name(alias_full)
            self._register_short_name(alias, full)

        self._regex_entries.extend(regex_entries)
        logger.debug(f"已注册命令: {full} (别名: {meta.aliases}, 正则: {meta.regex_patterns})")

    @staticmethod
    def _compile_regex_entries(command: BaseCommand, full_name: str) -> list[_RegexCommandEntry]:
        """编译并校验命令声明的普通消息正则。"""
        meta = command.metadata
        parameter_names, required_parameter_names = command.get_parameter_names()
        compiled_patterns = compile_command_regex_patterns(
            meta.regex_patterns,
            parameter_names,
            required_parameter_names,
            full_name,
        )
        return [
            _RegexCommandEntry(full_name=full_name, pattern=pattern, compiled=compiled)
            for pattern, compiled in zip(meta.regex_patterns, compiled_patterns, strict=True)
        ]

    def resolve(self, name: str) -> Optional[BaseCommand]:
        """解析命令名 -> 命令实例

        解析顺序:
        1. 精确匹配完整名 (namespace:cmd)
        2. 精确匹配别名完整名
        3. 短名无冲突匹配 (cmd -> 仅一个注册时直接命中)
        4. 短名别名无冲突匹配
        """
        # 1. 完整名直接查找
        if name in self._commands:
            return self._commands[name]

        # 2. 别名完整名
        if name in self._aliases:
            return self._commands.get(self._aliases[name])

        # 3. 短名查找 (无冲突时直接命中)
        candidates = self._short_names.get(name, [])
        if len(candidates) == 1:
            return self._commands[candidates[0]]

        return self._resolve_normalized(name)

    def list_all_commands(self) -> list[CommandMetadata]:
        """列出所有已注册命令（含插件命令，排除 internal）"""
        return sorted(
            [cmd.metadata for cmd in self._commands.values() if not cmd.metadata.internal],
            key=lambda m: (m.category, m.namespace, m.name),
        )

    def get_conflicting_short_names(self) -> dict[str, list[str]]:
        """获取存在冲突的短名（供诊断和帮助提示）"""
        return {short: fulls for short, fulls in self._short_names.items() if len(fulls) > 1}

    def match_regex(self, text: str, chat_key: Optional[str] = None) -> Optional[CommandRegexMatch]:
        """对普通消息执行全文正则匹配；冲突时不消费消息。"""
        from nekro_agent.services.command.manager import command_manager

        matches: dict[str, CommandRegexMatch] = {}
        plugin_enabled_cache: dict[str, bool] = {}

        for entry in self._regex_entries:
            if entry.full_name in matches:
                continue

            command = self._commands.get(entry.full_name)
            if command is None:
                continue

            meta = command.metadata
            if not command_manager.is_command_enabled_for_meta(
                meta,
                chat_key,
                plugin_enabled_cache=plugin_enabled_cache,
            ):
                continue

            try:
                matched = entry.compiled.fullmatch(text, timeout=REGEX_MATCH_TIMEOUT_SECONDS)
            except TimeoutError:
                logger.warning(f"命令正则匹配超时，已跳过: command={entry.full_name}, pattern={entry.pattern!r}")
                continue

            if matched is None:
                continue

            matches[entry.full_name] = CommandRegexMatch(
                command_name=entry.full_name,
                matched_args={name: value for name, value in matched.groupdict().items() if value is not None},
                pattern=entry.pattern,
            )

        if len(matches) > 1:
            candidates = ", ".join(sorted(matches))
            logger.warning(f"普通消息同时命中多个正则命令，已跳过执行: commands={candidates}")
            return None

        return next(iter(matches.values()), None)

    async def execute(self, request: CommandRequest) -> AsyncIterator[CommandResponse]:
        """执行命令 - 自动检查启用状态"""
        from nekro_agent.schemas.i18n import t
        from nekro_agent.services.command.manager import command_manager

        cmd = self.resolve(request.command_name)
        if not cmd:
            # 检查是否存在冲突
            candidates = self.get_conflicting_candidates(request.command_name)
            if len(candidates) > 1:
                hint = ", ".join(candidates)
                yield CommandResponse(
                    status=CommandResponseStatus.NOT_FOUND,
                    message=t(
                        zh_CN=f"命令 '{request.command_name}' 存在冲突，请使用完整名: {hint}",
                        en_US=f"Command '{request.command_name}' is ambiguous, use full name: {hint}",
                    ),
                )
                return
            yield CommandResponse(
                status=CommandResponseStatus.NOT_FOUND,
                message=t(
                    zh_CN=f"命令不存在: {request.command_name}",
                    en_US=f"Command not found: {request.command_name}",
                ),
            )
            return

        if not command_manager.is_command_enabled_for_meta(cmd.metadata, request.context.chat_key):
            yield CommandResponse(
                status=CommandResponseStatus.DISABLED,
                message=t(
                    zh_CN=f"命令已禁用: {request.command_name}",
                    en_US=f"Command is disabled: {request.command_name}",
                ),
            )
            return

        async for response in cmd.handle(request):
            yield response

    def register_plugin_command(self, plugin_cmd: PluginCommand) -> None:
        """注册插件命令（由插件加载流程调用）"""
        adapter = PluginCommandAdapter(plugin_cmd)
        self.register(adapter)

    def unregister_plugin_commands(self, source: str) -> None:
        """卸载指定插件的所有命令（插件卸载时调用）"""
        to_remove = [full_name for full_name, cmd in self._commands.items() if cmd.metadata.source == source]
        for full_name in to_remove:
            del self._commands[full_name]
            logger.debug(f"已卸载命令: {full_name}")
        # 重建短名索引
        self._rebuild_short_names()

    def _rebuild_short_names(self) -> None:
        """重建短名索引"""
        self._short_names.clear()
        self._aliases.clear()
        self._normalized_short_names.clear()
        self._normalized_full_names.clear()
        self._regex_entries.clear()
        for full_name, cmd in self._commands.items():
            meta = cmd.metadata
            self._register_full_name(full_name)
            self._register_short_name(meta.name, full_name)
            for alias in meta.aliases:
                alias_full = self._full_name(meta.namespace, alias)
                self._aliases[alias_full] = full_name
                self._register_full_name(alias_full)
                self._register_short_name(alias, full_name)
            self._regex_entries.extend(self._compile_regex_entries(cmd, full_name))


# 全局单例
command_registry = CommandRegistry()
