from typing import Optional

from pydantic import Field

from nekro_agent.api import context, core
from nekro_agent.api.core import config as global_config
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

plugin = NekroPlugin(
    name="[NA] AI 语音插件",
    module_name="ai_voice",
    description="提供AI语音生成功能，支持将文本转为AI合成语音",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_config()
class AIVoiceConfig(ConfigBase):
    """AI语音配置"""

    AI_VOICE_CHARACTER: str = Field(
        default=global_config.AI_VOICE_CHARACTER,
        title="AI语音角色",
        description="使用命令 /ai_voices 查看所有可用角色",
    )


# 获取配置
config = plugin.get_config(AIVoiceConfig)


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "发送消息语音")
async def ai_voice(_ctx: AgentCtx, chat_key: str, text: str) -> bool:
    """发送消息语音

    Args:
        chat_key (str): 聊天的唯一标识符 (仅支持群组)
        text (str): 语音文本 (必须是自然语句，不包含任何特殊符号)

    Returns:
        bool: 操作是否成功
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
            character=config.AI_VOICE_CHARACTER,
            text=text,
        )
        core.logger.info(f"[{chat_key}] 生成 AI 语音完成 (内容: {text})")
    except Exception as e:
        core.logger.error(f"[{chat_key}] 生成 AI 语音失败: {e} | 如果协议端不支持该功能，请禁用此插件")
        return False
    else:
        return True


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
