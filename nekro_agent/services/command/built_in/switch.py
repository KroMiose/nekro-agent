"""内置命令 - 开关类: na_on, na_off, na_observe"""

from typing import Annotated

from nekro_agent.schemas.i18n import i18n_text, t
from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


class NaOnCommand(BaseCommand):
    """开启聊天功能"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_on",
            aliases=["na-on"],
            description="开启指定聊天的聊天功能",
            i18n_description=i18n_text(zh_CN="开启指定聊天的聊天功能", en_US="Enable chat function for specified channel"),
            usage="na_on [chat_key|*|private_*|group_*]",
            permission=CommandPermission.SUPER_USER,
            category="开关",
            i18n_category=i18n_text(zh_CN="开关", en_US="Switch"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        target: Annotated[str, Arg("目标频道（*=全部, private_*=所有私聊, group_*=所有群聊）", positional=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.models.db_chat_channel import DBChatChannel
        from nekro_agent.schemas.chat_message import ChatType

        target_chat_key = target or context.chat_key
        if not target_chat_key:
            return CmdCtl.failed(t(zh_CN="请指定要操作的聊天", en_US="Please specify the target chat"))

        if target_chat_key == "*":
            for channel in await DBChatChannel.all():
                await channel.set_channel_status("active")
            return CmdCtl.success(
                t(zh_CN="已开启所有聊天的聊天功能", en_US="Enabled chat function for all channels")
            )

        if target_chat_key == "private_*":
            for channel in await DBChatChannel.all():
                if channel.chat_type == ChatType.PRIVATE:
                    await channel.set_channel_status("active")
            return CmdCtl.success(
                t(zh_CN="已开启所有私聊的聊天功能", en_US="Enabled chat function for all private chats")
            )

        if target_chat_key == "group_*":
            for channel in await DBChatChannel.all():
                if channel.chat_type == ChatType.GROUP:
                    await channel.set_channel_status("active")
            return CmdCtl.success(
                t(zh_CN="已开启所有群聊的聊天功能", en_US="Enabled chat function for all group chats")
            )

        db_chat_channel = await DBChatChannel.get_channel(chat_key=target_chat_key)
        await db_chat_channel.set_channel_status("active")
        return CmdCtl.success(
            t(zh_CN=f"已开启 {target_chat_key} 的聊天功能", en_US=f"Enabled chat function for {target_chat_key}")
        )


class NaOffCommand(BaseCommand):
    """关闭聊天功能"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_off",
            aliases=["na-off"],
            description="关闭指定聊天的聊天功能",
            i18n_description=i18n_text(zh_CN="关闭指定聊天的聊天功能", en_US="Disable chat function for specified channel"),
            usage="na_off [chat_key|*|private_*|group_*]",
            permission=CommandPermission.SUPER_USER,
            category="开关",
            i18n_category=i18n_text(zh_CN="开关", en_US="Switch"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        target: Annotated[str, Arg("目标频道（*=全部, private_*=所有私聊, group_*=所有群聊）", positional=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.models.db_chat_channel import DBChatChannel
        from nekro_agent.schemas.chat_message import ChatType

        target_chat_key = target or context.chat_key
        if not target_chat_key:
            return CmdCtl.failed(t(zh_CN="请指定要操作的聊天", en_US="Please specify the target chat"))

        if target_chat_key == "*":
            for channel in await DBChatChannel.all():
                await channel.set_channel_status("disabled")
            return CmdCtl.success(
                t(zh_CN="已关闭所有聊天的聊天功能", en_US="Disabled chat function for all channels")
            )

        if target_chat_key == "private_*":
            for channel in await DBChatChannel.all():
                if channel.chat_type == ChatType.PRIVATE:
                    await channel.set_channel_status("disabled")
            return CmdCtl.success(
                t(zh_CN="已关闭所有私聊的聊天功能", en_US="Disabled chat function for all private chats")
            )

        if target_chat_key == "group_*":
            for channel in await DBChatChannel.all():
                if channel.chat_type == ChatType.GROUP:
                    await channel.set_channel_status("disabled")
            return CmdCtl.success(
                t(zh_CN="已关闭所有群聊的聊天功能", en_US="Disabled chat function for all group chats")
            )

        db_chat_channel = await DBChatChannel.get_channel(chat_key=target_chat_key)
        await db_chat_channel.set_channel_status("disabled")
        return CmdCtl.success(
            t(zh_CN=f"已关闭 {target_chat_key} 的聊天功能", en_US=f"Disabled chat function for {target_chat_key}")
        )


class NaObserveCommand(BaseCommand):
    """设置聊天为旁观模式"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_observe",
            aliases=["na-observe"],
            description="设置指定聊天为旁观模式（仅记录消息，不触发回复）",
            i18n_description=i18n_text(
                zh_CN="设置指定聊天为旁观模式（仅记录消息，不触发回复）",
                en_US="Set specified channel to observe mode (record messages only, no replies)",
            ),
            usage="na_observe [chat_key|*|private_*|group_*]",
            permission=CommandPermission.SUPER_USER,
            category="开关",
            i18n_category=i18n_text(zh_CN="开关", en_US="Switch"),
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        target: Annotated[str, Arg("目标频道（*=全部, private_*=所有私聊, group_*=所有群聊）", positional=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.models.db_chat_channel import DBChatChannel
        from nekro_agent.schemas.chat_message import ChatType

        target_chat_key = target or context.chat_key
        if not target_chat_key:
            return CmdCtl.failed(t(zh_CN="请指定要操作的聊天", en_US="Please specify the target chat"))

        if target_chat_key == "*":
            for channel in await DBChatChannel.all():
                await channel.set_channel_status("observe")
            return CmdCtl.success(
                t(zh_CN="已将所有聊天设为旁观模式", en_US="Set all channels to observe mode")
            )

        if target_chat_key == "private_*":
            for channel in await DBChatChannel.all():
                if channel.chat_type == ChatType.PRIVATE:
                    await channel.set_channel_status("observe")
            return CmdCtl.success(
                t(zh_CN="已将所有私聊设为旁观模式", en_US="Set all private chats to observe mode")
            )

        if target_chat_key == "group_*":
            for channel in await DBChatChannel.all():
                if channel.chat_type == ChatType.GROUP:
                    await channel.set_channel_status("observe")
            return CmdCtl.success(
                t(zh_CN="已将所有群聊设为旁观模式", en_US="Set all group chats to observe mode")
            )

        db_chat_channel = await DBChatChannel.get_channel(chat_key=target_chat_key)
        await db_chat_channel.set_channel_status("observe")
        return CmdCtl.success(
            t(
                zh_CN=f"已将 {target_chat_key} 设为旁观模式",
                en_US=f"Set {target_chat_key} to observe mode",
            )
        )
