from typing import Type, cast

from nonebot import on_command
from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent,
    MessageEvent,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from nekro_agent.core import config, logger
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.sandbox.executor import (
    limited_run_code,
)
from nekro_agent.tools.onebot_util import get_chat_info, get_user_name

execute_matcher: Type[Matcher] = on_command("exec", priority=10, block=True)


@execute_matcher.handle()
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
    raw_cmd: str = arg.extract_plain_text().strip()

    chat_key, chat_type = await get_chat_info(event=event)

    logger.info(
        f"接收到用户: {username} 发送的指令: {raw_cmd}",
    )

    result: str = await limited_run_code(raw_cmd, from_chat_key=chat_key)

    if result:
        await matcher.finish(result)
    else:
        pass
        # await matcher.finish("<empty>")
