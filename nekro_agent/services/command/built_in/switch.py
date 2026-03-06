"""内置命令 - 开关类: na_on, na_off"""

from typing import Annotated

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
            usage="na_on [chat_key|*|private_*|group_*]",
            permission=CommandPermission.SUPER_USER,
            category="开关",
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
            return CmdCtl.failed("请指定要操作的聊天")

        if target_chat_key == "*":
            for channel in await DBChatChannel.all():
                await channel.set_active(True)
            return CmdCtl.success("已开启所有聊天的聊天功能")

        if target_chat_key == "private_*":
            for channel in await DBChatChannel.all():
                if channel.chat_type == ChatType.PRIVATE:
                    await channel.set_active(True)
            return CmdCtl.success("已开启所有私聊的聊天功能")

        if target_chat_key == "group_*":
            for channel in await DBChatChannel.all():
                if channel.chat_type == ChatType.GROUP:
                    await channel.set_active(True)
            return CmdCtl.success("已开启所有群聊的聊天功能")

        db_chat_channel = await DBChatChannel.get_channel(chat_key=target_chat_key)
        await db_chat_channel.set_active(True)
        return CmdCtl.success(f"已开启 {target_chat_key} 的聊天功能")


class NaOffCommand(BaseCommand):
    """关闭聊天功能"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="na_off",
            aliases=["na-off"],
            description="关闭指定聊天的聊天功能",
            usage="na_off [chat_key|*|private_*|group_*]",
            permission=CommandPermission.SUPER_USER,
            category="开关",
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
            return CmdCtl.failed("请指定要操作的聊天")

        if target_chat_key == "*":
            for channel in await DBChatChannel.all():
                await channel.set_active(False)
            return CmdCtl.success("已关闭所有聊天的聊天功能")

        if target_chat_key == "private_*":
            for channel in await DBChatChannel.all():
                if channel.chat_type == ChatType.PRIVATE:
                    await channel.set_active(False)
            return CmdCtl.success("已关闭所有私聊的聊天功能")

        if target_chat_key == "group_*":
            for channel in await DBChatChannel.all():
                if channel.chat_type == ChatType.GROUP:
                    await channel.set_active(False)
            return CmdCtl.success("已关闭所有群聊的聊天功能")

        db_chat_channel = await DBChatChannel.get_channel(chat_key=target_chat_key)
        await db_chat_channel.set_active(False)
        return CmdCtl.success(f"已关闭 {target_chat_key} 的聊天功能")
