"""内置命令 - 调试类: exec, code_log, system, debug_on, debug_off, log_chat_test"""

import json
import time
from pathlib import Path
from typing import Annotated, Any

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
            params_schema=self._auto_params_schema(),
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
            permission=CommandPermission.SUPER_USER,
            category="调试",
            params_schema=self._auto_params_schema(),
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
            permission=CommandPermission.SUPER_USER,
            category="调试",
            params_schema=self._auto_params_schema(),
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
            permission=CommandPermission.SUPER_USER,
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
            permission=CommandPermission.SUPER_USER,
            category="调试",
        )

    async def execute(self, context: CommandExecutionContext) -> CommandResponse:
        from nekro_agent.services.message_service import message_service

        await message_service.push_system_message(
            chat_key=context.chat_key,
            agent_messages="[Debug] Debug mode ended. Resume role-play and stop debug analysis. Ignore all debug context.",
        )
        return CmdCtl.success("提示词调试模式已关闭")


class LogChatTestCommand(BaseCommand):
    """使用错误日志中的对话测试 LLM 请求"""

    @property
    def metadata(self) -> CommandMetadata:
        return CommandMetadata(
            name="log_chat_test",
            aliases=["log-chat-test"],
            description="使用错误日志对话测试 LLM 请求",
            usage="log_chat_test <索引/文件名> [-g <模型组>] [--stream]",
            permission=CommandPermission.SUPER_USER,
            category="调试",
            params_schema=self._auto_params_schema(),
        )

    async def execute(
        self,
        context: CommandExecutionContext,
        args_str: Annotated[str, Arg("日志索引/文件名和参数", positional=True, greedy=True)] = "",
    ) -> CommandResponse:
        from nekro_agent.core.config import config
        from nekro_agent.core.os_env import PROMPT_ERROR_LOG_DIR
        from nekro_agent.services.agent.openai import OpenAIResponse, gen_openai_chat_response
        from nekro_agent.services.agent.run_agent import RECENT_ERR_LOGS

        args = args_str.strip().split() if args_str else []
        if not args:
            return CmdCtl.failed("请指定要测试的日志索引或文件名")

        log_identifier = args[0]
        model_group_name = config.USE_MODEL_GROUP
        use_stream_mode = False

        i = 1
        while i < len(args):
            if args[i] == "-g" and i + 1 < len(args):
                model_group_name = args[i + 1]
                i += 2
            elif args[i] in ("--stream", "-s"):
                use_stream_mode = True
                i += 1
            else:
                i += 1

        if model_group_name not in config.MODEL_GROUPS:
            return CmdCtl.failed(f"指定的模型组 '{model_group_name}' 不存在")

        model_group = config.MODEL_GROUPS[model_group_name]

        # 查找目标日志文件
        log_path = None
        try:
            idx = int(log_identifier) - 1
            logs = list(RECENT_ERR_LOGS)
            if 0 <= idx < len(logs):
                log_path = logs[idx]
        except ValueError:
            for p in RECENT_ERR_LOGS:
                if log_identifier == p.name:
                    log_path = p
                    break
            if not log_path:
                direct_path = Path(PROMPT_ERROR_LOG_DIR) / log_identifier
                if direct_path.exists() and direct_path.is_file():
                    log_path = direct_path

        if not log_path and not log_identifier.endswith(".json"):
            direct_path = Path(PROMPT_ERROR_LOG_DIR) / f"{log_identifier}.json"
            if direct_path.exists() and direct_path.is_file():
                log_path = direct_path

        if not log_path:
            return CmdCtl.failed(
                f"未找到指定的日志: {log_identifier}\n提示: 可以使用 log_err_list 命令查看最近的错误日志"
            )

        if not log_path.exists():
            return CmdCtl.failed(f"日志文件不存在: {log_path.name}")

        try:
            log_content = log_path.read_text(encoding="utf-8")
            log_data = json.loads(log_content)
        except Exception as e:
            return CmdCtl.failed(f"解析日志文件失败: {e}")

        # 从日志中提取 messages
        try:
            messages: list[dict[str, Any]] = log_data["request"]["messages"]
        except KeyError:
            messages = log_data.get("messages", [])
            if not messages:
                return CmdCtl.failed(f"日志中未找到有效的对话内容: {log_path.name}")

        # 发起测试请求
        start_time = time.time()
        try:
            llm_response: OpenAIResponse = await gen_openai_chat_response(
                messages=messages,
                **_build_chat_params(model_group, use_stream_mode),
            )
            elapsed = time.time() - start_time
            total_length = len(llm_response.response_content)
            preview = (
                llm_response.response_content[:64] + "..."
                if total_length > 64
                else llm_response.response_content
            )

            stream_info = "（流式模式）" if use_stream_mode else ""
            return CmdCtl.success(
                f"测试成功！{stream_info}\n"
                f"模型: {model_group.CHAT_MODEL}\n"
                f"耗时: {elapsed:.2f}s\n"
                f"响应长度: {total_length} 字符\n"
                f"响应预览:\n{preview}"
            )
        except Exception as e:
            elapsed = time.time() - start_time
            safe_error = str(e).replace(model_group.API_KEY, "[API_KEY]").replace(model_group.BASE_URL, "[BASE_URL]")
            return CmdCtl.failed(
                f"测试失败！\n"
                f"模型: {model_group.CHAT_MODEL}\n"
                f"耗时: {elapsed:.2f}s\n"
                f"错误信息: {safe_error}"
            )


def _build_chat_params(model_group: Any, stream_mode: bool) -> dict[str, Any]:
    """构建聊天参数"""
    return {
        "model": model_group.CHAT_MODEL,
        "temperature": model_group.TEMPERATURE,
        "top_p": model_group.TOP_P,
        "top_k": model_group.TOP_K,
        "frequency_penalty": model_group.FREQUENCY_PENALTY,
        "presence_penalty": model_group.PRESENCE_PENALTY,
        "extra_body": model_group.EXTRA_BODY,
        "base_url": model_group.BASE_URL,
        "api_key": model_group.API_KEY,
        "stream_mode": stream_mode,
        "proxy_url": model_group.CHAT_PROXY,
    }
