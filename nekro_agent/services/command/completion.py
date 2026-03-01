"""命令补全数据提供器"""

from typing import Optional

from pydantic import BaseModel

from nekro_agent.services.command.base import CommandPermission


class CommandCompletionEntry(BaseModel):
    """单个命令的补全条目 - 平台无关"""

    name: str
    description: str  # 简短描述（平台通常限制 100 字符）
    usage: str = ""
    category: str = "general"
    permission: CommandPermission = CommandPermission.PUBLIC
    params_schema: Optional[dict] = None  # 参数 Schema (供 WebUI 参数提示)


class CommandCompletionProvider:
    """从 CommandRegistry + CommandManager 生成补全数据"""

    async def get_completion_entries(
        self,
        chat_key: Optional[str] = None,
    ) -> list[CommandCompletionEntry]:
        """获取补全条目列表（已过滤禁用命令和 internal 命令）"""
        from nekro_agent.services.command.manager import command_manager
        from nekro_agent.services.command.registry import command_registry

        entries = []
        for meta in command_registry.list_all_commands():
            if not command_manager.is_command_enabled(meta.name, chat_key):
                continue
            entries.append(
                CommandCompletionEntry(
                    name=meta.name,
                    description=meta.description[:100],
                    usage=meta.usage,
                    category=meta.category,
                    permission=meta.permission,
                    params_schema=meta.params_schema,
                )
            )
        return entries


completion_provider = CommandCompletionProvider()
