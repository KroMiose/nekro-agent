from nonebot.adapters.onebot.v11 import Bot

from nekro_agent.core import logger
from nekro_agent.core.bot import get_bot
from nekro_agent.core.config import config
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.chat import chat_service
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import MethodType, agent_collector

__meta__ = ExtMetaData(
    name="group_honor",
    description="[NA] 群荣誉",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@agent_collector.mount_method(MethodType.TOOL)
async def set_user_special_title(chat_key: str, user_qq: str, special_title: str, days: int, _ctx: AgentCtx) -> bool:
    """赋予用户头衔称号

    Args:
        chat_key (str): 聊天的唯一标识符 (仅支持群组)
        user_qq (str): 用户 QQ 号
        special_title (str): 头衔 (不超过6个字符, 为空则移除头衔)
        days (int): 有效期/天

    Returns:
        bool: 操作是否成功
    """
    chat_type, chat_id = chat_key.split("_")
    if chat_type != "group":
        logger.error(f"不支持 {chat_type} 类型")
        return False

    try:
        await get_bot().call_api(
            "set_group_special_title",
            group_id=int(chat_id),
            user_id=int(user_qq),
            special_title=special_title,
            duration=days * 24 * 60 * 60,
        )
        logger.info(f"[{chat_key}] 已授予用户 {user_qq} 头衔 {special_title} {days} 天")
    except Exception as e:
        logger.error(f"[{chat_key}] 授予用户 {user_qq} 头衔 {special_title} {days} 天失败: {e}")
        return False
    else:
        return True
