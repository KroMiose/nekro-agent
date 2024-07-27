from typing import Optional, Type, Union, cast

from nonebot import on_message
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageEvent,
)
from nonebot.matcher import Matcher

from nekro_agent.core import logger
from nekro_agent.schemas.chat_message import ChatMessage, ChatType
from nekro_agent.schemas.user import UserCreate
from nekro_agent.services.user import query_user_by_bind_qq, user_register
from nekro_agent.systems.message.convertor import convert_chat_message
from nekro_agent.systems.message.push import push_human_chat_message
from nekro_agent.tools.onebot_util import gen_chat_text, get_user_name

message_matcher: Type[Matcher] = on_message(priority=20, block=True)


@message_matcher.handle()
async def _(
    _: Matcher,
    event: Union[MessageEvent, GroupMessageEvent],
    bot: Bot,
):
    raw_chat_type = event.message_type
    chat_type: ChatType
    if raw_chat_type == "friend":
        event = cast(MessageEvent, event)
        chat_key: str = f"friend_{event.user_id}"
        chat_type = ChatType.PRIVATE
    else:
        event = cast(GroupMessageEvent, event)
        chat_key = f"group_{event.group_id}"
        chat_type = ChatType.GROUP

    # 用户信息处理
    sender_real_nickname: Optional[str] = event.sender.nickname or event.sender.card
    assert sender_real_nickname

    bind_qq: str = str(event.sender.user_id)
    user = await query_user_by_bind_qq(bind_qq)

    if not user:
        ret = await user_register(
            UserCreate(
                username=sender_real_nickname,
                password="123456",
                bind_qq=event.get_user_id(),
            ),
        )

        if not ret:
            logger.error(f"注册用户失败: {sender_real_nickname}")
            return

        user = await query_user_by_bind_qq(bind_qq)
        assert user

    content_data = await convert_chat_message(event.message)
    if not content_data:  # 忽略无法转换的消息
        return

    sender_nickname: str = await get_user_name(event=event, bot=bot, user_id=event.get_user_id())
    content_text, is_tome = await gen_chat_text(event=event, bot=bot)
    send_timestamp: int = event.time

    chat_message: ChatMessage = ChatMessage(
        sender_id=user.id,
        sender_real_nickname=sender_real_nickname,
        sender_nickname=sender_nickname,
        sender_bind_qq=bind_qq,
        is_tome=is_tome,
        is_recalled=False,
        chat_key=chat_key,
        chat_type=chat_type,
        content_text=content_text,
        content_data=content_data,
        raw_cq_code=event.raw_message,
        ext_data={},
        send_timestamp=send_timestamp,
    )

    await push_human_chat_message(chat_message)
