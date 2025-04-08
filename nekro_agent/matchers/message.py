import time
from datetime import datetime
from typing import Optional, Type, Union

from nonebot import on_message, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GroupUploadNoticeEvent,
    MessageEvent,
)
from nonebot.matcher import Matcher

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.chat_message import ChatMessage, ChatType
from nekro_agent.schemas.user import UserCreate
from nekro_agent.services.message.convertor import convert_chat_message
from nekro_agent.services.message.message_service import message_service
from nekro_agent.services.user.util import query_user_by_bind_qq, user_register
from nekro_agent.tools.onebot_util import gen_chat_text, get_chat_info, get_user_name

message_matcher: Type[Matcher] = on_message(priority=99999, block=False)


@message_matcher.handle()
async def _(
    _: Matcher,
    event: Union[MessageEvent, GroupMessageEvent],
    bot: Bot,
):
    chat_key, chat_type = await get_chat_info(event=event)
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)
    # 用户信息处理
    sender_real_nickname: Optional[str] = event.sender.nickname or event.sender.card
    assert sender_real_nickname

    bind_qq: str = str(event.sender.user_id)
    user: Optional[DBUser] = await query_user_by_bind_qq(bind_qq)

    if not user:
        ret = await user_register(
            UserCreate(
                username=sender_real_nickname,
                password="123456",
                bind_qq=bind_qq,
            ),
        )

        if not ret:
            logger.error(f"注册用户失败: {sender_real_nickname} - {bind_qq}")
            return

        user = await query_user_by_bind_qq(bind_qq)
        assert user

    if not user.is_active:
        logger.info(f"用户 {bind_qq} 被封禁，封禁结束时间: {user.ban_until}")
        return

    content_data, msg_tome, message_id = await convert_chat_message(event, event.to_me, bot, db_chat_channel)
    if not content_data:  # 忽略无法转换的消息
        return

    sender_nickname: str = await get_user_name(event=event, bot=bot, user_id=bind_qq, db_chat_channel=db_chat_channel)
    content_text, is_tome = await gen_chat_text(event=event, bot=bot, db_chat_channel=db_chat_channel)
    # send_timestamp: int = event.time

    if any(content_text.startswith(prefix) for prefix in config.AI_IGNORED_PREFIXES):
        logger.info(f"忽略前缀匹配的消息: {content_text[:32]}...")
        return

    chat_message: ChatMessage = ChatMessage(
        message_id=message_id,
        sender_id=str(user.id),
        sender_real_nickname=sender_real_nickname,
        sender_nickname=sender_nickname,
        sender_bind_qq=bind_qq,
        is_tome=is_tome or msg_tome or event.to_me,
        is_recalled=False,
        chat_key=chat_key,
        chat_type=chat_type,
        content_text=content_text,
        content_data=content_data,
        raw_cq_code=event.raw_message,
        ext_data={},
        send_timestamp=int(time.time()),
    )

    await message_service.push_human_message(message=chat_message, user=user)


upload_notice_matcher: Type[Matcher] = on_notice(priority=99999, block=False)


@upload_notice_matcher.handle()
async def _(
    _: Matcher,
    event: GroupUploadNoticeEvent,
    bot: Bot,
):
    chat_key, chat_type = await get_chat_info(event=event)
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)
    bind_qq: str = str(event.user_id)
    user: Optional[DBUser] = await query_user_by_bind_qq(bind_qq)

    if not user:
        if bind_qq == config.BOT_QQ:
            return
        raise ValueError(f"用户 {bind_qq} 尚未注册，请先发送任意消息注册后即可上传文件") from None

    if not user.is_active:
        logger.info(f"用户 {bind_qq} 被封禁，封禁结束时间: {user.ban_until}")
        return

    # 用户信息处理
    sender_real_nickname: Optional[str] = user.username

    content_data, msg_tome, message_id = await convert_chat_message(event, False, bot, db_chat_channel)
    if not content_data:  # 忽略无法转换的消息
        return

    sender_nickname: str = await get_user_name(event=event, bot=bot, user_id=bind_qq, db_chat_channel=db_chat_channel)

    chat_message: ChatMessage = ChatMessage(
        message_id=message_id,
        sender_id=str(user.id),
        sender_real_nickname=sender_real_nickname,
        sender_nickname=sender_nickname,
        sender_bind_qq=bind_qq,
        is_tome=msg_tome,
        is_recalled=False,
        chat_key=chat_key,
        chat_type=chat_type,
        content_text="",
        content_data=content_data,
        raw_cq_code="",
        ext_data={},
        send_timestamp=int(time.time()),
    )

    await message_service.push_human_message(message=chat_message, user=user)
