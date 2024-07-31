import time
from typing import List, Union

from nekro_agent.core import config, logger
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
    convert_agent_message_to_prompt,
)
from nekro_agent.schemas.chat_message import ChatType


async def push_bot_chat_message(chat_key: str, agent_messages: Union[str, List[AgentMessageSegment]]):
    """推送机器人消息"""

    logger.info(f"Pushing Bot Message To Chat {chat_key}")
    if isinstance(agent_messages, str):
        agent_messages = [AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=agent_messages)]

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


async def push_system_message(chat_key: str, agent_messages: Union[str, List[AgentMessageSegment]]):
    """推送系统消息"""

    logger.info(f"Pushing System Message To Chat {chat_key}")
    if isinstance(agent_messages, str):
        agent_messages = [AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=agent_messages)]

    send_timestamp = int(time.time())
    content_text = convert_agent_message_to_prompt(agent_messages)

    DBChatMessage.add(
        data={
            DBChatMessage.sender_id: -1,
            DBChatMessage.sender_bind_qq: "0",
            DBChatMessage.sender_real_nickname: "SYSTEM",
            DBChatMessage.sender_nickname: "SYSTEM",
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
