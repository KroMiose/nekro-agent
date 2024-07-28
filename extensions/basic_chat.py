from typing import List

from fastapi import APIRouter

from nekro_agent.core.logger import logger
from nekro_agent.schemas.agent_message import AgentMessageSegment
from nekro_agent.services.chat import chat_service
from nekro_agent.systems.message.push import push_bot_chat_message
from nekro_agent.tools.doc_collector import agent_method_collector

router = APIRouter(prefix="/chat", tags=["Tools"])


@agent_method_collector.fastapi_interface()
async def send_msg(chat_key: str, message: List[AgentMessageSegment]) -> bool:
    """发送聊天消息

    Args:
        chat_key (str): 聊天的唯一标识符
        message (List[AgentMessageSegment]): 消息内容

    Returns:
        bool: 是否发送成功
    """
    try:
        await chat_service.send_agent_message(chat_key, message)
        await push_bot_chat_message(chat_key, message)
    except Exception as e:
        logger.error(f"Error sending message to chat: {e}")
        return False
    else:
        return True
