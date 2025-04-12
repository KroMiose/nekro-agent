from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from pydantic import Field

from nekro_agent.api import context, core
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.matchers.command import command_guard, finish_with, on_command
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

plugin = NekroPlugin(
    name="AI 语音插件",
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
        default="lucy-voice-xueling",
        title="AI语音角色",
        description="使用命令 `/ai_voices` 可查看所有可用角色",
    )


# 获取配置
config = plugin.get_config(AIVoiceConfig)


@on_command("ai_voices", aliases={"ai-voices"}, priority=5, block=True).handle()
async def _(matcher: Matcher, event: MessageEvent, bot: Bot, arg: Message = CommandArg()):
    username, cmd_content, chat_key, chat_type = await command_guard(event, bot, arg, matcher)

    if chat_type is ChatType.GROUP:
        tags = await bot.call_api("get_ai_characters", group_id=chat_key.split("_")[1])
        formatted_characters = []
        for tag in tags:
            char_list = []
            for char in tag["characters"]:
                char_list.append(f"ID: {char['character_id']} - {char['character_name']}")
            formatted_characters.append(f"=== {tag['type']} ===\n" + "\n".join(char_list))

        await finish_with(matcher, message="当前可用的 AI 声聊角色: \n\n" + "\n\n".join(formatted_characters))
    else:
        await finish_with(matcher, message="AI 声聊功能仅支持群组")


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
