from fastapi import APIRouter

from nekro_agent.core.logger import logger
from nekro_agent.services.chat import chat_service

router = APIRouter(prefix="/chat", tags=["Tools"])


@router.post("/send_msg_text", summary="Send a message to a chat")
async def send_message_text(chat_key: str, message: str) -> str:
    try:
        await chat_service.send_message(chat_key, message)
    except Exception as e:
        logger.error(f"Error sending message to chat: {e}")
        return "Error sending message to chat"
    else:
        return "Message sent successfully"
