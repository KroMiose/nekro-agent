import datetime
import json
import os
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import weave
from jinja2 import Environment

from nekro_agent.core import logger
from nekro_agent.core.config import CoreConfig, ModelConfigGroup
from nekro_agent.core.config import config as core_config
from nekro_agent.core.os_env import PROMPT_ERROR_LOG_DIR, PROMPT_LOG_DIR
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_exec_code import ExecStopType
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.schemas.chat_message import ChatMessage
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.sandbox.runner import limited_run_code

from ..config_resolver import config_resolver
from .creator import OpenAIChatMessage
from .openai import OpenAIResponse, gen_openai_chat_response
from .resolver import ParsedCodeRunData, parse_chat_response
from .templates.base import env as default_env
from .templates.history import HistoryFirstStart, render_history_data
from .templates.plugin import render_plugins_prompt
from .templates.practice import (
    BasePracticePrompt_question,
    BasePracticePrompt_response,
    PracticePrompt_question_1,
    PracticePrompt_question_2,
    PracticePrompt_response_1,
    PracticePrompt_response_2,
)
from .templates.system import SystemPrompt

# 使用deque保存最近100条错误日志路径
RECENT_ERR_LOGS = deque(maxlen=100)


@weave.op(name="run_agent")
async def run_agent(
    chat_key: str,
    chat_message: Optional[ChatMessage] = None,
):
    # 获取当前会话的有效配置
    one_time_code = os.urandom(4).hex()
    db_chat_channel: DBChatChannel = await DBChatChannel.get(chat_key=chat_key)
    config = await db_chat_channel.get_effective_config()
    preset = await db_chat_channel.get_preset()
    ctx: AgentCtx = AgentCtx.create_by_db_chat_channel(db_chat_channel=db_chat_channel)
    adapter_dialog_examples = await ctx.adapter.set_dialog_example()
    adapter_jinja_env = await ctx.adapter.get_jinja_env()
    self_info = await ctx.adapter.get_self_info()

    # 获取当前使用的模型组
    used_model_group: ModelConfigGroup = config.MODEL_GROUPS[config.USE_MODEL_GROUP]

    messages = [
        OpenAIChatMessage.from_template(
            "system",
            SystemPrompt(
                one_time_code=one_time_code,
                platform_name=self_info.platform_name,
                bot_platform_id=self_info.user_id,
                chat_preset=preset.content,
                chat_key=chat_key,
                plugins_prompt=await render_plugins_prompt(plugin_collector.get_all_active_plugins(), ctx),
                admin_chat_key=config.ADMIN_CHAT_KEY,
                enable_cot=used_model_group.ENABLE_COT,
                chat_key_rules="\n".join([f"- {r}" for r in [db_chat_channel.adapter.chat_key_rules]]),
                enable_at=db_chat_channel.adapter.config.SESSION_ENABLE_AT,
            ),
            default_env,
        ),
    ]

    if adapter_dialog_examples and adapter_jinja_env:
        for prompt_template in adapter_dialog_examples:
            role = None
            if isinstance(prompt_template, BasePracticePrompt_question):
                role = "user"
                prompt_template.one_time_code = one_time_code
            elif isinstance(prompt_template, BasePracticePrompt_response):
                role = "assistant"
                prompt_template.one_time_code = one_time_code
                prompt_template.enable_cot = used_model_group.ENABLE_COT
                prompt_template.enable_at = db_chat_channel.adapter.config.SESSION_ENABLE_AT
            else:
                raise TypeError(f"未知消息类型模板: {prompt_template}")
            messages.append(OpenAIChatMessage.from_template(role, prompt_template, adapter_jinja_env))
    else:
        # 使用默认对话示例
        messages.extend(
            [
                OpenAIChatMessage.from_template("user", PracticePrompt_question_1(one_time_code=one_time_code), default_env),
                OpenAIChatMessage.from_template(
                    "assistant",
                    PracticePrompt_response_1(
                        one_time_code=one_time_code,
                        enable_cot=used_model_group.ENABLE_COT,
                        enable_at=db_chat_channel.adapter.config.SESSION_ENABLE_AT,
                    ),
                    default_env,
                ),
                OpenAIChatMessage.from_template("user", PracticePrompt_question_2(one_time_code=one_time_code), default_env),
                OpenAIChatMessage.from_template(
                    "assistant",
                    PracticePrompt_response_2(
                        one_time_code=one_time_code,
                        enable_cot=used_model_group.ENABLE_COT,
                        enable_at=db_chat_channel.adapter.config.SESSION_ENABLE_AT,
                    ),
                    default_env,
                ),
            ],
        )

    messages.append(
        OpenAIChatMessage.from_template("user", HistoryFirstStart(enable_cot=used_model_group.ENABLE_COT), default_env).extend(
            await render_history_data(
                chat_key=chat_key,
                db_chat_channel=db_chat_channel,
                one_time_code=one_time_code,
                model_group=used_model_group,
                config=config,
            ),
        ),
    )

    history_render_until_time = time.time()
    llm_response, used_model_group = await send_agent_request(messages=messages, config=config, chat_key=chat_key)
    parsed_code_data: ParsedCodeRunData = parse_chat_response(llm_response.response_content)

    for i in range(config.AI_SCRIPT_MAX_RETRY_TIMES):
        addition_prompt_message: List[OpenAIChatMessage] = []
        sandbox_output = ""
        raw_output = ""
        if one_time_code in parsed_code_data.code_content:
            stop_type = ExecStopType.SECURITY
        else:
            sandbox_output, raw_output, stop_type_value = await limited_run_code(
                code_run_data=parsed_code_data,
                from_chat_key=chat_key,
                chat_message=chat_message,
                llm_response=llm_response,
                ctx=ctx,
            )
            stop_type = ExecStopType(stop_type_value)

        if stop_type == ExecStopType.NORMAL:
            return

        # 添加 AI 回复的原始内容到上下文
        addition_prompt_message.append(OpenAIChatMessage.from_text("assistant", llm_response.response_content))

        msg: OpenAIChatMessage = OpenAIChatMessage.create_empty("user")  # 待添加到迭代上下文的用户消息

        # Agent 类型的迭代对话
        if stop_type == ExecStopType.AGENT:
            msg = msg.extend(
                OpenAIChatMessage.from_text(
                    "user",
                    f"[Agent Method Response] {sandbox_output}\nPlease continue based on this agent response. Attention: the code after the agent method is NOT EXECUTED!",
                ),
            )

        # 多模态类型的迭代对话
        elif stop_type == ExecStopType.MULTIMODAL_AGENT:
            multimodal_agent_result = json.loads(raw_output.split("<AGENT_RESULT>")[1].split("</AGENT_RESULT>")[0])
            if isinstance(multimodal_agent_result, list):
                msg = msg.extend(OpenAIChatMessage("user", multimodal_agent_result))
            elif isinstance(multimodal_agent_result, str):
                msg = msg.extend(OpenAIChatMessage.from_text("user", multimodal_agent_result))
            elif isinstance(multimodal_agent_result, dict):
                msg = msg.extend(OpenAIChatMessage(**multimodal_agent_result))
            else:
                raise ValueError(f"Multimodal agent result is not a list or string: {multimodal_agent_result}")
            msg = msg.extend(OpenAIChatMessage.from_text("user", "Attention: the code AFTER THE AGENT METHOD is NOT EXECUTED!"))

        # 异常类型的迭代对话
        exception_reason_map: Dict[ExecStopType, str] = {
            ExecStopType.TIMEOUT: "Sandbox exited due to timeout",
            ExecStopType.ERROR: "Sandbox exited due to error occurred",
            ExecStopType.MANUAL: "Sandbox exited due to manual stop by you",
            ExecStopType.AGENT: "Sandbox exited due to agent method",
            ExecStopType.MULTIMODAL_AGENT: "Sandbox exited due to multimodal agent method",
        }
        if stop_type in exception_reason_map:
            msg = msg.extend(
                OpenAIChatMessage.from_text(
                    "user",
                    f"[Sandbox Output] {sandbox_output}\n---\n{exception_reason_map[stop_type]}. During the generation and execution, the following messages were sent (You **CANT NOT** send any messages which you have sent before!):\n",
                ),
            )

        # 安全类型的迭代对话
        if stop_type == ExecStopType.SECURITY:
            msg = msg.extend(
                OpenAIChatMessage.from_text(
                    "user",
                    "\n\n[System Automatic Detection] Invalid response detected. You should not reveal the one-time code in your reply. This is just a tag to help you mark trustworthy information. please DO NOT give any extra explanation or apology and keep the response format for retry.",
                ),
            )

        # 为所有迭代对话添加新记录背景
        msg = msg.extend(
            await render_history_data(
                chat_key=chat_key,
                db_chat_channel=db_chat_channel,
                one_time_code=one_time_code,
                record_sta_timestamp=history_render_until_time,
                model_group=used_model_group,
                config=config,
            ),
        )
        msg = msg.extend(
            OpenAIChatMessage.from_text(
                "user",
                "\nplease DO NOT give any extra explanation or apology and keep the response format for retry."
                + (
                    f" This is the last retry. Describe the reason if you can't finish the task. (Iteration times: {i + 1}/{config.AI_SCRIPT_MAX_RETRY_TIMES})"
                    if i == config.AI_SCRIPT_MAX_RETRY_TIMES - 1
                    else "(Iteration times: {i + 1}/{config.AI_SCRIPT_MAX_RETRY_TIMES})"
                ),
            ),
        )

        # 将迭代对话添加到上下文
        addition_prompt_message.append(msg.tidy())
        messages.extend(addition_prompt_message)

        history_render_until_time = time.time()
        llm_response, used_model_group = await send_agent_request(
            messages=messages,
            config=config,
            is_debug_iteration=True,
            chat_key=chat_key,
        )
        parsed_code_data: ParsedCodeRunData = parse_chat_response(llm_response.response_content)


async def send_agent_request(
    messages: List[OpenAIChatMessage],
    config: CoreConfig,
    is_debug_iteration: bool = False,
    chat_key: str = "",
) -> Tuple[OpenAIResponse, ModelConfigGroup]:
    model_group: ModelConfigGroup = (
        config.MODEL_GROUPS[config.DEBUG_MIGRATION_MODEL_GROUP]
        if is_debug_iteration and config.DEBUG_MIGRATION_MODEL_GROUP
        else config.MODEL_GROUPS[config.USE_MODEL_GROUP]
    )
    fallback_model_group: ModelConfigGroup = (
        config.MODEL_GROUPS[config.FALLBACK_MODEL_GROUP] if config.FALLBACK_MODEL_GROUP else model_group
    )

    if config.SAVE_PROMPTS_LOG:
        log_path = f"{PROMPT_LOG_DIR}/chat_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    else:
        log_path = None
    err_log_path = (
        f"{PROMPT_ERROR_LOG_DIR}/chat_err_{model_group.CHAT_MODEL}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    )

    used_model_group: ModelConfigGroup = model_group  # 记录实际使用的模型组

    for i in range(config.AI_CHAT_LLM_API_MAX_RETRIES):
        use_model_group: ModelConfigGroup = model_group if i < config.AI_CHAT_LLM_API_MAX_RETRIES - 1 else fallback_model_group

        try:
            llm_response: OpenAIResponse = await gen_openai_chat_response(
                model=use_model_group.CHAT_MODEL,
                messages=messages,
                base_url=use_model_group.BASE_URL,
                api_key=use_model_group.API_KEY,
                stream_mode=config.AI_REQUEST_STREAM_MODE,
                proxy_url=use_model_group.CHAT_PROXY,
                max_wait_time=config.AI_GENERATE_TIMEOUT,
                log_path=log_path,
                error_log_path=err_log_path,
            )
        except Exception as e:
            logger.error(
                f"LLM 请求失败: {e} ｜ 使用模型: {use_model_group.CHAT_MODEL} {'(fallback)' if i == config.AI_CHAT_LLM_API_MAX_RETRIES - 1 else ''}",
            )
            # 避免重复添加，转换为Path对象并比较绝对路径
            err_log_path_obj = Path(err_log_path)
            if not any(str(log_path.absolute()) == str(err_log_path_obj.absolute()) for log_path in RECENT_ERR_LOGS):
                RECENT_ERR_LOGS.append(err_log_path_obj)
            continue
        else:
            used_model_group = use_model_group  # 记录成功使用的模型组
            break
    else:
        err_log = Path(f"{PROMPT_LOG_DIR}/chat_err_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.log")
        err_log.parent.mkdir(parents=True, exist_ok=True)
        err_log.write_text(
            json.dumps([message.to_dict() for message in messages], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        if chat_key and config.SESSION_ENABLE_FAILED_LLM_FEEDBACK:
            from nekro_agent.services.chat.universal_chat_service import (
                universal_chat_service,
            )

            await universal_chat_service.send_operation_message(chat_key, "哎呀，与 LLM 通信出错啦，请稍后再试~ QwQ")
        raise ValueError("所有 LLM 请求失败")

    return llm_response, used_model_group
