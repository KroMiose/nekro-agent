from nonebot import get_bots
from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot


def get_bot() -> OneBotV11Bot:
    """获取当前 OneBot V11 Bot 实例"""
    all_bots = get_bots()
    for bot_instance in all_bots.values():
        if isinstance(bot_instance, OneBotV11Bot):
            return bot_instance
    raise RuntimeError("No OneBot V11 bot instance found.")
