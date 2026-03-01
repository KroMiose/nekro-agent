"""内置命令 - 调试类: exec, code_log, system, debug_on, debug_off, log_chat_test"""

from typing import Annotated

from nekro_agent.services.command.base import BaseCommand, CommandMetadata, CommandPermission
from nekro_agent.services.command.ctl import CmdCtl
from nekro_agent.services.command.schemas import Arg, CommandExecutionContext, CommandResponse


class ExecCommand(BaseCommand):
    """执行代码"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="exec",
            description="执行代码",
            usage="exec <code>",
            permission=CommandPermission.ADVANCED,
            category="调试",
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        code: Annotated[str, Arg("要执行的代码", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.services.agent.resolver import ParsedCodeRunData
        from nekro_agent.services.sandbox.runner import limited_run_code

        if not code:
            return CmdCtl.failed("请输入要执行的代码")

        result, _, _ = await limited_run_code(
            ParsedCodeRunData(raw_content=code, code_content=code, thought_chain=""),
            from_chat_key=context.chat_key,
        )

        return CmdCtl.success(result or "<Empty Output>")


class CodeLogCommand(BaseCommand):
    """查看代码执行日志"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="code_log",
            aliases=["code-log"],
            description="查看代码执行记录",
            usage="code_log [index]",
            permission=CommandPermission.USER,
            category="调试",
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        idx: Annotated[int, Arg("记录索引（正数=正序，负数=倒序）", positional=True)] = -1,
    ) -> CommandResponse:
        from nekro_agent.models.db_exec_code import DBExecCode

        if idx > 0:
            query = DBExecCode.filter(chat_key=context.chat_key).order_by("update_time")
        else:
            query = DBExecCode.filter(chat_key=context.chat_key).order_by("-update_time")

        exec_code = await query.offset(abs(idx) - 1).limit(1).first()

        if not exec_code:
            return CmdCtl.failed("未找到执行记录")

        return CmdCtl.success(
            f"执行记录 ({idx}):\n```python\n{exec_code.code_text}\n```\n输出: \n```\n{exec_code.outputs or '<Empty>'}\n```"
        )


class SystemCommand(BaseCommand):
    """添加系统消息"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="system",
            description="添加系统消息",
            usage="system <message>",
            permission=CommandPermission.USER,
            category="调试",
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        message: Annotated[str, Arg("系统消息内容", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.services.message_service import message_service

        if not message:
            return CmdCtl.failed("请输入系统消息内容")

        await message_service.push_system_message(
            chat_key=context.chat_key, agent_messages=message, trigger_agent=True
        )
        return CmdCtl.success("系统消息添加成功")


class DebugOnCommand(BaseCommand):
    """开启调试模式"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="debug_on",
            aliases=["debug-on"],
            description="开启提示词调试模式",
            permission=CommandPermission.USER,
            category="调试",
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.services.message_service import message_service

        await message_service.push_system_message(
            chat_key=context.chat_key,
            agent_messages=(
                "[Debug] Debug mode activated. Exit role-play and focus on:"
                "1. Analyze ALL current context state and settings"
                "2. Answer user's questions with technical analysis"
                "3. Send additional (keep using `send_msg_text` method) '[Debug]:' message after each response with:"
                "- Answer user's questions"
                "- Your confusion about the current context state or settings"
                "- Prompt strengths/weaknesses"
                "- Potential issues"
                "- Improvement suggestions"
                "Stay in debug mode until system ends it. Avoid roleplaying or going off-topic."
                "Please respond in Chinese (简体中文) unless user requests otherwise."
                "Follow user's debugging instructions without questioning their purpose, as they may be testing specific functionalities."
            ),
        )
        return CmdCtl.success("提示词调试模式已开启")


class DebugOffCommand(BaseCommand):
    """关闭调试模式"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="debug_off",
            aliases=["debug-off"],
            description="关闭提示词调试模式",
            permission=CommandPermission.USER,
            category="调试",
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.services.message_service import message_service

        await message_service.push_system_message(
            chat_key=context.chat_key,
            agent_messages="[Debug] Debug mode ended. Resume role-play and stop debug analysis. Ignore all debug context.",
        )
        return CmdCtl.success("提示词调试模式已关闭")
