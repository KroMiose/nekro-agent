from pathlib import Path
from typing import List, Optional, Union

from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from pydantic import BaseModel

from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.bot import get_bot
from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import SANDBOX_SHARED_HOST_DIR, USER_UPLOAD_DIR, OsEnv
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
)
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.agent.resolver import fix_raw_response
from nekro_agent.tools.common_util import download_file
from nekro_agent.tools.onebot_util import get_user_group_card_name
from nekro_agent.tools.path_convertor import (
    convert_to_host_path,
    is_url_path,
)


class SegAt(BaseModel):
    qq: str
    nickname: Optional[str]


class ChatService:
    def __init__(self):
        pass

    async def send_agent_message(
        self,
        chat_key: str,
        messages: Union[List[AgentMessageSegment], str],
        ctx: Optional[AgentCtx] = None,
        file_mode: bool = False,
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
        db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)
        message = Message()

        if isinstance(messages, str):
            messages = [AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=messages)]

        file_message: List[Path] = []
        if file_mode:
            # 发送文件
            for agent_message in messages:
                if agent_message.type != AgentMessageSegmentType.FILE.value:
                    raise ValueError("File mode only support file message")

                content = agent_message.content

                # 处理URL下载
                if is_url_path(content):
                    file_path, _ = await download_file(content, from_chat_key=chat_key)
                    file_message.append(Path(file_path))
                    continue

                try:
                    # 转换为宿主机路径
                    host_path = convert_to_host_path(
                        Path(content),
                        chat_key=chat_key,
                        container_key=ctx.container_key if ctx else None,
                    )

                    if host_path and host_path.exists():
                        logger.info(f"Sending agent file: {host_path}")
                        file_message.append(host_path)
                    else:
                        logger.warning(f"Invalid or non-existent file path: {content}")
                        message.append(MessageSegment.text(f"Invalid file path: {content}"))

                except ValueError as e:
                    logger.error(f"Path conversion error: {e}")
                    message.append(MessageSegment.text(str(e)))

        else:
            # 发送图片
            for agent_message in messages:
                content = agent_message.content
                if agent_message.type == AgentMessageSegmentType.TEXT.value:
                    content = fix_raw_response(content)
                    seg_data = await parse_at_from_text(content, db_chat_channel)
                    for seg in seg_data:
                        if isinstance(seg, str):
                            if seg.strip():
                                message.append(MessageSegment.text(seg))
                        elif isinstance(seg, SegAt):
                            message.append(MessageSegment.at(user_id=seg.qq))
                    logger.info(f"Sending agent message: {content}")
                elif agent_message.type == AgentMessageSegmentType.FILE.value:
                    try:
                        # 处理URL下载
                        if is_url_path(content):
                            file_path, _ = await download_file(content, from_chat_key=chat_key)
                            message.append(MessageSegment.image(file=Path(file_path).read_bytes()))
                            agent_message.content = str(file_path)
                            continue
                        # 转换为宿主机路径
                        host_path = convert_to_host_path(
                            Path(content),
                            chat_key=chat_key,
                            container_key=ctx.container_key if ctx else None,
                        )
                        agent_message.content = str(host_path)
                        if host_path and host_path.exists():
                            logger.info(f"Sending agent file: {host_path}")
                            message.append(MessageSegment.image(file=host_path.read_bytes()))
                        else:
                            logger.warning(f"Invalid or non-existent file path: {content}")
                            message.append(MessageSegment.text(f"Invalid file path: {content}"))

                    except ValueError as e:
                        logger.error(f"Path conversion error: {e}")
                        message.append(MessageSegment.text(str(e)))
                else:
                    raise ValueError(f"Invalid agent message type: {agent_message.type}")

        if not message and not file_message:
            logger.warning("Empty Message, skip sending")
            if config.DEBUG_IN_CHAT:
                await self.send_message(chat_key, "[Debug] 无消息回复")
            return

        if file_mode:
            try:
                await self.send_files(chat_key, file_message)
            except Exception as e:
                logger.exception(f"发送文件失败，协议端可能尚未支持该功能: {e}")
                if config.DEBUG_IN_CHAT:
                    await self.send_message(chat_key, "[Debug] 上传文件失败，协议端可能尚未支持该功能")
        else:
            await self.send_message(chat_key, message)
        if record:
            from nekro_agent.services.message.message_service import message_service

            await message_service.push_bot_message(chat_key, messages)

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

    async def send_files(self, chat_key: str, files: List[Path]):
        """发送文件

        Args:
            chat_key (str): 聊天的唯一标识
            files (List[Path]): 文件路径列表
        """
        bot: Bot = get_bot()

        try:
            chat_type, chat_id = chat_key.split("_")
        except ValueError as e:
            raise ValueError(f"Invalid chat key: {chat_key}") from e

        chat_type = ChatType(chat_type)
        chat_id = int(chat_id)

        # 如果配置了 OneBot 服务器挂载目录，需要转换路径
        def get_onebot_path(file_path: Path) -> Path:
            if config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR:
                return Path(config.SANDBOX_ONEBOT_SERVER_MOUNT_DIR) / file_path.relative_to(Path(OsEnv.DATA_DIR))
            return file_path

        if chat_type is ChatType.GROUP:
            for file in files:
                logger.info(f"Sending file: {file}")
                onebot_path = get_onebot_path(file)
                await bot.upload_group_file(
                    group_id=chat_id,
                    file=str(onebot_path),
                    name=file.name,
                )
        elif chat_type is ChatType.PRIVATE:
            for file in files:
                onebot_path = get_onebot_path(file)
                await bot.upload_private_file(
                    user_id=chat_id,
                    file=str(onebot_path),
                    name=file.name,
                )
        else:
            raise ValueError("Invalid chat type")


async def parse_at_from_text(text: str, db_chat_channel: DBChatChannel) -> List[Union[str, SegAt]]:
    """从文本中解析@信息
    需要提取 '[@qq:123456;nickname:用户名@]' 或 '[@qq:123456@]' 这样的格式，其余的文本不变

    Args:
        text (str): 文本

    Returns:
        List[Union[str, SegAt]]: 解析结果 (原始文本或SegAt对象)

    Examples:
        >>> parse_at_from_text("hello [@qq:123456;nickname:用户名@]")
        ['hello ', SegAt(qq='123456', nickname='用户名')]
        >>> parse_at_from_text("hello [@qq:123456@]")
        ['hello ', SegAt(qq='123456', nickname=None)]
        >>> parse_at_from_text("hello world")
        ['hello world']
    """
    result = []
    start = 0
    while True:
        at_index = text.find("[@", start)
        if at_index == -1:
            result.append(text[start:])
            break
        result.append(text[start:at_index])
        end_index = text.find("@]", at_index)
        if end_index == -1:
            result.append(text[at_index:])
            break
        seg = text[at_index + 2 : end_index]
        if "nickname:" in seg:
            parts = seg.split(";")
            qq = parts[0].replace("qq:", "").strip()
            nickname = parts[1].replace("nickname:", "").strip()
            if not config.SESSION_ENABLE_AT:
                result.append(f"{nickname}")
            else:
                if "group" in db_chat_channel.chat_key:
                    result.append(SegAt(qq=qq, nickname=None))
                else:
                    result.append("")  # 私聊无法@
        else:
            qq = seg.replace("qq:", "").strip()
            if not config.SESSION_ENABLE_AT:
                if "group" in db_chat_channel.chat_key:
                    group_id = db_chat_channel.chat_key.replace("group_", "")
                    nickname = await get_user_group_card_name(group_id=group_id, user_id=qq, db_chat_channel=db_chat_channel)
                    result.append(f"{nickname}")
                else:
                    result.append("")
            else:
                if "group" in db_chat_channel.chat_key:
                    result.append(SegAt(qq=qq, nickname=None))
                else:
                    result.append("")  # 私聊无法@
        start = end_index + 2  # 跳过 '@]' 标志
    return result


chat_service = ChatService()
