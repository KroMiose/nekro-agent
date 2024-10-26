from typing import Tuple, Union, cast

from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import (
    GroupIncreaseNoticeEvent,
    GroupMessageEvent,
    GroupUploadNoticeEvent,
    MessageEvent,
)

from nekro_agent.core.bot import get_bot
from nekro_agent.core.config import config
from nekro_agent.schemas.chat_message import ChatType


async def gen_chat_text(event: MessageEvent, bot: Bot) -> Tuple[str, int]:
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
                    msg += "@[全体成员]"
                    is_tome = 1
                else:
                    user_name = await get_user_name(
                        event=event,
                        bot=bot,
                        user_id=int(qq),
                    )
                    if user_name:
                        msg += f"@[{user_name}, qq={qq}]"  # 保持给bot看到的内容与真实用户看到的一致
    return msg, is_tome


async def get_user_name(
    event: Union[MessageEvent, GroupIncreaseNoticeEvent, GroupUploadNoticeEvent],
    bot: Bot,
    user_id: Union[int, str],
) -> str:
    """获取QQ用户名"""
    if str(user_id) == str(config.BOT_QQ):
        return config.AI_CHAT_PRESET_NAME

    if isinstance(event, GroupMessageEvent) and event.sub_type == "anonymous" and event.anonymous:  # 匿名消息
        return f"[匿名]{event.anonymous.name}"

    if isinstance(event, (GroupMessageEvent, GroupIncreaseNoticeEvent)):
        user_info = await bot.get_group_member_info(
            group_id=event.group_id,
            user_id=user_id,
            no_cache=False,
        )
        user_name = user_info.get("nickname", None)
        user_name = user_info.get("card", None) or user_name
    else:
        user_name = event.sender.nickname if not isinstance(event, GroupUploadNoticeEvent) and event.sender else event.get_user_id()

    if not user_name:
        raise ValueError("获取用户名失败")

    return user_name


async def get_user_group_card_name(group_id: Union[int, str], user_id: Union[int, str]) -> str:
    """获取用户所在群的群名片"""
    if str(user_id) == str(config.BOT_QQ):
        return config.AI_CHAT_PRESET_NAME
    user_info = await get_bot().get_group_member_info(
        group_id=int(group_id),
        user_id=int(user_id),
        no_cache=False,
    )
    return user_info.get("card") or user_info.get("nickname", "未知")


async def get_chat_info(event: Union[MessageEvent, GroupIncreaseNoticeEvent, GroupUploadNoticeEvent]) -> Tuple[str, ChatType]:
    if isinstance(event, (GroupUploadNoticeEvent, GroupIncreaseNoticeEvent)):
        raw_chat_type = "group"
    else:
        raw_chat_type = event.message_type
    chat_type: ChatType
    if raw_chat_type == "friend" or raw_chat_type == "private":
        event = cast(MessageEvent, event)
        chat_key: str = f"private_{event.user_id}"
        chat_type = ChatType.PRIVATE
    elif raw_chat_type == "group":
        event = cast(GroupMessageEvent, event)
        chat_key = f"group_{event.group_id}"
        chat_type = ChatType.GROUP  # noqa: F841
    else:
        raise ValueError("未知的消息类型")

    return chat_key, chat_type
