from nonebot.adapters.onebot.v11 import Bot

from nekro_agent.core import logger
from nekro_agent.core.bot import get_bot
from nekro_agent.core.config import config
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.chat import chat_service
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import MethodType, agent_collector

__meta__ = ExtMetaData(
    name="ai_voice",
    description="[NA] AI 声聊",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@agent_collector.mount_method(MethodType.TOOL)
async def ai_voice(chat_key: str, text: str, _ctx: AgentCtx):
    """发送消息语音

    Args:
        chat_key (str): 聊天的唯一标识符 (仅支持群组)
        text (str): 语音文本 (必须是自然语句，不包含任何特殊符号)
    """
    chat_type, chat_id = chat_key.split("_")
    if chat_type != "group":
        logger.error(f"不支持 {chat_type} 类型")
        return False

    try:
        await get_bot().call_api(
            "send_group_ai_record",
            group_id=int(chat_id),
            character=config.AI_VOICE_CHARACTER,
            text=text,
        )
        logger.info(f"[{chat_key}] 已生成 AI 语音 (内容: {text})")
    except Exception as e:
        logger.error(f"[{chat_key}] 生成 AI 语音失败: {e} | 如果协议端不支持该功能，请禁用此扩展")
