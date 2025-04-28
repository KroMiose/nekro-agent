import time
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from nekro_agent.api import core, schemas
from nekro_agent.core.bot import get_bot
from nekro_agent.core.config import config as global_config
from nekro_agent.core.logger import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

plugin = NekroPlugin(
    name="状态控制插件",
    module_name="status",
    description="角色状态控制，提高角色状态保持能力，提供状态管理和名片更新能力",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
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

    async def update_preset_status(self, preset_status: PresetStatus):
        """更新预设状态"""
        latest_preset_status: Optional[PresetStatus] = self.get_latest_preset_status()
        if latest_preset_status is not None and latest_preset_status.setting_name == preset_status.setting_name:
            self.preset_status_list[-1].translated_timestamp = preset_status.translated_timestamp
        else:
            self._append_preset_status(preset_status)
            try:
                # 尝试更新机器人昵称
                if config.ENABLE_CHANGE_NICKNAME:
                    chat_type, chat_id = self.chat_key.split("_")
                    if chat_type == "group":
                        try:
                            bot = get_bot()  # 移除 await，直接获取 bot 实例
                            if bot:
                                await bot.set_group_card(
                                    group_id=int(chat_id),
                                    user_id=int(global_config.BOT_QQ),
                                    card=f"{config.NICKNAME_PREFIX}{preset_status.setting_name}",
                                )
                        except Exception as e:
                            logger.warning(f"会话 {self.chat_key} 尝试更新群名片失败: {e}")
            except Exception as e:
                logger.warning(f"更新昵称失败: {e}")

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

    async def clear_status(self):
        """清除状态"""
        self.preset_status_list = []
        try:
            # 尝试重置机器人昵称
            if config.ENABLE_CHANGE_NICKNAME:
                chat_type, chat_id = self.chat_key.split("_")
                if chat_type == "group":
                    try:
                        bot = get_bot()  # 移除 await，直接获取 bot 实例
                        if bot:
                            await bot.set_group_card(
                                group_id=int(chat_id),
                                user_id=int(global_config.BOT_QQ),
                                card=f"{config.NICKNAME_PREFIX}{(await (await DBChatChannel.get_channel(chat_key=self.chat_key)).get_preset()).name}",
                            )
                    except Exception as e:
                        logger.warning(f"会话 {self.chat_key} 尝试重置群名片失败: {e}")
        except Exception as e:
            logger.warning(f"重置昵称失败: {e}")

    @property
    def chat_type(self) -> ChatType:
        """获取聊天频道类型"""
        return ChatType.from_chat_key(self.chat_key)


# endregion: 状态系统数据模型


@plugin.mount_prompt_inject_method("status_prompt")
async def status_prompt(_ctx: schemas.AgentCtx) -> str:
    """状态提示"""
    data = await store.get(chat_key=_ctx.from_chat_key, store_key="status")
    if not data:
        channel_data = ChannelData(chat_key=_ctx.from_chat_key)
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
    await channel_data.update_preset_status(new_status)

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
    await channel_data.clear_status()

    # 保存到存储
    await store.set(chat_key=chat_key, store_key="status", value=channel_data.model_dump_json())

    return "Character status cleared"


@plugin.mount_on_channel_reset()
async def on_channel_reset(_ctx: schemas.AgentCtx):
    """重置插件"""
    if config.ENABLE_CHANGE_NICKNAME:
        bot = get_bot()
        if bot:
            await bot.set_group_card(
                group_id=int(_ctx.from_chat_key.split("_")[1]),
                user_id=int(global_config.BOT_QQ),
                card=f"{config.NICKNAME_PREFIX}{(await (await DBChatChannel.get_channel(chat_key=_ctx.from_chat_key)).get_preset()).name}",
            )
    await store.delete(chat_key=_ctx.from_chat_key, store_key="status")


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
