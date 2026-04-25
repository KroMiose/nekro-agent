"""命令状态管理 - 基于 JSON 文件存储"""

import json
from pathlib import Path
from typing import Optional

from nonebot import logger

from nekro_agent.core.os_env import (
    COMMAND_CHANNEL_PERMISSION_DIR,
    COMMAND_CHANNEL_STATE_DIR,
    COMMAND_STATE_DIR,
    COMMAND_SYSTEM_PERMISSION_FILE,
    COMMAND_SYSTEM_STATE_FILE,
)
from nekro_agent.schemas.errors import ValidationError
from nekro_agent.services.command.base import BUILT_IN_SOURCE, CommandMetadata, CommandPermission


class CommandManager:
    """命令状态管理 - 基于 JSON 文件存储

    状态优先级: 频道级 > 系统级 > 默认启用
    """

    def __init__(self):
        Path(COMMAND_STATE_DIR).mkdir(parents=True, exist_ok=True)
        Path(COMMAND_CHANNEL_STATE_DIR).mkdir(parents=True, exist_ok=True)
        Path(COMMAND_CHANNEL_PERMISSION_DIR).mkdir(parents=True, exist_ok=True)
        self._system_cache: Optional[dict[str, bool]] = None
        self._channel_cache: dict[str, dict[str, bool]] = {}
        self._system_permission_cache: Optional[dict[str, CommandPermission]] = None
        self._channel_permission_cache: dict[str, dict[str, CommandPermission]] = {}

    def _load_system_state(self) -> dict[str, bool]:
        """加载系统级状态（带缓存）"""
        if self._system_cache is None:
            system_state_file = Path(COMMAND_SYSTEM_STATE_FILE)
            if system_state_file.exists():
                try:
                    self._system_cache = json.loads(system_state_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"加载系统级命令状态失败: {e}")
                    self._system_cache = {}
            else:
                self._system_cache = {}
        assert self._system_cache is not None
        return self._system_cache

    def _load_channel_state(self, chat_key: str) -> dict[str, bool]:
        """加载频道级状态（带缓存）"""
        if chat_key not in self._channel_cache:
            path = Path(COMMAND_CHANNEL_STATE_DIR) / f"{chat_key}.json"
            if path.exists():
                try:
                    self._channel_cache[chat_key] = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"加载频道 {chat_key} 命令状态失败: {e}")
                    self._channel_cache[chat_key] = {}
            else:
                self._channel_cache[chat_key] = {}
        return self._channel_cache[chat_key]

    @staticmethod
    def _normalize_permission_state(raw_state: object) -> dict[str, CommandPermission]:
        if not isinstance(raw_state, dict):
            return {}

        normalized: dict[str, CommandPermission] = {}
        for command_name, permission in raw_state.items():
            if not isinstance(command_name, str) or not isinstance(permission, str):
                continue
            try:
                normalized[command_name] = CommandPermission(permission)
            except ValueError:
                logger.warning(f"检测到无效命令权限配置，已忽略: {command_name}={permission}")
        return normalized

    def _load_system_permission_state(self) -> dict[str, CommandPermission]:
        """加载系统级权限覆盖（带缓存）。

        返回内部共享缓存，调用方仅应在 setter 流程中原地修改并立即持久化。
        """
        if self._system_permission_cache is None:
            system_permission_file = Path(COMMAND_SYSTEM_PERMISSION_FILE)
            if system_permission_file.exists():
                try:
                    raw_state = json.loads(system_permission_file.read_text(encoding="utf-8"))
                    self._system_permission_cache = self._normalize_permission_state(raw_state)
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"加载系统级命令权限失败: {e}")
                    self._system_permission_cache = {}
            else:
                self._system_permission_cache = {}
        assert self._system_permission_cache is not None
        return self._system_permission_cache

    def _load_channel_permission_state(self, chat_key: str) -> dict[str, CommandPermission]:
        """加载频道级权限覆盖（带缓存）。

        返回内部共享缓存，调用方仅应在 setter 流程中原地修改并立即持久化。
        """
        if chat_key not in self._channel_permission_cache:
            path = Path(COMMAND_CHANNEL_PERMISSION_DIR) / f"{chat_key}.json"
            if path.exists():
                try:
                    raw_state = json.loads(path.read_text(encoding="utf-8"))
                    self._channel_permission_cache[chat_key] = self._normalize_permission_state(raw_state)
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"加载频道 {chat_key} 命令权限失败: {e}")
                    self._channel_permission_cache[chat_key] = {}
            else:
                self._channel_permission_cache[chat_key] = {}
        return self._channel_permission_cache[chat_key]

    def _save_system_state(self, state: dict[str, bool]) -> None:
        Path(COMMAND_SYSTEM_STATE_FILE).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        self._system_cache = state

    def _save_channel_state(self, chat_key: str, state: dict[str, bool]) -> None:
        path = Path(COMMAND_CHANNEL_STATE_DIR) / f"{chat_key}.json"
        if state:
            path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            path.unlink(missing_ok=True)
        self._channel_cache[chat_key] = state

    def _save_system_permission_state(self, state: dict[str, CommandPermission]) -> None:
        Path(COMMAND_SYSTEM_PERMISSION_FILE).write_text(
            json.dumps({key: value.value for key, value in state.items()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._system_permission_cache = state

    def _save_channel_permission_state(self, chat_key: str, state: dict[str, CommandPermission]) -> None:
        path = Path(COMMAND_CHANNEL_PERMISSION_DIR) / f"{chat_key}.json"
        if state:
            path.write_text(
                json.dumps({key: value.value for key, value in state.items()}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            path.unlink(missing_ok=True)
        self._channel_permission_cache[chat_key] = state

    @staticmethod
    def _is_plugin_command_source_enabled(
        source: str,
        plugin_enabled_cache: Optional[dict[str, bool]] = None,
    ) -> bool:
        """检查插件来源命令对应的插件是否已启用。"""
        if source == BUILT_IN_SOURCE:
            return True

        if plugin_enabled_cache is not None and source in plugin_enabled_cache:
            return plugin_enabled_cache[source]

        from nekro_agent.services.plugin.collector import plugin_collector

        plugin = plugin_collector.get_plugin(source)
        enabled = bool(plugin and plugin.is_enabled)
        if plugin_enabled_cache is not None:
            plugin_enabled_cache[source] = enabled
        return enabled

    def _is_command_enabled_impl(
        self,
        command_name: str,
        chat_key: Optional[str] = None,
        *,
        meta: Optional[CommandMetadata] = None,
        plugin_enabled_cache: Optional[dict[str, bool]] = None,
    ) -> bool:
        """统一的命令启用检查实现。"""
        target_meta = meta
        if target_meta is None:
            from nekro_agent.services.command.registry import command_registry

            command = command_registry.resolve(command_name)
            if command is not None:
                target_meta = command.metadata

        state_key = target_meta.name if target_meta is not None else command_name
        if target_meta is not None and not self._is_plugin_command_source_enabled(
            target_meta.source,
            plugin_enabled_cache,
        ):
            return False

        if chat_key:
            channel_state = self._load_channel_state(chat_key)
            if state_key in channel_state:
                return channel_state[state_key]

        system_state = self._load_system_state()
        if state_key in system_state:
            return system_state[state_key]

        return True

    def is_command_enabled_for_meta(
        self,
        meta: CommandMetadata,
        chat_key: Optional[str] = None,
        *,
        plugin_enabled_cache: Optional[dict[str, bool]] = None,
    ) -> bool:
        """按命令元数据查询启用状态，同时校验插件启用态。"""
        return self._is_command_enabled_impl(
            meta.name,
            chat_key,
            meta=meta,
            plugin_enabled_cache=plugin_enabled_cache,
        )

    def is_command_enabled(self, command_name: str, chat_key: Optional[str] = None) -> bool:
        """查询命令是否启用（频道级 > 系统级 > 默认），并兼容插件启用态。"""
        return self._is_command_enabled_impl(command_name, chat_key)

    def get_command_permission(
        self,
        command_name: str,
        default_permission: CommandPermission,
        chat_key: Optional[str] = None,
    ) -> CommandPermission:
        """查询命令生效权限（频道级 > 系统级 > 注册默认）"""
        if chat_key:
            channel_state = self._load_channel_permission_state(chat_key)
            if command_name in channel_state:
                return channel_state[command_name]

        system_state = self._load_system_permission_state()
        if command_name in system_state:
            return system_state[command_name]

        return default_permission

    def has_permission_override(
        self,
        command_name: str,
        chat_key: Optional[str] = None,
    ) -> bool:
        """当前作用域下是否存在权限覆盖"""
        if chat_key:
            return command_name in self._load_channel_permission_state(chat_key)
        return command_name in self._load_system_permission_state()

    @staticmethod
    def _resolve_command(command_name: str) -> tuple[str, CommandPermission]:
        """解析命令名（含别名）到规范名和默认权限，命令不存在则抛出 ValidationError。"""
        from nekro_agent.services.command.registry import command_registry

        command = command_registry.resolve(command_name)
        if command is None:
            raise ValidationError(reason=f"命令不存在: {command_name}")
        return command.metadata.name, command.metadata.permission

    @staticmethod
    def _get_command_default_permission(command_name: str) -> CommandPermission:
        _, permission = CommandManager._resolve_command(command_name)
        return permission

    async def set_command_enabled(
        self,
        command_name: str,
        enabled: bool,
        chat_key: Optional[str] = None,
    ) -> None:
        """设置命令启用状态"""
        canonical_name, _ = self._resolve_command(command_name)
        if chat_key:
            state = self._load_channel_state(chat_key)
            state[canonical_name] = enabled
            self._save_channel_state(chat_key, state)
        else:
            state = self._load_system_state()
            state[canonical_name] = enabled
            self._save_system_state(state)
        await self.notify_commands_changed(chat_key)

    async def set_command_permission(
        self,
        command_name: str,
        permission: CommandPermission | str,
        chat_key: Optional[str] = None,
    ) -> None:
        """设置命令权限覆盖"""
        normalized_permission = (
            permission if isinstance(permission, CommandPermission) else CommandPermission(permission)
        )
        canonical_name, default_permission = self._resolve_command(command_name)
        if chat_key:
            state = self._load_channel_permission_state(chat_key)
            inherited_permission = self.get_command_permission(canonical_name, default_permission, None)
            if normalized_permission == inherited_permission:
                state.pop(canonical_name, None)
            else:
                state[canonical_name] = normalized_permission
            self._save_channel_permission_state(chat_key, state)
        else:
            state = self._load_system_permission_state()
            if normalized_permission == default_permission:
                state.pop(canonical_name, None)
            else:
                state[canonical_name] = normalized_permission
            self._save_system_permission_state(state)
        await self.notify_commands_changed(chat_key)

    async def reset_command_state(
        self,
        command_name: str,
        chat_key: Optional[str] = None,
    ) -> None:
        """重置命令状态（删除覆盖，回退到上级）"""
        from nekro_agent.services.command.registry import command_registry

        resolved = command_registry.resolve(command_name)
        canonical_name = resolved.metadata.name if resolved is not None else command_name
        if chat_key:
            state = self._load_channel_state(chat_key)
            state.pop(canonical_name, None)
            self._save_channel_state(chat_key, state)
        else:
            state = self._load_system_state()
            state.pop(canonical_name, None)
            self._save_system_state(state)
        await self.notify_commands_changed(chat_key)

    async def reset_command_permission(
        self,
        command_name: str,
        chat_key: Optional[str] = None,
    ) -> None:
        """重置命令权限覆盖（删除覆盖，回退到上级）"""
        from nekro_agent.services.command.registry import command_registry

        resolved = command_registry.resolve(command_name)
        canonical_name = resolved.metadata.name if resolved is not None else command_name
        if chat_key:
            state = self._load_channel_permission_state(chat_key)
            state.pop(canonical_name, None)
            self._save_channel_permission_state(chat_key, state)
        else:
            state = self._load_system_permission_state()
            state.pop(canonical_name, None)
            self._save_system_permission_state(state)
        await self.notify_commands_changed(chat_key)

    async def get_all_command_states(
        self,
        chat_key: Optional[str] = None,
    ) -> list[dict]:
        """获取所有命令及其状态（用于 WebUI 展示）"""
        from nekro_agent.services.command.registry import command_registry
        from nekro_agent.services.plugin.collector import plugin_collector

        commands = command_registry.list_all_commands()
        channel_state = self._load_channel_state(chat_key) if chat_key else {}
        plugin_enabled_cache: dict[str, bool] = {}
        result = []
        for meta in commands:
            enabled = self.is_command_enabled_for_meta(meta, chat_key, plugin_enabled_cache=plugin_enabled_cache)
            permission = self.get_command_permission(meta.name, meta.permission, chat_key)
            has_channel_override = chat_key is not None and meta.name in channel_state
            has_permission_override = self.has_permission_override(meta.name, chat_key)
            source_display_name = "内置" if meta.source == BUILT_IN_SOURCE else meta.source
            if meta.source != BUILT_IN_SOURCE:
                plugin = plugin_collector.get_plugin(meta.source)
                if plugin:
                    source_display_name = plugin.name

            result.append({
                "name": meta.name,
                "namespace": meta.namespace,
                "aliases": meta.aliases,
                "description": meta.description,
                "usage": meta.usage,
                "permission": permission.value,
                "default_permission": meta.permission.value,
                "category": meta.category,
                "source": meta.source,
                "source_display_name": source_display_name,
                "enabled": enabled,
                "has_channel_override": has_channel_override,
                "has_permission_override": has_permission_override,
                "params_schema": meta.params_schema,
                "i18n_description": meta.i18n_description,
                "i18n_usage": meta.i18n_usage,
                "i18n_category": meta.i18n_category,
            })
        return result

    async def notify_commands_changed(self, chat_key: Optional[str] = None) -> None:
        """通知所有支持补全的适配器重新同步命令列表"""
        from nekro_agent.adapters import loaded_adapters

        for adapter in loaded_adapters.values():
            if adapter.supports_command_completion:
                try:
                    await adapter.sync_commands(chat_key)
                except Exception as e:
                    logger.warning(f"适配器 {adapter.key} 同步命令失败: {e}")

    def invalidate_cache(self) -> None:
        """清除缓存（配置文件外部修改后调用）"""
        self._system_cache = None
        self._channel_cache.clear()
        self._system_permission_cache = None
        self._channel_permission_cache.clear()


command_manager = CommandManager()
