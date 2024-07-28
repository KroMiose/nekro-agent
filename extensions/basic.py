from typing import List

from nekro_agent.core import logger
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
)
from nekro_agent.services.chat import chat_service
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.systems.message.push import push_bot_chat_message
from nekro_agent.tools.collector import agent_collector

__meta__ = ExtMetaData(
    name="basic",
    description="Nekro-Agent 交互基础工具集",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@agent_collector.mount_method()
async def send_msg_text(chat_key: str, message: str) -> bool:
    """发送聊天消息

    Args:
        chat_key (str): 会话标识
        message (str): 消息内容

    Returns:
        bool: 是否发送成功
    """
    try:
        message_ = [AgentMessageSegment(content=message)]
        await chat_service.send_agent_message(chat_key, message_)
        await push_bot_chat_message(chat_key, message_)
    except Exception as e:
        logger.exception(f"Error sending message to chat: {e}")
        return False
    else:
        return True


@agent_collector.mount_method()
async def send_msg_img(chat_key: str, file_path: str) -> bool:
    """发送聊天消息

    Args:
        chat_key (str): 会话标识
        file_path (str): 图片路径或 URL

    Returns:
        bool: 是否发送成功
    """
    try:
        message_ = [AgentMessageSegment(type=AgentMessageSegmentType.FILE, content=file_path)]
        await chat_service.send_agent_message(chat_key, message_)
        await push_bot_chat_message(chat_key, message_)
    except Exception as e:
        logger.exception(f"Error sending message to chat: {e}")
        return False
    else:
        return True
