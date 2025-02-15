from nekro_agent.api import core, context
from nekro_agent.api.schemas import AgentCtx

__meta__ = core.ExtMetaData(
    name="ai_voice",
    description="[NA] AI 声聊",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@core.agent_collector.mount_method(core.MethodType.TOOL)
async def ai_voice(chat_key: str, text: str, _ctx: AgentCtx):
    """发送消息语音

    Args:
        chat_key (str): 聊天的唯一标识符 (仅支持群组)
        text (str): 语音文本 (必须是自然语句，不包含任何特殊符号)
    """
    chat_type = context.get_chat_type(chat_key)
    chat_id = context.get_chat_id(chat_key)

    if chat_type != "group":
        core.logger.error(f"不支持 {chat_type} 类型")
        return False

    try:
        await core.get_bot().call_api(
            "send_group_ai_record",
            group_id=int(chat_id),
            character=core.config.AI_VOICE_CHARACTER,
            text=text,
        )
        core.logger.info(f"[{chat_key}] 已生成 AI 语音 (内容: {text})")
    except Exception as e:
        core.logger.error(f"[{chat_key}] 生成 AI 语音失败: {e} | 如果协议端不支持该功能，请禁用此扩展")


async def clean_up():
    """清理扩展"""
    pass
