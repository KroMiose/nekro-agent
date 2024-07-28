from typing import List

from nonebot.adapters.onebot.v11 import Bot

from nekro_agent.core import logger
from nekro_agent.core.bot import get_bot
from nekro_agent.services.chat import chat_service
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import agent_collector

from .basic import send_msg_text

__meta__ = ExtMetaData(
    name="judgement",
    description="Nekro-Agent 风纪委员 (群管工具集)",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@agent_collector.mount_method()
async def mute_user(chat_key: str, user_qq: str, duration: int) -> bool:
    """禁言用户

    Args:
        chat_key (str): 聊天的唯一标识符
        user_qq (str): 被禁言的用户的QQ号
        duration (int): 禁言时长，单位为秒，设置为 0 则解除禁言.

    Returns:
        bool: 操作是否成功
    """
    bot: Bot = get_bot()
    chat_type, chat_id = chat_key.split("_")
    if chat_type != "group":
        logger.error(f"不支持 {chat_type} 类型")
        return False

    try:
        await bot.set_group_ban(group_id=int(chat_id), user_id=int(user_qq), duration=duration)
        logger.info(f"[{chat_key}] 已禁言用户 {user_qq} {duration} 秒")
    except Exception as e:
        logger.error(f"[{chat_key}] 禁言用户 {user_qq} {duration} 秒失败: {e}")
        return False
    else:
        return True
