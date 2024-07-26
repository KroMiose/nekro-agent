from typing import Union

from nonebot.adapters.onebot.v11 import Bot, Message

from nekro_agent.core.bot import get_bot
from nekro_agent.schemas.chat_message import ChatType


class ChatService:
    def __init__(self):
        pass

    async def send_message(self, chat_key: str, message: Union[str, Message]):
        bot: Bot = get_bot()

        try:
            chat_type, chat_id = chat_key.split("_")
        except ValueError as e:
            raise ValueError(f"Invalid chat key: {chat_key}") from e

        chat_type = ChatType(chat_type)
        chat_id = int(chat_id)

        if chat_type is ChatType.GROUP:
            await bot.send_group_msg(group_id=chat_id, message=message)
        elif chat_type is ChatType.PRIVATE:
            await bot.send_private_msg(user_id=chat_id, message=message)
        else:
            raise ValueError("Invalid chat type")


chat_service = ChatService()
