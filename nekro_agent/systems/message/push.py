import time
from typing import List

from nekro_agent.core import config, logger
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    convert_agent_message_to_prompt,
)
from nekro_agent.schemas.chat_message import ChatMessage, ChatType
from nekro_agent.services.agents.chat_agent import agent_run


async def push_human_chat_message(message: ChatMessage):
    """推送聊天消息"""

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

    if config.AI_CHAT_PRESET_NAME in message.content_text and message.sender_bind_qq in config.SUPER_USERS:
        logger.info(f"Message From {message.sender_real_nickname} is ToMe, Running Chat Agent...")
        await agent_run(message)


async def push_bot_chat_message(chat_key: str, agent_messages: List[AgentMessageSegment]):
    """推送机器人消息"""

    logger.info(f"Pushing Bot Message To Chat {chat_key}")

    send_timestamp = int(time.time())
    content_text = convert_agent_message_to_prompt(agent_messages)

    DBChatMessage.add(
        data={
            DBChatMessage.sender_id: -1,
            DBChatMessage.sender_bind_qq: config.BOT_QQ or "0",
            DBChatMessage.sender_real_nickname: config.AI_CHAT_PRESET_NAME,
            DBChatMessage.sender_nickname: config.AI_CHAT_PRESET_NAME,
            DBChatMessage.is_tome: 0,
            DBChatMessage.is_recalled: False,
            DBChatMessage.chat_key: chat_key,
            DBChatMessage.chat_type: ChatType.from_chat_key(chat_key).value,
            DBChatMessage.content_text: content_text,
            DBChatMessage.content_data: [],
            DBChatMessage.raw_cq_code: "",
            DBChatMessage.ext_data: {},
            DBChatMessage.send_timestamp: send_timestamp,
        },
    )
