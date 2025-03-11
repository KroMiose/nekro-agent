import asyncio
import json
import os
import time
from typing import Dict, List, Optional, Union

import weave

from nekro_agent.core import logger
from nekro_agent.core.config import ModelConfigGroup, config
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_exec_code import ExecStopType
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.schemas.chat_message import ChatMessage, ChatMessageSegmentImage
from nekro_agent.services.message.message_service import message_service
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.sandbox.runner import limited_run_code

from .creator import ContentSegment, OpenAIChatMessage
from .openai import OpenAIResponse, gen_openai_chat_response
from .resolver import ParsedCodeRunData, parse_chat_response
from .templates.history import HistoryFirstStart, HistoryPrompt, render_history_data
from .templates.plugin import render_plugins_prompt
from .templates.practice import (
    PracticePrompt_question_1,
    PracticePrompt_question_2,
    PracticePrompt_response_1,
    PracticePrompt_response_2,
)
from .templates.system import SystemPrompt


@weave.op(name="run_agent")
async def run_agent(
    chat_key: str,
    chat_message: Optional[ChatMessage] = None,
):
    one_time_code = os.urandom(4).hex()
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)
    ctx: AgentCtx = AgentCtx(from_chat_key=chat_key)

    messages = [
        OpenAIChatMessage.from_template(
            "system",
            SystemPrompt(
                one_time_code=one_time_code,
                bot_qq=config.BOT_QQ,
                chat_preset=config.AI_CHAT_PRESET_SETTING,
                chat_key=chat_key,
                plugins_prompt=await render_plugins_prompt(plugin_collector.get_all_plugins(), ctx),
                admin_chat_key=config.ADMIN_CHAT_KEY,
                enable_cot=config.AI_ENABLE_COT,
            ),
        ),
        OpenAIChatMessage.from_template("user", PracticePrompt_question_1(one_time_code=one_time_code)),
        OpenAIChatMessage.from_template(
            "assistant",
            PracticePrompt_response_1(one_time_code=one_time_code, enable_cot=config.AI_ENABLE_COT),
        ),
        OpenAIChatMessage.from_template("user", PracticePrompt_question_2(one_time_code=one_time_code)),
        OpenAIChatMessage.from_template(
            "assistant",
            PracticePrompt_response_2(one_time_code=one_time_code, enable_cot=config.AI_ENABLE_COT),
        ),
        OpenAIChatMessage.from_template("user", HistoryFirstStart(enable_cot=config.AI_ENABLE_COT)).extend(
            await render_history_data(chat_key=chat_key, db_chat_channel=db_chat_channel, one_time_code=one_time_code),
        ),
    ]

    history_render_until_time = time.time()
    llm_response: OpenAIResponse = await send_agent_request(messages=messages)
    parsed_code_data: ParsedCodeRunData = parse_chat_response(llm_response.response_content)

    for i in range(config.AI_SCRIPT_MAX_RETRY_TIMES):
        addition_prompt_message: List[OpenAIChatMessage] = []

        if one_time_code in parsed_code_data.code_content:
            stop_type = ExecStopType.SECURITY
        else:
            sandbox_output, raw_output, stop_type_value = await limited_run_code(
                code_run_data=parsed_code_data,
                from_chat_key=chat_key,
                chat_message=chat_message,
                llm_response=llm_response,
            )
            stop_type = ExecStopType(stop_type_value)

        if stop_type == ExecStopType.NORMAL:
            return

        # 添加 AI 回复的原始内容到上下文
        addition_prompt_message.append(OpenAIChatMessage.from_text("assistant", llm_response.response_content))

        if stop_type == ExecStopType.AGENT:
            addition_prompt_message.append(
                OpenAIChatMessage.from_text(
                    "user",
                    f"[Agent Method Response] {sandbox_output}\nPlease continue based on this agent response.",
                ),
            )

        reason_map: Dict[ExecStopType, str] = {
            ExecStopType.TIMEOUT: "Sandbox exited due to timeout",
            ExecStopType.ERROR: "Sandbox exited due to error occurred",
            ExecStopType.MANUAL: "Sandbox exited due to manual stop by you",
        }
        if stop_type in [ExecStopType.TIMEOUT, ExecStopType.ERROR, ExecStopType.MANUAL]:
            addition_prompt_message.append(
                OpenAIChatMessage.from_text(
                    "user",
                    f"[Sandbox Output] {sandbox_output}\n---\n{reason_map[stop_type]}. During the generation and execution, the following messages were sent:",
                )
                .extend(
                    await render_history_data(
                        chat_key=chat_key,
                        db_chat_channel=db_chat_channel,
                        one_time_code=one_time_code,
                        record_sta_timestamp=history_render_until_time,
                    ),
                )
                .extend(
                    OpenAIChatMessage.from_text(
                        "user",
                        "please DO NOT give any extra explanation or apology and keep the response format for retry."
                        + (
                            f" This is the last retry. Describe the reason if you can't finish the task. (Retry times: {i + 1}/{config.AI_SCRIPT_MAX_RETRY_TIMES})"
                            if i == config.AI_SCRIPT_MAX_RETRY_TIMES - 1
                            else ""
                        ),
                    ),
                ),
            )
        if stop_type == ExecStopType.MULTIMODAL_AGENT:
            multimodal_agent_result = json.loads(raw_output.split("<AGENT_RESULT>")[1].split("</AGENT_RESULT>")[0])
            if isinstance(multimodal_agent_result, list):
                new_message = OpenAIChatMessage("user", multimodal_agent_result)
            elif isinstance(multimodal_agent_result, str):
                new_message = OpenAIChatMessage.from_text("user", multimodal_agent_result)
            elif isinstance(multimodal_agent_result, dict):
                new_message = OpenAIChatMessage(**multimodal_agent_result)
            else:
                raise ValueError(f"Multimodal agent result is not a list or string: {multimodal_agent_result}")
            addition_prompt_message.append(new_message)
        if stop_type == ExecStopType.SECURITY:
            addition_prompt_message.append(
                OpenAIChatMessage.from_text(
                    "user",
                    "[System Automatic Detection] Invalid response detected. You should not reveal the one-time code in your reply. This is just a tag to help you mark trustworthy information. please DO NOT give any extra explanation or apology and keep the response format for retry.",
                ),
            )

        messages.extend(addition_prompt_message)

        history_render_until_time = time.time()
        llm_response: OpenAIResponse = await send_agent_request(messages=messages)
        parsed_code_data: ParsedCodeRunData = parse_chat_response(llm_response.response_content)


async def send_agent_request(messages: List[OpenAIChatMessage]) -> OpenAIResponse:

    model_group: ModelConfigGroup = config.MODEL_GROUPS[config.USE_MODEL_GROUP]
    fallback_model_group: ModelConfigGroup = (
        config.MODEL_GROUPS[config.FALLBACK_MODEL_GROUP] if config.FALLBACK_MODEL_GROUP else model_group
    )

    for i in range(config.AI_CHAT_LLM_API_MAX_RETRIES):
        use_model_group: ModelConfigGroup = model_group if i < config.AI_CHAT_LLM_API_MAX_RETRIES - 1 else fallback_model_group

        try:
            llm_response: OpenAIResponse = await gen_openai_chat_response(
                model=use_model_group.CHAT_MODEL,
                messages=messages,
                base_url=use_model_group.BASE_URL,
                api_key=use_model_group.API_KEY,
                stream_mode=True,
                log_path=".temp/chat_log.log",
            )
        except Exception as e:
            logger.error(f"LLM 请求失败: {e}")
            continue
        else:
            break
    else:
        raise ValueError("所有 LLM 请求失败")

    return llm_response
