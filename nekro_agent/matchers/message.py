import time
from enum import Enum
from functools import wraps
from typing import Callable, Dict, Optional, Tuple, Type, Union

from nonebot import on_message, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    GroupUploadNoticeEvent,
    MessageEvent,
    NoticeEvent,
)
from nonebot.matcher import Matcher

from nekro_agent.core import config, logger
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.chat_message import ChatMessage, ChatType
from nekro_agent.schemas.user import UserCreate
from nekro_agent.services.user import query_user_by_bind_qq, user_register
from nekro_agent.systems.message.convertor import convert_chat_message
from nekro_agent.systems.message.push_human_msg import push_human_chat_message
from nekro_agent.tools.onebot_util import gen_chat_text, get_chat_info, get_user_name

message_matcher: Type[Matcher] = on_message(priority=20, block=True)


@message_matcher.handle()
async def _(
    _: Matcher,
    event: Union[MessageEvent, GroupMessageEvent],
    bot: Bot,
):
    chat_key, chat_type = await get_chat_info(event=event)

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

    content_data, msg_tome, message_id = await convert_chat_message(event, event.to_me, bot, chat_key)
    if not content_data:  # 忽略无法转换的消息
        return

    sender_nickname: str = await get_user_name(event=event, bot=bot, user_id=bind_qq)
    content_text, is_tome = await gen_chat_text(event=event, bot=bot)
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

    await push_human_chat_message(chat_message)


upload_notice_matcher: Type[Matcher] = on_notice(priority=20, block=True)


@upload_notice_matcher.handle()
async def _(
    _: Matcher,
    event: GroupUploadNoticeEvent,
    bot: Bot,
):
    chat_key, chat_type = await get_chat_info(event=event)
    bind_qq: str = str(event.user_id)
    user: Optional[DBUser] = await query_user_by_bind_qq(bind_qq)

    if not user:
        if bind_qq == config.BOT_QQ:
            return
        raise ValueError(f"用户 {bind_qq} 尚未注册，请先发送任意消息注册后即可上传文件") from None

    # 用户信息处理
    sender_real_nickname: Optional[str] = user.username

    content_data, msg_tome, message_id = await convert_chat_message(event, False, bot, chat_key)
    if not content_data:  # 忽略无法转换的消息
        return

    sender_nickname: str = await get_user_name(event=event, bot=bot, user_id=bind_qq)

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

    await push_human_chat_message(chat_message)


"""通用通知匹配器"""
notice_matcher: Type[Matcher] = on_notice(priority=20, block=True)


class NoticeEventType(Enum):
    POKE = "poke"  # 戳一戳
    GROUP_INCREASE = "group_increase"  # 群成员增加
    GROUP_DECREASE = "group_decrease"  # 群成员退出
    # ... 未来可以添加更多事件类型


def notice_handler(event_type: NoticeEventType, force_tome: bool = False):
    """注册通知事件处理器的装饰器
    Args:
        event_type (NoticeEventType): 通知事件类型
        force_tome (bool): 是否强制设置 is_tome 为 True
    """

    def decorator(func: Callable[[dict], str]):
        @wraps(func)
        def wrapper(info: dict) -> Tuple[str, bool]:
            return func(info), force_tome

        EVENT_MESSAGE_FORMATTERS[event_type] = wrapper
        return wrapper

    return decorator


# 事件类型到消息格式化函数的映射
EVENT_MESSAGE_FORMATTERS: Dict[NoticeEventType, Callable[[dict], Tuple[str, bool]]] = {}


@notice_handler(NoticeEventType.POKE)
def format_poke_message(info: dict) -> str:
    """格式化戳一戳消息"""
    target_id = info["target_id"]
    if str(target_id) == str(config.BOT_QQ):
        return f"(戳了戳 {config.AI_CHAT_PRESET_NAME})"
    return f"(戳了戳 {target_id})"


@notice_handler(NoticeEventType.GROUP_INCREASE, force_tome=True)
def format_group_increase_message(info: dict) -> str:
    """格式化群成员增加消息"""
    return f"(新成员 (qq:{info['user_id']}) 加入群聊)"


@notice_handler(NoticeEventType.GROUP_DECREASE, force_tome=True)
def format_group_decrease_message(info: dict) -> str:
    return f"(成员 (qq:{info['user_id']}) 退出群聊)"


def get_notice_info(event: NoticeEvent) -> Tuple[Optional[NoticeEventType], dict]:
    """解析通知事件类型和相关信息"""
    logger.debug(f"收到通知事件: {event}")
    sub_type = getattr(event, "sub_type", None)
    user_id: str = str(getattr(event, "user_id", ""))
    target_id: str = str(getattr(event, "target_id", ""))

    if event.notice_type == "notify" and sub_type == "poke":
        return NoticeEventType.POKE, {"user_id": user_id, "target_id": target_id}
    if event.notice_type == "group_increase":
        return NoticeEventType.GROUP_INCREASE, {"user_id": user_id}
    if event.notice_type == "group_decrease":
        return NoticeEventType.GROUP_DECREASE, {"user_id": user_id}
    return None, {}


@notice_matcher.handle()
async def _(
    _: Matcher,
    event: NoticeEvent,
    bot: Bot,
):
    # 解析事件类型和信息
    event_type, event_info = get_notice_info(event)
    if not event_type:
        logger.debug(f"收到未处理的通知类型: {event}")
        return

    chat_key, chat_type = await get_chat_info(event=event)
    bind_qq: str = str(event_info["user_id"])
    user: Optional[DBUser] = await query_user_by_bind_qq(bind_qq)

    # 获取对应的消息格式化方法并生成消息文本
    message_formatter = EVENT_MESSAGE_FORMATTERS.get(event_type)
    if not message_formatter:
        logger.debug(f"未找到 {event_type.value} 事件的消息格式化方法, 跳过处理...")
        return

    content_text, force_tome = message_formatter(event_info)

    # 获取发送者昵称
    sender_nickname: str = await get_user_name(event=event, bot=bot, user_id=bind_qq)

    chat_message: ChatMessage = ChatMessage(
        message_id="",
        sender_id=str(user.id) if user else str(bind_qq),
        sender_real_nickname=user.username if user else sender_nickname,
        sender_nickname=sender_nickname,
        sender_bind_qq=bind_qq,
        is_tome=1 if (force_tome or (event_type == NoticeEventType.POKE and event_info["target_id"] == config.BOT_QQ)) else 0,
        is_recalled=False,
        chat_key=chat_key,
        chat_type=chat_type,
        content_text=content_text,
        content_data=[],
        raw_cq_code="",
        ext_data={},
        send_timestamp=int(time.time()),
    )

    await push_human_chat_message(chat_message)
