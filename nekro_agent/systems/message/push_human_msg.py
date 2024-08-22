import asyncio
import time
from typing import Dict

from miose_toolkit_llm.exceptions import ResolveError

from nekro_agent.core import config, logger
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.schemas.chat_message import ChatMessage
from nekro_agent.services.agents.chat_agent import agent_run

running_chat_task_map: Dict[str, asyncio.Task] = {}
running_chat_task_throttle_map: Dict[str, float] = {}


async def push_human_chat_message(message: ChatMessage):
    """推送聊天消息"""
    global running_chat_task_map, running_chat_task_throttle_map

    logger.info(f'Message Received: "{message.content_text}" From {message.sender_real_nickname}')

    content_data = [o.model_dump() for o in message.content_data]

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

    if config.AI_CHAT_PRESET_NAME in message.content_text or message.is_tome:
        if message.chat_key in running_chat_task_throttle_map:
            current_time = time.time()
            running_chat_task_throttle_map[message.chat_key] = current_time
            await asyncio.sleep(config.AI_GENERATE_THROTTLE_SECONDS)
            if running_chat_task_throttle_map[message.chat_key] != current_time:
                logger.warning("检测到高频触发消息，节流控制生效中，跳过本次处理...")
                return
        if message.chat_key in running_chat_task_map:
            logger.info(f"检测到正在进行的聊天任务: {message.chat_key} 取消之前的任务")
            running_chat_task_map[message.chat_key].cancel()
        running_chat_task_map[message.chat_key] = asyncio.create_task(agent_task(message))


async def agent_task(message: ChatMessage):
    global running_chat_task_map
    logger.info(f"Message From {message.sender_real_nickname} is ToMe, Running Chat Agent...")
    for i in range(3):
        try:
            await agent_run(message)
        except ResolveError:
            logger.error(f"Resolve Error, Retrying {i+1}/3...")
        else:
            break
    else:
        logger.error("Failed to Run Chat Agent.")

    del running_chat_task_map[message.chat_key]
