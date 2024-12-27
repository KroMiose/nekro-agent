import asyncio
import datetime
import re
import time
from asyncio import Task, create_task, sleep
from contextlib import suppress
from typing import Dict

from nekro_agent.core import config, logger
from nekro_agent.libs.miose_llm.exceptions import ResolveError
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.schemas.chat_message import ChatMessage
from nekro_agent.services.agents.chat_agent import agent_run
from nekro_agent.tools.common_util import check_content_trigger, random_chat_check


def message_validation_check(message: ChatMessage) -> bool:
    """消息校验"""

    plaint_text = message.content_text.strip().replace(" ", "").lower()

    # 检查伪造消息
    if re.match(r"<.{4,12}\|messageseparator>", plaint_text):
        return False
    if re.match(r"<.{4,12}\|messageseperator>", plaint_text):
        return False

    if "message" in plaint_text and "(qq:" in plaint_text:
        return False
    if "from_qq:" in plaint_text:  # noqa: SIM103
        return False

    return True


# 全局状态追踪
running_tasks: Dict[str, Task] = {}  # 记录每个会话正在执行的agent任务
debounce_timers: Dict[str, float] = {}  # 记录每个会话的防抖计时器
pending_messages: Dict[str, ChatMessage] = {}  # 记录每个会话待处理的最新消息


async def push_human_chat_message(message: ChatMessage):
    """推送聊天消息"""
    global running_chat_task_map, running_chat_task_throttle_map

    logger.info(f'Message Received: "{message.content_text}" From {message.sender_real_nickname}')

    if not message_validation_check(message):
        logger.warning("消息校验失败，跳过本次处理...")
        return

    content_data = [o.model_dump() for o in message.content_data]
    current_time: float = time.time()

    # 添加聊天记录
    await DBChatMessage.create(
        message_id=message.message_id,
        sender_id=message.sender_id,
        sender_bind_qq=message.sender_bind_qq,
        sender_real_nickname=message.sender_real_nickname,
        sender_nickname=message.sender_nickname,
        is_tome=message.is_tome,
        is_recalled=message.is_recalled,
        chat_key=message.chat_key,
        chat_type=message.chat_type,
        content_text=message.content_text,
        content_data=content_data,
        raw_cq_code=message.raw_cq_code,
        ext_data=message.ext_data,
        send_timestamp=int(current_time),  # 使用处理后的时间戳
    )

    # 检查是否需要触发回复
    should_trigger = (
        config.AI_CHAT_PRESET_NAME in message.content_text
        or message.is_tome
        or random_chat_check()
        or check_content_trigger(message.content_text)
    )

    if should_trigger:
        db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=message.chat_key)
        if not db_chat_channel.is_active:
            logger.info(f"聊天频道 {message.chat_key} 已被禁用，跳过本次处理...")
            return

        await schedule_agent_task(message)


async def schedule_agent_task(message: ChatMessage):
    """调度agent任务，实现防抖和任务控制"""
    chat_key = message.chat_key
    current_time = time.time()

    # 更新待处理消息和防抖计时器
    pending_messages[chat_key] = message
    debounce_timers[chat_key] = current_time

    # 如果已有正在执行的任务，直接返回
    if chat_key in running_tasks and not running_tasks[chat_key].done():
        return

    # 等待防抖时间
    await sleep(config.AI_DEBOUNCE_WAIT_SECONDS)

    # 检查是否在防抖期间有新消息
    if current_time != debounce_timers[chat_key]:
        return

    # 获取最终要处理的消息
    final_message = pending_messages.pop(chat_key, None)
    if not final_message:
        return

    # 创建新的agent任务
    task = create_task(agent_task(final_message))
    running_tasks[chat_key] = task


async def agent_task(message: ChatMessage):
    """执行agent任务"""
    chat_key = message.chat_key

    try:
        logger.info(f"Message From {message.sender_real_nickname} is ToMe, Running Chat Agent...")
        for i in range(3):
            try:
                await agent_run(message)
            except ResolveError as e:
                logger.error(f"Resolve Error, Retrying {i+1}/3...")
                if "list index out of range" in str(e) and i > 0:
                    logger.error("Resolve Error: 列表索引越界，可能由于目标站点返回空响应引起")
                    break
            else:
                break
        else:
            logger.error("Failed to Run Chat Agent.")
    finally:
        # 清理任务状态
        if chat_key in running_tasks:
            del running_tasks[chat_key]

        final_message = pending_messages.pop(chat_key, None)
        debounce_timers.pop(chat_key, None)

        # 如果有待处理消息，创建新的任务处理最后一条消息
        if final_message:
            new_task = create_task(agent_task(final_message))
            running_tasks[chat_key] = new_task
