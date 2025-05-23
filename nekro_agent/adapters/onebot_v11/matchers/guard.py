from typing import NoReturn, Tuple, Union

from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.matcher import Matcher

from nekro_agent.adapters.onebot_v11.tools.onebot_util import (
    get_chat_info_old,
    get_user_name,
)
from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType


async def finish_with(matcher: Matcher, message: str) -> NoReturn:
    await matcher.finish(message=f"[Opt Output] {message}")


async def command_guard(
    event: Union[MessageEvent, GroupMessageEvent],
    bot: Bot,
    arg: Message,
    matcher: Matcher,
    trigger_on_off: bool = False,
) -> Tuple[str, str, str, ChatType]:
    """指令执行前处理

    Args:
        event (Union[MessageEvent, GroupMessageEvent]): 事件对象
        bot (Bot): Bot 对象
        arg (Message): 命令参数
        matcher (Matcher): Matcher 对象

    Returns:
        Tuple[str, str, str, ChatType]: 用户名, 命令内容(不含命令名), 会话标识, 会话类型
    """
    chat_key, chat_type = await get_chat_info_old(event=event)
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)
    if not db_chat_channel.is_active and not trigger_on_off:
        await matcher.finish()
    username = await get_user_name(event=event, bot=bot, user_id=event.get_user_id(), db_chat_channel=db_chat_channel)
    # 判断是否是禁止使用的用户
    if event.get_user_id() not in config.SUPER_USERS:
        logger.warning(f"用户 {username} 不在允许的管理用户中")
        if config.ENABLE_COMMAND_UNAUTHORIZED_OUTPUT:
            await finish_with(matcher, f"用户 [{event.get_user_id()}]{username} 不在允许的管理用户中")
        else:
            await matcher.finish()

    cmd_content: str = arg.extract_plain_text().strip()
    return username, cmd_content, chat_key, chat_type


async def reset_command_guard(
    event: Union[MessageEvent, GroupMessageEvent],
    bot: Bot,
    arg: Message,
    matcher: Matcher,
) -> Tuple[str, str, str, ChatType]:
    """Reset指令鉴权"""
    chat_key, chat_type = await get_chat_info_old(event=event)
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)
    username = await get_user_name(event=event, bot=bot, user_id=event.get_user_id(), db_chat_channel=db_chat_channel)
    cmd_content: str = arg.extract_plain_text().strip()

    if event.get_user_id() in config.SUPER_USERS:
        return username, cmd_content, chat_key, chat_type

    # 非超级用户
    if cmd_content and chat_key != cmd_content:
        logger.warning(f"用户 {username} 尝试越权操作其他会话")
        if config.ENABLE_COMMAND_UNAUTHORIZED_OUTPUT:
            await finish_with(matcher, "您只能操作当前会话")
        else:
            await matcher.finish()

    # 私聊用户允许操作
    if chat_type == ChatType.PRIVATE:
        return username, cmd_content, chat_key, chat_type

    # 群聊检查管理员权限
    if chat_type == ChatType.GROUP and isinstance(event, GroupMessageEvent) and event.sender.role in ["admin", "owner"]:
        return username, cmd_content, chat_key, chat_type

    # 无权限情况处理
    logger.warning(f"用户 {username} 不在允许的管理用户中")
    if config.ENABLE_COMMAND_UNAUTHORIZED_OUTPUT:
        await finish_with(matcher, f"用户 [{event.get_user_id()}]{username} 不在允许的管理用户中")
    else:
        await matcher.finish()
    raise
