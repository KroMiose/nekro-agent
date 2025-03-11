import time
from typing import Optional

from pydantic import Field

from nekro_agent.api import core, schemas
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_channel import ChannelData, PresetNote, PresetStatus
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

plugin = NekroPlugin(
    name="status",
    description="[NA] 状态控制插件",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_config()
class StatusConfig(ConfigBase):
    """状态控制配置"""

    some_field: str = Field(default="", title="一些配置")


# 获取配置
config = plugin.get_config(StatusConfig)


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "更新角色状态")
async def update_preset_status(chat_key: str, setting_name: str, description: str, _ctx: schemas.AgentCtx):
    """Update Character Preset Basic Status

    **Attention**:
    1. You must call this method only when the scene development changes and the current preset status **does not match**, because the context is limited, you cannot use this method too frequently, otherwise the earlier status records will be lost!
    2. Usually used in conjunction with `set_note` / `remove_note` to implement persistent memory

    Args:
        chat_key (str): Chat Key
        setting_name (str): New Character Preset Name (keep short, less than 20 characters)
        description (str): Description of the change state and reason (Recommend format: "由于 [事件]，转变为 [新状态的详细描述] [且仍然...(旧状态仍有效信息 可选)]" **event must be summarized based on the context and described as detailed as possible to describe the current state, appearance, action, etc.**)

    Example:
        ```
        character_name = "" # 替换为实际人物设定 (你的名字)
        # 假设新状态为 "认真看书" 并保持之前 "戴着帽子" 的状态
        update_preset_status(chat_key, f"正在认真看书的{character_name}", f'由于 ... " ... {character_name} 开始认真看书且仍然戴着帽子')
        set_note(chat_key, "戴着帽子", "戴着一顶可爱的帽子")  # 添加 "戴着帽子" 效果保持状态一致性
        ```
    """
    db_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key)
    channel_data: ChannelData = await db_channel.get_channel_data()
    before_status: Optional[PresetStatus] = channel_data.get_latest_preset_status()
    new_status = PresetStatus(
        setting_name=setting_name.strip(),
        description=description.strip().replace("\n", " "),
        translated_timestamp=int(time.time()),
    )
    await channel_data.update_preset_status(new_status)
    await db_channel.save_channel_data(channel_data)

    return (
        f"Preset status updated from `{before_status.setting_name}` to `{setting_name}` (Use `set_note` or `remove_note` method to maintain the scene consistency)"
        if before_status
        else f"Preset status updated to {setting_name}"
    )


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
