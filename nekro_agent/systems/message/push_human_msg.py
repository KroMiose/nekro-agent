import asyncio
import re
import time
from contextlib import suppress
from typing import Dict

from miose_toolkit_llm.exceptions import ResolveError

from nekro_agent.core import config, logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.schemas.chat_message import ChatMessage
from nekro_agent.services.agents.chat_agent import agent_run
from nekro_agent.tools.common_util import check_content_trigger, random_chat_check

running_chat_task_map: Dict[str, asyncio.Task] = {}
running_chat_task_throttle_map: Dict[str, float] = {}


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


async def push_human_chat_message(message: ChatMessage):
    """推送聊天消息"""
    global running_chat_task_map, running_chat_task_throttle_map

    logger.info(f'Message Received: "{message.content_text}" From {message.sender_real_nickname}')

    if not message_validation_check(message):
        logger.warning("消息校验失败，跳过本次处理...")
        return

    content_data = [o.model_dump() for o in message.content_data]

    # 添加聊天记录
    DBChatMessage.add(
        data={
            DBChatMessage.sender_id: message.sender_id,
            DBChatMessage.sender_bind_qq: message.sender_bind_qq,
            DBChatMessage.sender_real_nickname: message.sender_real_nickname,
            DBChatMessage.sender_nickname: message.sender_nickname,
            DBChatMessage.is_tome: message.is_tome,
            DBChatMessage.is_recalled: message.is_recalled,
            DBChatMessage.chat_key: message.chat_key,
            DBChatMessage.chat_type: message.chat_type,
            DBChatMessage.content_text: message.content_text,
            DBChatMessage.content_data: content_data,
            DBChatMessage.raw_cq_code: message.raw_cq_code,
            DBChatMessage.ext_data: message.ext_data,
            DBChatMessage.send_timestamp: message.send_timestamp,
        },
    )

    if (
        config.AI_CHAT_PRESET_NAME in message.content_text  # 提及人设名
        or message.is_tome  # 引用 / @ 回复
        or random_chat_check()  # 随机触发聊天
        or check_content_trigger(message.content_text)  # 触发词
    ):
        db_chat_channel: DBChatChannel = DBChatChannel.get_channel(chat_key=message.chat_key)
        if not db_chat_channel.is_active:
            logger.info(f"聊天频道 {message.chat_key} 已被禁用，跳过本次处理...")
            return

        # 第一层节流控制 根据触发时间是否变化判断连续触发
        current_time = time.time()
        if message.chat_key in running_chat_task_throttle_map:
            running_chat_task_throttle_map[message.chat_key] = current_time
            await asyncio.sleep(config.AI_GENERATE_THROTTLE_SECONDS)
            if running_chat_task_throttle_map[message.chat_key] != current_time:
                logger.warning("检测到高频触发消息，节流控制生效中，跳过本次处理...")
                return

        if message.chat_key in running_chat_task_map and running_chat_task_throttle_map.get(message.chat_key):
            time_diff: float = current_time - running_chat_task_throttle_map[message.chat_key]
            if 5 < time_diff < 60:
                logger.warning("检测到长响应，跳过本次触发...")
                return
            logger.info(f"检测到正在进行的聊天任务: {message.chat_key} 取消之前的任务")
            with suppress(Exception):
                running_chat_task_map[message.chat_key].cancel()

        running_chat_task_map[message.chat_key] = asyncio.create_task(agent_task(message))


async def agent_task(message: ChatMessage):
    global running_chat_task_map, running_chat_task_throttle_map
    logger.info(f"Message From {message.sender_real_nickname} is ToMe, Running Chat Agent...")
    for i in range(3):
        try:
            await agent_run(message)
        except ResolveError as e:
            logger.error(f"Resolve Error, Retrying {i+1}/3...")
            if "list index out of range" in str(e) and i > 0:
                logger.error("Resolve Error: 列表索引越界，可能由于目标站点返回空响应引起")
                break  # 请求被拒绝了，不重试
        else:
            break
    else:
        logger.error("Failed to Run Chat Agent.")

    del running_chat_task_map[message.chat_key]
    with suppress(KeyError):
        del running_chat_task_throttle_map[message.chat_key]
