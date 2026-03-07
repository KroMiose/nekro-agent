"""命令注册表 - 命名空间路由与冲突检测"""

from collections.abc import AsyncIterator
from typing import Optional

from nonebot import logger

from nekro_agent.services.command.base import BaseCommand, CommandMetadata, PluginCommand, PluginCommandAdapter
from nekro_agent.services.command.schemas import (
    CommandRequest,
    CommandResponse,
    CommandResponseStatus,
)


class CommandRegistry:
    def __init__(self):
        self._commands: dict[str, BaseCommand] = {}  # 完整名 -> 命令
        self._short_names: dict[str, list[str]] = {}  # 短名 -> [完整名列表]
        self._aliases: dict[str, str] = {}  # 别名完整名 -> 命令完整名

    def _full_name(self, namespace: str, name: str) -> str:
        """生成完整命令名: namespace:name"""
        return f"{namespace}:{name}"

    def register(self, command: BaseCommand) -> None:
        """注册命令"""
        meta = command.metadata
        full = self._full_name(meta.namespace, meta.name)

        if full in self._commands:
            logger.warning(f"命令 {full} 已注册，将被覆盖")

        self._commands[full] = command

        # 短名索引
        self._short_names.setdefault(meta.name, []).append(full)

        # 别名索引
        for alias in meta.aliases:
            alias_full = self._full_name(meta.namespace, alias)
            self._aliases[alias_full] = full
            self._short_names.setdefault(alias, []).append(full)

        logger.debug(f"已注册命令: {full} (别名: {meta.aliases})")

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

        return None

    def list_all_commands(self) -> list[CommandMetadata]:
        """列出所有已注册命令（含插件命令，排除 internal）"""
        return sorted(
            [cmd.metadata for cmd in self._commands.values() if not cmd.metadata.internal],
            key=lambda m: (m.category, m.namespace, m.name),
        )

    def get_conflicting_short_names(self) -> dict[str, list[str]]:
        """获取存在冲突的短名（供诊断和帮助提示）"""
        return {short: fulls for short, fulls in self._short_names.items() if len(fulls) > 1}

    async def execute(self, request: CommandRequest) -> AsyncIterator[CommandResponse]:
        """执行命令 - 自动检查启用状态"""
        from nekro_agent.services.command.manager import command_manager

        cmd = self.resolve(request.command_name)
        if not cmd:
            # 检查是否存在冲突
            candidates = self._short_names.get(request.command_name, [])
            if len(candidates) > 1:
                hint = ", ".join(candidates)
                yield CommandResponse(
                    status=CommandResponseStatus.NOT_FOUND,
                    message=f"命令 '{request.command_name}' 存在冲突，请使用完整名: {hint}",
                )
                return
            yield CommandResponse(
                status=CommandResponseStatus.NOT_FOUND,
                message=f"命令不存在: {request.command_name}",
            )
            return

        if not command_manager.is_command_enabled(cmd.metadata.name, request.context.chat_key):
            yield CommandResponse(
                status=CommandResponseStatus.DISABLED,
                message=f"命令已禁用: {request.command_name}",
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
        for full_name, cmd in self._commands.items():
            meta = cmd.metadata
            self._short_names.setdefault(meta.name, []).append(full_name)
            for alias in meta.aliases:
                alias_full = self._full_name(meta.namespace, alias)
                self._aliases[alias_full] = full_name
                self._short_names.setdefault(alias, []).append(full_name)


# 全局单例
command_registry = CommandRegistry()
