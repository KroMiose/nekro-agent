from typing import List

from fastapi import APIRouter

from nekro_agent.core.logger import logger
from nekro_agent.schemas.agent_message import AgentMessageSegment
from nekro_agent.services.chat import chat_service

router = APIRouter(prefix="/chat", tags=["Tools"])


@router.post("/send_msg", summary="Send a message to a chat")
async def send_msg(chat_key: str, message: List[AgentMessageSegment]) -> bool:
    """发送聊天消息

    向指定的聊天发送消息，私聊的 chat_key 格式为 private_{user_qq}

    Api: POST /chat/send_msg

    Query:
        chat_key: 会话 ID

    Body:
        message_segments(body): 消息片段

    Returns:
        bool: 是否发送成功

    Usage:
        requests.post(
            f"{CHAT_API}/chat/send_msg?chat_key=group_123456",
            json=[
                {"type": "text", "content": "Hello!"},
                {"type": "file", "content": "shared/output.txt"},
                {"type": "file", "content": "https://example.com/image.jpg"},
            ]
        )
    """
    try:
        await chat_service.send_agent_message(chat_key, message)
    except Exception as e:
        logger.error(f"Error sending message to chat: {e}")
        return False
    else:
        return True
