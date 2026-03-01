"""内置命令 - 信息类: na_info, na_help"""

from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import CommandExecutionContext, CommandResponse


class NaInfoCommand(BaseCommand):
    """查看系统信息"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_info",
            aliases=["na-info"],
            description="查看系统信息",
            permission=CommandPermission.SUPER_USER,
            category="信息",
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.core.config import config
        from nekro_agent.core.os_env import OsEnv
        from nekro_agent.models.db_chat_channel import DBChatChannel
        from nekro_agent.tools.common_util import get_app_version

        db_chat_channel = await DBChatChannel.get_channel(chat_key=context.chat_key)
        preset = await db_chat_channel.get_preset()
        version = get_app_version()

        message = (
            f"[Nekro-Agent 信息]\n"
            f"> 更智能、更优雅的代理执行 AI\n"
            f"Author: KroMiose\n"
            f"Github: https://github.com/KroMiose/nekro-agent\n"
            f"Version: {version}\n"
            f"In-Docker: {OsEnv.RUN_IN_DOCKER}\n"
            "========聊天设定========\n"
            f"人设: {preset.name}\n"
            f"当前模型组: {config.USE_MODEL_GROUP}"
        )

        return CmdCtl.success(
            message=message,
            data={
                "version": version,
                "in_docker": OsEnv.RUN_IN_DOCKER,
                "preset": preset.name,
                "model_group": config.USE_MODEL_GROUP,
            },
        )


class NaHelpCommand(BaseCommand):
    """查看帮助信息"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_help",
            aliases=["na-help"],
            description="查看帮助信息",
            permission=CommandPermission.USER,
            category="信息",
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.services.command.registry import command_registry
        from nekro_agent.tools.common_util import get_app_version

        # 从注册表动态生成帮助信息
        commands = command_registry.list_all_commands()
        conflicts = command_registry.get_conflicting_short_names()

        # 按分类分组
        categories: dict[str, list[str]] = {}
        for meta in commands:
            cat = meta.category
            categories.setdefault(cat, [])
            # 构建命令描述行
            name = meta.name
            if name in conflicts:
                name = f"{meta.namespace}:{meta.name}"
            alias_str = f" ({', '.join(meta.aliases)})" if meta.aliases else ""
            perm_str = f"[{meta.permission.value.upper()}]" if meta.permission != CommandPermission.PUBLIC else ""
            line = f"{name}{alias_str}: {meta.description} {perm_str}".strip()
            categories[cat].append(line)

        # 构建输出
        parts = ["[Nekro-Agent 帮助]"]
        for cat_name, lines in categories.items():
            parts.append(f"\n====== [{cat_name}] ======")
            parts.extend(lines)

        parts.append("\n====== [更多信息] ======")
        parts.append(f"Version: {get_app_version()}")
        parts.append("Github: https://github.com/KroMiose/nekro-agent")

        return CmdCtl.success(message="\n".join(parts))
