from nonebot import get_driver
from nonebot.adapters.onebot.v11 import Bot

_bot: Bot


def get_bot() -> Bot:
    """获取当前 Bot 实例"""

    global _bot

    assert _bot, "Bot not available"
    return _bot


@get_driver().on_bot_connect
async def _(bot):
    global _bot
    _bot = bot


@get_driver().on_bot_disconnect
async def _(bot):
    global _bot
    if _bot == bot:
        _bot = None  # type: ignore
