from arclet.alconna import Alconna
from nonebot import on_message
from nonebot.adapters.minecraft import Adapter as MinecraftAdapter
from nonebot.adapters.minecraft import Bot
from nonebot.rule import Rule
from nonebot_plugin_alconna import AlconnaMatches, Arparma, on_alconna

from nekro_agent.core import config, logger


async def is_minecraft_event(bot: Bot) -> bool:
    return isinstance(bot.adapter, MinecraftAdapter)

recv_minecraft_message = on_message(
    rule=Rule(is_minecraft_event),
    priority=99999,
    block=False,
)

@recv_minecraft_message.handle()
async def _():
    logger.info("Received message from Minecraft.")
    

