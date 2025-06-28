from typing import Tuple, Union, cast

from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import (
    GroupIncreaseNoticeEvent,
    GroupMessageEvent,
    GroupUploadNoticeEvent,
    MessageEvent,
    NoticeEvent,
)

from nekro_agent.adapters.onebot_v11.core.bot import get_bot
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType


async def gen_chat_text(event: MessageEvent, bot: Bot, db_chat_channel: DBChatChannel) -> Tuple[str, int]:
    """生成合适的会话消息内容(eg. 将cq at 解析为真实的名字)

    Args:
        event (MessageEvent): 事件对象
        bot (Bot): 机器人对象

    Returns:
        Tuple[str, int]: 会话消息内容, 是否与自身相关
    """
    if not isinstance(event, GroupMessageEvent):
        return event.get_plaintext(), 0

    is_tome: int = 0
    msg = ""
    for seg in event.message:
        if seg.is_text():
            msg += seg.data.get("text", "")
        elif seg.type == "at":
            qq = seg.data.get("qq", None)
            if qq:
                if qq == "all":
                    msg += "[@id:all;nickname:全体成员@]"
                    is_tome = 1
                else:
                    user_name = await get_user_name(
                        event=event,
                        bot=bot,
                        user_id=int(qq),
                        db_chat_channel=db_chat_channel,
                    )
                    if user_name:
                        msg += f"[@id:{qq};nickname:{user_name}@]"  # 保持给bot看到的内容与真实用户看到的一致
    return msg, is_tome


async def get_user_name(
    event: Union[MessageEvent, GroupIncreaseNoticeEvent, GroupUploadNoticeEvent, NoticeEvent],
    bot: Bot,
    user_id: Union[int, str],
    db_chat_channel: DBChatChannel,
) -> str:
    """获取QQ用户名"""
    if str(user_id) == (await db_chat_channel.adapter.get_self_info()).user_id:
        return (await db_chat_channel.get_preset()).name

    if isinstance(event, GroupMessageEvent) and event.sub_type == "anonymous" and event.anonymous:  # 匿名消息
        return f"[匿名]{event.anonymous.name}"

    if isinstance(event, (GroupMessageEvent, GroupIncreaseNoticeEvent, NoticeEvent)):
        group_id = getattr(event, "group_id", None)
        if group_id:
            user_info = await bot.get_group_member_info(
                group_id=group_id,
                user_id=user_id,
                no_cache=False,
            )
        else:
            raise ValueError("获取群成员信息失败")
        user_name = user_info.get("nickname", None)
        user_name = user_info.get("card", None) or user_name
    else:
        user_name = (
            event.sender.nickname if not isinstance(event, GroupUploadNoticeEvent) and event.sender else event.get_user_id()
        )

    if not user_name:
        raise ValueError("获取用户名失败")

    return user_name


async def get_user_group_card_name(
    group_id: Union[int, str],
    user_id: Union[int, str],
    db_chat_channel: DBChatChannel,
) -> str:
    """获取用户所在群的群名片"""
    if str(user_id) == (await db_chat_channel.adapter.get_self_info()).user_id:
        return (await db_chat_channel.get_preset()).name
    if str(user_id) == "all" or str(user_id) == "0":
        return "全体成员"
    user_info = await get_bot().get_group_member_info(
        group_id=int(group_id),
        user_id=int(user_id),
        no_cache=False,
    )
    return user_info.get("card") or user_info.get("nickname", "未知")


async def get_chat_info(
    event: Union[MessageEvent, GroupIncreaseNoticeEvent, GroupUploadNoticeEvent, NoticeEvent],
) -> Tuple[str, ChatType]:
    """获取频道信息"""
    if isinstance(event, (GroupUploadNoticeEvent, GroupIncreaseNoticeEvent, NoticeEvent)):
        raw_chat_type = "group"
    else:
        raw_chat_type = event.message_type
    chat_type: ChatType
    if raw_chat_type == "friend" or raw_chat_type == "private":
        event = cast(MessageEvent, event)
        channel_id: str = f"private_{event.user_id}"
        chat_type = ChatType.PRIVATE
    elif raw_chat_type == "group":
        event = cast(GroupMessageEvent, event)
        channel_id = f"group_{event.group_id}"
        chat_type = ChatType.GROUP  # noqa: F841
    else:
        chat_type = ChatType.UNKNOWN
        raise ValueError("未知的消息类型")

    return channel_id, chat_type


async def get_chat_info_old(
    event: Union[MessageEvent, GroupIncreaseNoticeEvent, GroupUploadNoticeEvent, NoticeEvent],
) -> Tuple[str, ChatType]:
    """获取频道信息(旧版)

    直接返回完整频道标识适配旧功能需求
    """
    if isinstance(event, (GroupUploadNoticeEvent, GroupIncreaseNoticeEvent, NoticeEvent)):
        raw_chat_type = "group"
    else:
        raw_chat_type = event.message_type
    chat_type: ChatType
    if raw_chat_type == "friend" or raw_chat_type == "private":
        event = cast(MessageEvent, event)
        channel_id: str = f"private_{event.user_id}"
        chat_type = ChatType.PRIVATE
    elif raw_chat_type == "group":
        event = cast(GroupMessageEvent, event)
        channel_id = f"group_{event.group_id}"
        chat_type = ChatType.GROUP  # noqa: F841
    else:
        chat_type = ChatType.UNKNOWN
        raise ValueError("未知的消息类型")

    return f"onebot_v11-{channel_id}", chat_type


async def get_message_reply_info(event: MessageEvent) -> str:
    """获取消息回复信息"""
    if not event.original_message:
        return ""
    for seg in event.original_message:
        if seg.type == "reply":
            return str(seg.data.get("id") or "")
    return ""
