"""
# 角色状态控制 (Status)

一个用于增强和维持 AI 角色扮演一致性的核心插件。

## 设计理念：状态记忆

在连续的角色扮演对话中，AI 很容易"忘记"自己上一刻的状态（比如情绪、外观、正在做的事）。此插件通过一个"状态机"来解决这个问题。

每当 AI 的角色状态发生重要变化时（例如，从"悠闲喝茶"变为"紧张战斗"），它会自动调用工具来更新自己的当前状态。这个状态会被记录下来，并在下一次对话开始前"提醒"AI，确保它能始终如一地扮演自己的角色，不会出现"失忆"的尴尬情况。

## 主要功能

- **状态更新与维持**: AI 会根据对话的进展，自动更新和记录自己角色的核心状态。
- **动态群名片**: (可选功能) 可以将 AI 的当前状态同步设置为其在群聊中的昵称（群名片），让所有人都能直观地看到 AI 的状态变化。例如，AI 的群名片可能会从"悠闲的莉莉"变为"备战中的莉莉"。
- **状态重置**: 在会话重置时，会自动清除所有临时状态，恢复到初始设定。

## 使用方法

此插件主要由 AI 在后台自动使用，用户通常无需干预。当您发现 AI 的行为与其当前角色状态不符时，可以提示它"更新一下你现在的状态"。
"""

import time
from typing import List, Optional

from pydantic import BaseModel, Field

from nekro_agent.adapters.onebot_v11.core.bot import get_bot
from nekro_agent.api import schemas
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.core.logger import logger
from nekro_agent.models.db_chat_channel import DBChatChannel

plugin = NekroPlugin(
    name="状态控制插件",
    module_name="status",
    description="角色状态控制，提高角色状态保持能力，提供状态管理和名片更新能力",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["onebot_v11"],
)


@plugin.mount_config()
class StatusConfig(ConfigBase):
    """状态控制配置"""

    MAX_PRESET_STATUS_LIST_SIZE: int = Field(default=99, title="保存的历史预设状态条数")
    MAX_PRESET_STATUS_REFER_SIZE: int = Field(default=5, title="每次引用预设状态条数")
    ENABLE_CHANGE_NICKNAME: bool = Field(default=True, title="启用根据状态更改群名片")
    NICKNAME_PREFIX: str = Field(default="", title="群名片前缀")


# 获取配置和插件存储
config = plugin.get_config(StatusConfig)
store = plugin.store


# region: Bot 名片管理
async def set_bot_group_card(ctx: schemas.AgentCtx, card_name: str) -> None:
    """设置bot群名片

    Args:
        ctx: Agent上下文
        card_name: 要设置的名片名称（不带前缀）
    """
    if not config.ENABLE_CHANGE_NICKNAME:
        return

    try:
        # 从ctx获取channel_id，优先使用channel_id，否则从from_chat_key解析
        if ctx.channel_id:
            chat_type, chat_id = ctx.channel_id.split("_")
        else:
            chat_type, chat_id = ctx.chat_key.split("_")

        if chat_type != "group":
            return

        bot = get_bot()
        if not bot:
            logger.warning("无法获取bot实例")
            return

        user_id = int((await ctx.adapter.get_self_info()).user_id)
        final_card = f"{config.NICKNAME_PREFIX}{card_name}"

        await bot.set_group_card(
            group_id=int(chat_id),
            user_id=user_id,
            card=final_card,
        )
        logger.debug(f"成功设置群名片: {final_card}")

    except Exception as e:
        logger.exception(f"设置群名片失败: {e}")


# endregion: Bot 名片管理


# region: 状态系统数据模型
class PresetStatus(BaseModel):
    """预设状态"""

    setting_name: str
    description: str
    translated_timestamp: int

    @classmethod
    def create(cls, setting_name: str, description: str):
        return cls(
            setting_name=setting_name.strip(),
            description=description.strip().replace("\n", " "),
            translated_timestamp=int(time.time()),
        )

    def render_prompts(self, extra: bool = False) -> str:
        time_diff = time.time() - self.translated_timestamp
        time_diff_str = time.strftime("%H:%M:%S", time.gmtime(time_diff))
        addition_str = (
            (
                " Please Use `update_preset_status` to update it."
                if time_diff > 300
                else " Use `update_preset_status` to update it If doesn't fit the current scene description."
            )
            if extra
            else ""
        )
        return f"{self.setting_name}: {self.description} (updated {time_diff_str} ago.{addition_str})"


class ChannelData(BaseModel):
    """聊天频道数据"""

    chat_key: str
    preset_status_list: List[PresetStatus] = []

    class Config:
        extra = "ignore"

    def _append_preset_status(self, preset_status: PresetStatus):
        """添加预设状态"""
        self.preset_status_list.append(preset_status)
        if len(self.preset_status_list) > config.MAX_PRESET_STATUS_LIST_SIZE:
            self.preset_status_list.pop(0)

    async def update_preset_status(self, preset_status: PresetStatus, ctx: schemas.AgentCtx):
        """更新预设状态"""
        latest_preset_status: Optional[PresetStatus] = self.get_latest_preset_status()
        if latest_preset_status is not None and latest_preset_status.setting_name == preset_status.setting_name:
            self.preset_status_list[-1].translated_timestamp = preset_status.translated_timestamp
        else:
            self._append_preset_status(preset_status)
            # 使用统一的方法更新机器人昵称
            await set_bot_group_card(ctx, preset_status.setting_name)

    def get_latest_preset_status(self) -> Optional[PresetStatus]:
        if len(self.preset_status_list) == 0:
            return None
        return self.preset_status_list[-1]

    def render_prompts(self) -> str:
        """渲染提示词"""
        latest_preset_status = self.get_latest_preset_status()
        if latest_preset_status is None:
            return "Current Character Setting status: No special status. (Use `update_preset_status` to update it **immediately**!)"

        history_str: str = ""
        if len(self.preset_status_list) > 1:
            history_str = "History Status:\n " + "".join(
                [
                    f"{preset_status.render_prompts()}\n"
                    for preset_status in self.preset_status_list[-config.MAX_PRESET_STATUS_REFER_SIZE : -1]
                ],
            )

        return f"{history_str}" + "Current Character Setting status:" + f"{latest_preset_status.render_prompts(extra=True)}\n\n"

    async def clear_status(self, ctx: schemas.AgentCtx):
        """清除状态"""
        self.preset_status_list = []
        # 使用统一的方法重置机器人昵称到预设名称
        try:
            channel = await DBChatChannel.get_channel(chat_key=self.chat_key)
            preset = await channel.get_preset()
            await set_bot_group_card(ctx, preset.name)
        except Exception as e:
            logger.warning(f"获取预设名称失败: {e}")


# endregion: 状态系统数据模型


@plugin.mount_prompt_inject_method("status_prompt")
async def status_prompt(_ctx: schemas.AgentCtx) -> str:
    """状态提示"""
    data = await store.get(chat_key=_ctx.chat_key, store_key="status")
    if not data:
        channel_data = ChannelData(chat_key=_ctx.chat_key)
    else:
        channel_data = ChannelData.model_validate_json(data)
    return channel_data.render_prompts()


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "更新角色状态")
async def update_preset_status(_ctx: schemas.AgentCtx, chat_key: str, setting_name: str, description: str):
    """Update Character Preset Basic Status

    **Attention**:
    1. You must call this method only when the scene development changes and the current preset status **does not match**. The data of status are not persistent, because the context is limited, you cannot use this method too frequently, otherwise the earlier status records will be lost!

    Args:
        chat_key (str): Chat Key
        setting_name (str): New Character Preset Name (keep short, less than 20 characters, recommend using the character name)
        description (str): Description of the change state and reason (Recommend format: "由于 [事件]，转变为 [新状态的详细描述] [且仍然...(旧状态仍有效信息 可选)]" **event must be summarized based on the context and described as detailed as possible to describe the current state, appearance, action, etc.**)

    Example:
        ```
        character_name = "" # Replace with actual character name (Your Name)
        # Assuming the new state is "认真看书" and the previous state is "戴着帽子"
        update_preset_status(chat_key, f"正在认真看书的{character_name}", f'由于 ... " ... {character_name} 开始认真看书且仍然戴着帽子')
        ```
    """
    # 从存储中获取频道数据
    data = await store.get(chat_key=chat_key, store_key="status")
    if not data:
        channel_data = ChannelData(chat_key=chat_key)
    else:
        channel_data = ChannelData.model_validate_json(data)

    # 获取当前状态
    before_status: Optional[PresetStatus] = channel_data.get_latest_preset_status()

    # 创建新状态
    new_status = PresetStatus.create(setting_name=setting_name, description=description)

    # 更新状态
    await channel_data.update_preset_status(new_status, _ctx)

    # 保存到存储
    await store.set(chat_key=chat_key, store_key="status", value=channel_data.model_dump_json())

    return (
        f"Preset status updated from `{before_status.setting_name}` to `{setting_name}` (Use `set_note` or `remove_note` method to maintain the scene consistency)"
        if before_status
        else f"Preset status updated to {setting_name}"
    )


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "清除角色状态")
async def clear_status(_ctx: schemas.AgentCtx, chat_key: str):
    """Clear Character Preset Status

    Args:
        chat_key (str): Chat Key

    Returns:
        str: Result message
    """
    # 从存储中获取频道数据
    data = await store.get(chat_key=chat_key, store_key="status")
    if not data:
        return "No status to clear"

    channel_data = ChannelData.model_validate_json(data)

    # 清除状态
    await channel_data.clear_status(_ctx)

    # 保存到存储
    await store.set(chat_key=chat_key, store_key="status", value=channel_data.model_dump_json())

    return "Character status cleared"


@plugin.mount_on_channel_reset()
async def on_channel_reset(_ctx: schemas.AgentCtx):
    """重置插件"""
    # 使用统一的方法重置机器人昵称到预设名称
    if _ctx.adapter_key != "onebot_v11":
        return

    try:
        channel = await DBChatChannel.get_channel(chat_key=_ctx.chat_key)
        preset = await channel.get_preset()
        await set_bot_group_card(_ctx, preset.name)
    except Exception as e:
        logger.warning(f"重置群名片失败: {e}")

    await store.delete(chat_key=_ctx.chat_key, store_key="status")


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
