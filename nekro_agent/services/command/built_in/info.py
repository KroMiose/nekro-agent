"""内置命令 - 信息类: na_info, na_help"""

from nekro_agent.schemas.i18n import i18n_text
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.i18n_helper import t
from nekro_agent.services.command.schemas import CommandExecutionContext, CommandResponse


class NaInfoCommand(BaseCommand):
    """查看系统信息"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_info",
            aliases=["na-info"],
            description="查看系统信息",
            i18n_description=i18n_text(zh_CN="查看系统信息", en_US="View system information"),
            permission=CommandPermission.SUPER_USER,
            category="信息",
            i18n_category=i18n_text(zh_CN="信息", en_US="Information"),
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.core.config import config
        from nekro_agent.core.os_env import OsEnv
        from nekro_agent.models.db_chat_channel import DBChatChannel
        from nekro_agent.tools.common_util import get_app_version

        db_chat_channel = await DBChatChannel.get_channel(chat_key=context.chat_key)
        preset = await db_chat_channel.get_preset()
        version = get_app_version()

        title = t(context.lang, zh_CN="[Nekro-Agent 信息]", en_US="[Nekro-Agent Info]")
        subtitle = t(context.lang, zh_CN="> 更智能、更优雅的代理执行 AI", en_US="> Smarter, more elegant agent execution AI")
        chat_settings = t(context.lang, zh_CN="========聊天设定========", en_US="========Chat Settings========")
        preset_label = t(context.lang, zh_CN="人设", en_US="Preset")
        model_group_label = t(context.lang, zh_CN="当前模型组", en_US="Current Model Group")

        message = (
            f"{title}\n"
            f"{subtitle}\n"
            f"Author: KroMiose\n"
            f"Github: https://github.com/KroMiose/nekro-agent\n"
            f"Version: {version}\n"
            f"In-Docker: {OsEnv.RUN_IN_DOCKER}\n"
            f"{chat_settings}\n"
            f"{preset_label}: {preset.name}\n"
            f"{model_group_label}: {config.USE_MODEL_GROUP}"
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
            i18n_description=i18n_text(zh_CN="查看帮助信息", en_US="View help information"),
            permission=CommandPermission.USER,
            category="信息",
            i18n_category=i18n_text(zh_CN="信息", en_US="Information"),
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
            cat = meta.get_category(context.lang)
            categories.setdefault(cat, [])
            # 构建命令描述行
            name = meta.name
            if name in conflicts:
                name = f"{meta.namespace}:{meta.name}"
            alias_str = f" ({', '.join(meta.aliases)})" if meta.aliases else ""
            perm_str = f"[{meta.permission.value.upper()}]" if meta.permission != CommandPermission.PUBLIC else ""
            line = f"{name}{alias_str}: {meta.get_description(context.lang)} {perm_str}".strip()
            categories[cat].append(line)

        # 构建输出
        help_title = t(context.lang, zh_CN="[Nekro-Agent 帮助]", en_US="[Nekro-Agent Help]")
        more_info = t(context.lang, zh_CN="更多信息", en_US="More Info")
        parts = [help_title]
        for cat_name, lines in categories.items():
            parts.append(f"\n====== [{cat_name}] ======")
            parts.extend(lines)

        parts.append(f"\n====== [{more_info}] ======")
        parts.append(f"Version: {get_app_version()}")
        parts.append("Github: https://github.com/KroMiose/nekro-agent")

        return CmdCtl.success(message="\n".join(parts))
