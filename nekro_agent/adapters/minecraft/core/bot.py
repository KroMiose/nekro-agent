from typing import Optional

from nonebot import get_bots
from nonebot.adapters.minecraft import Bot

from nekro_agent.core import logger


def get_bot(identifier: Optional[str] = None) -> Optional[Bot]:
    """
    获取 Minecraft Bot 实例。

    Args:
        identifier: Bot 的标识符。
                    来自 nekro-agent 的 chat_key (例如 'minecraft-servername')，
                    其中 'servername' 应该对应 NoneBot 中 Bot 的 self_id。
                    如果为 None 或无法从中解析出 servername，则尝试返回第一个可用的 Minecraft Bot。
    """
    bots = get_bots()  # get_bots() 返回一个字典 {bot_id: Bot_instance}

    target_bot_id: Optional[str] = None
    if identifier and identifier.startswith("minecraft-"):
        parts = identifier.split("-", 1)
        if len(parts) > 1 and parts[1]:
            target_bot_id = parts[1]

    if target_bot_id:
        bot = bots.get(target_bot_id)
        if bot and isinstance(bot, Bot):
            return bot

    return None
