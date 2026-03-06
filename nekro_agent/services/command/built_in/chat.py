"""内置命令 - 会话类: reset, stop, inspect"""

from typing import Annotated

from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


class ResetCommand(BaseCommand):
    """重置对话上下文"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="reset",
            description="重置对话上下文",
            usage="reset [chat_key]",
            permission=CommandPermission.SUPER_USER,
            category="会话",
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        target: Annotated[str, Arg("目标频道（留空则为当前频道，超级用户可指定其他频道）", positional=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.models.db_chat_channel import DBChatChannel
        from nekro_agent.models.db_chat_message import DBChatMessage

        # 非超级用户只能操作当前频道
        target_chat_key = target if target and context.is_super_user else context.chat_key

        if not target_chat_key:
            return CmdCtl.failed("聊天标识获取失败")

        db_chat_channel = await DBChatChannel.get_channel(chat_key=target_chat_key)

        # 获取重置前的消息统计
        msg_cnt = await DBChatMessage.filter(
            chat_key=target_chat_key,
            send_timestamp__gte=int(db_chat_channel.conversation_start_time.timestamp()),
        ).count()

        # 只重置对话起始时间，不删除历史消息
        await db_chat_channel.reset_channel()

        return CmdCtl.success(f"已重置 {target_chat_key} 的对话上下文（当前会话 {msg_cnt} 条消息已归档）")


class StopCommand(BaseCommand):
    """终止当前频道正在进行的回复流程"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="stop",
            aliases=["stop-stream"],
            description="停止当前回复流程",
            usage="stop [chat_key]",
            permission=CommandPermission.SUPER_USER,
            category="会话",
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        target: Annotated[str, Arg("目标频道（留空则为当前频道）", positional=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.services.message_service import message_service

        target_chat_key = target if target and context.is_super_user else context.chat_key

        cancelled = await message_service.cancel_agent_task(target_chat_key)
        if cancelled:
            return CmdCtl.success("已终止当前回复流程")
        else:
            return CmdCtl.success("当前没有正在进行的回复流程")


class InspectCommand(BaseCommand):
    """查询频道信息"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="inspect",
            description="查询频道信息",
            usage="inspect [chat_key]",
            permission=CommandPermission.SUPER_USER,
            category="会话",
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        target: Annotated[str, Arg("目标频道（留空则为当前频道）", positional=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.models.db_chat_channel import DBChatChannel

        target_chat_key = target or context.chat_key
        if not target_chat_key:
            return CmdCtl.failed("请指定要查询的聊天")

        db_chat_channel = await DBChatChannel.get_channel(chat_key=target_chat_key)
        preset = await db_chat_channel.get_preset()
        info = f"基本人设: {preset.name}"

        return CmdCtl.success(
            f"频道 {target_chat_key} 信息：\n{info}",
            data={"chat_key": target_chat_key, "preset": preset.name},
        )
