"""
# AI 语音 (AI Voice)

提供文本转语音（TTS）功能，让 AI 可以"开口说话"。

## 主要功能

- **文本转语音**: AI 可以将指定的文本，通过预设的 AI 语音角色（声源）合成为语音消息，并发送到群聊中。
- **角色查询**: 用户可以通过 `/ai_voices` 命令，查询当前协议端支持的所有可用语音角色。

## 使用方法

- **AI 自动调用**: 在某些场景下，AI 可能会决定使用语音来回复，此时它会自动调用此插件。
- **命令查询**: 用户可以使用 `/ai_voices` 命令查看可用的声音列表，然后在插件配置中修改 `AI_VOICE_CHARACTER` 来切换 AI 的声音。

## 特别说明

此插件的功能**高度依赖**于您所使用的 OneBot v11 协议端。它需要协议端实现了 `send_group_ai_record` 和 `get_ai_characters` 这两个自定义 API。如果您的协议端不支持这些 API，此插件将无法正常工作。
"""

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from pydantic import Field

from nekro_agent.adapters.onebot_v11.core.bot import get_bot
from nekro_agent.adapters.onebot_v11.matchers.command import (
    command_guard,
    finish_with,
    on_command,
)
from nekro_agent.api import core
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType

plugin = NekroPlugin(
    name="AI 语音插件",
    module_name="ai_voice",
    description="提供AI语音生成功能，支持将文本转为AI合成语音",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["onebot_v11"],
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
        tags = await bot.call_api("get_ai_characters", group_id=chat_key.split("_")[2])
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
    db_chat_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key=chat_key)
    chat_type = db_chat_channel.chat_type
    chat_id = db_chat_channel.channel_id

    if chat_type != ChatType.GROUP:
        core.logger.error(f"不支持 {chat_type} 类型")
        return False

    try:
        await get_bot().call_api(
            "send_group_ai_record",
            group_id=int(chat_id.split("_")[1]),
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
