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

    await DBChatMessage.create(
        message_id="",
        sender_id=-1,
        sender_bind_qq=config.BOT_QQ or "0",
        sender_real_nickname=config.AI_CHAT_PRESET_NAME,
        sender_nickname=config.AI_CHAT_PRESET_NAME,
        is_tome=0,
        is_recalled=False,
        chat_key=chat_key,
        chat_type=ChatType.from_chat_key(chat_key).value,
        content_text=content_text,
        content_data=[],
        raw_cq_code="",
        ext_data={},
        send_timestamp=send_timestamp,
    )


async def push_system_message(chat_key: str, agent_messages: Union[str, List[AgentMessageSegment]]):
    """推送系统消息"""

    logger.info(f"Pushing System Message To Chat {chat_key}")
    if isinstance(agent_messages, str):
        agent_messages = [AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=agent_messages)]

    send_timestamp = int(time.time())
    content_text = convert_agent_message_to_prompt(agent_messages)

    await DBChatMessage.create(
        message_id="",
        sender_id=-1,
        sender_bind_qq="0",
        sender_real_nickname="SYSTEM",
        sender_nickname="SYSTEM",
        is_tome=0,
        is_recalled=False,
        chat_key=chat_key,
        chat_type=ChatType.from_chat_key(chat_key).value,
        content_text=content_text,
        content_data=[],
        raw_cq_code="",
        ext_data={},
        send_timestamp=send_timestamp,
    )
