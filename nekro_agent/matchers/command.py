from typing import Type

from nonebot import on_command
from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from nekro_agent.core import config, logger
from nekro_agent.services.chat import chat_service
from nekro_agent.tools.onebot_util import gen_chat_text, get_user_name

push_message_matcher: Type[Matcher] = on_command("push", priority=20, block=True)


@push_message_matcher.handle()
async def _(
    matcher: Matcher,  # noqa: ARG001
    event: MessageEvent,
    bot: Bot,
    arg: Message = CommandArg(),
):
    # 判断是否是禁止使用的用户
    if event.get_user_id() not in config.SUPER_USERS:
        logger.info(f"用户 {event.get_user_id()} 不在允许用户中")
        return

    username = await get_user_name(event=event, bot=bot, user_id=event.get_user_id())
    cmd_content: str = arg.extract_plain_text()

    logger.info(
        f"接收到用户: {username} 发送的指令: {cmd_content}",
    )

    chat_key, content = cmd_content.split(" ", 1)

    await chat_service.send_message(chat_key, content)
