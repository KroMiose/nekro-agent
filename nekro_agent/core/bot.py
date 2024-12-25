from nonebot import get_bot as _get_bot
from nonebot.adapters.onebot.v11 import Bot


def get_bot() -> Bot:
    """获取当前 Bot 实例"""

    return _get_bot()  # type: ignore
