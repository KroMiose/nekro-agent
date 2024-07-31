from pathlib import Path
from typing import List, Optional, Union

from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment

from nekro_agent.core.bot import get_bot
from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
)
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.systems.message.push_bot_msg import push_bot_chat_message
from nekro_agent.tools.common_util import download_file


class ChatService:
    def __init__(self):
        pass

    async def send_agent_message(
        self,
        chat_key: str,
        messages: Union[List[AgentMessageSegment], str],
        ctx: Optional[AgentCtx] = None,
        record: bool = False,
    ):
        """发送机器人消息

        Args:
            chat_key (str): 聊天的唯一标识
            messages (Union[List[AgentMessageSegment], str]): 机器人消息
            ctx (Optional[AgentCtx], optional): 机器人上下文. Defaults to None.
            record (bool, optional): 是否记录聊天记录. Defaults to False.

        Raises:
            ValueError: 聊天类型错误
        """
        message = Message()

        if isinstance(messages, str):
            messages = [AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=messages)]

        for agent_message in messages:
            content = agent_message.content
            if agent_message.type == AgentMessageSegmentType.TEXT.value:
                message.append(content)
                logger.info(f"Sending agent message: {content}")
            elif agent_message.type == AgentMessageSegmentType.FILE.value:
                if content.startswith("/app/uploads/"):
                    content = content[len("/app/") :]
                if content.startswith("app/uploads/"):
                    content = content[len("app/") :]
                if content.startswith("uploads/"):
                    real_path = Path(config.USER_UPLOAD_DIR) / content[len("uploads/") :]
                    logger.info(f"Sending agent file: {real_path}")
                    message.append(MessageSegment.image(file=real_path.read_bytes(), type_="image"))

                if not ctx:
                    raise ValueError("Cannot send file without agent context")

                if content.startswith("/app/shared/"):
                    content = content[len("/app/") :]
                if content.startswith("app/shared/"):
                    content = content[len("app/") :]
                if content.startswith("shared/"):
                    real_path = Path(config.SANDBOX_SHARED_HOST_DIR) / ctx.container_key / content[len("shared/") :]
                    logger.info(f"Sending agent file: {real_path}")
                    message.append(MessageSegment.image(file=real_path.read_bytes(), type_="image"))
                elif content.startswith(("http://", "https://")):
                    file_path, _ = await download_file(content)
                    message.append(MessageSegment.image(file=Path(file_path).read_bytes()))
                else:
                    message.append(MessageSegment.text(f"Invalid file path: {content}"))
                    continue
            else:
                raise ValueError(f"Invalid agent message type: {agent_message.type}")

        await self.send_message(chat_key, message)
        if record:
            await push_bot_chat_message(chat_key, messages)

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
