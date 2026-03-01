"""命令状态管理 - 基于 JSON 文件存储"""

import json
from pathlib import Path
from typing import Optional

from nonebot import logger

from nekro_agent.core.os_env import OsEnv

COMMAND_STATE_DIR = Path(OsEnv.DATA_DIR) / "configs" / "command_states"
SYSTEM_STATE_FILE = COMMAND_STATE_DIR / "system.json"
CHANNEL_STATE_DIR = COMMAND_STATE_DIR / "channels"


class CommandManager:
    """命令状态管理 - 基于 JSON 文件存储

    状态优先级: 频道级 > 系统级 > 默认启用
    """

    def __init__(self):
        COMMAND_STATE_DIR.mkdir(parents=True, exist_ok=True)
        CHANNEL_STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._system_cache: Optional[dict[str, bool]] = None
        self._channel_cache: dict[str, dict[str, bool]] = {}

    def _load_system_state(self) -> dict[str, bool]:
        """加载系统级状态（带缓存）"""
        if self._system_cache is None:
            if SYSTEM_STATE_FILE.exists():
                try:
                    self._system_cache = json.loads(SYSTEM_STATE_FILE.read_text(encoding="utf-8"))
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
            path = CHANNEL_STATE_DIR / f"{chat_key}.json"
            if path.exists():
                try:
                    self._channel_cache[chat_key] = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning(f"加载频道 {chat_key} 命令状态失败: {e}")
                    self._channel_cache[chat_key] = {}
            else:
                self._channel_cache[chat_key] = {}
        return self._channel_cache[chat_key]

    def _save_system_state(self, state: dict[str, bool]) -> None:
        SYSTEM_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        self._system_cache = state

    def _save_channel_state(self, chat_key: str, state: dict[str, bool]) -> None:
        path = CHANNEL_STATE_DIR / f"{chat_key}.json"
        if state:
            path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            path.unlink(missing_ok=True)  # 空状态则删除文件
        self._channel_cache[chat_key] = state

    def is_command_enabled(self, command_name: str, chat_key: Optional[str] = None) -> bool:
        """查询命令是否启用（频道级 > 系统级 > 默认）"""
        if chat_key:
            channel_state = self._load_channel_state(chat_key)
            if command_name in channel_state:
                return channel_state[command_name]

        system_state = self._load_system_state()
        if command_name in system_state:
            return system_state[command_name]

        return True  # 默认启用

    async def set_command_enabled(
        self,
        command_name: str,
        enabled: bool,
        chat_key: Optional[str] = None,
    ) -> None:
        """设置命令启用状态"""
        if chat_key:
            state = self._load_channel_state(chat_key)
            state[command_name] = enabled
            self._save_channel_state(chat_key, state)
        else:
            state = self._load_system_state()
            state[command_name] = enabled
            self._save_system_state(state)
        await self.notify_commands_changed(chat_key)

    async def reset_command_state(
        self,
        command_name: str,
        chat_key: Optional[str] = None,
    ) -> None:
        """重置命令状态（删除覆盖，回退到上级）"""
        if chat_key:
            state = self._load_channel_state(chat_key)
            state.pop(command_name, None)
            self._save_channel_state(chat_key, state)
        else:
            state = self._load_system_state()
            state.pop(command_name, None)
            self._save_system_state(state)

    async def get_all_command_states(
        self,
        chat_key: Optional[str] = None,
    ) -> list[dict]:
        """获取所有命令及其状态（用于 WebUI 展示）"""
        from nekro_agent.services.command.registry import command_registry

        commands = command_registry.list_all_commands()
        channel_state = self._load_channel_state(chat_key) if chat_key else {}
        result = []
        for meta in commands:
            enabled = self.is_command_enabled(meta.name, chat_key)
            has_channel_override = chat_key is not None and meta.name in channel_state

            result.append({
                "name": meta.name,
                "namespace": meta.namespace,
                "aliases": meta.aliases,
                "description": meta.description,
                "usage": meta.usage,
                "permission": meta.permission.value,
                "category": meta.category,
                "source": meta.source,
                "enabled": enabled,
                "has_channel_override": has_channel_override,
                "params_schema": meta.params_schema,
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


command_manager = CommandManager()
