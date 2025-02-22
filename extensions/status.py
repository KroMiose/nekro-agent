import time
from typing import Optional

from nekro_agent.api import core, schemas
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_channel import ChannelData, PresetEffect, PresetStatus

__meta__ = core.ExtMetaData(
    name="status",
    description="[NA] 状态控制扩展",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@core.agent_collector.mount_method(core.MethodType.BEHAVIOR)
async def update_preset_status(chat_key: str, setting_name: str, description: str, _ctx: schemas.AgentCtx):
    """更新人物设定基本状态

    **注意**: 你必须在**当且仅当**场景发展变化导致**不符合**当前设定状态时调用此方法来更新自身状态 (通常与 `set_effect` / `remove_effect` 配合使用)；由于上下文有限，你不能过度频繁使用此方法，否则会丢失较早的状态记录!

    Args:
        chat_key (str): 会话标识
        setting_name (str): 新状态的人设名 (less than 20 characters)
        description (str): 变化状态描述与原因 (推荐格式 "由于 [事件]，转变为 [新状态的详细描述] [且仍然...(旧状态仍有效信息 可选)]" **事件必须基于上下文进行总结描述尽可能详细地说明人物当前状态、外观、动作等信息**)

    Example:
        ```
        character_name = "" # 替换为实际人物设定 (你的名字)
        # 假设新状态为 "正在认真看书" 并保持之前 "戴着帽子" 的状态
        update_preset_status(chat_key, f"正在认真看书的{character_name}", f'由于 ... " ... 转变为 `正在认真看书的{character_name}` 且仍然戴着帽子')
        set_effect(chat_key, "戴着帽子", "戴着一顶可爱的帽子")  # 添加 "戴着帽子" 效果保持状态一致性
        ```
    """
    db_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key)
    channel_data: ChannelData = await db_channel.get_channel_data()
    before_status: Optional[PresetStatus] = channel_data.get_latest_preset_status()
    new_status = PresetStatus(setting_name=setting_name, description=description, translated_timestamp=int(time.time()))
    await channel_data.update_preset_status(new_status)
    await db_channel.save_channel_data(channel_data)

    return (
        f"Preset status updated from `{before_status.setting_name}` to `{setting_name}` (Use `set_effect` or `remove_effect` method to maintain the scene consistency)"
        if before_status
        else f"Preset status updated to {setting_name}"
    )


@core.agent_collector.mount_method(core.MethodType.BEHAVIOR)
async def set_effect(chat_key: str, effect_name: str, description: str, _ctx: schemas.AgentCtx):
    """设置状态效果标签 适用于 "外观外貌"、"身体部位"、"心理状态" 等效果, 请**经常更新**你的角色的状态效果标签避免丢失记录

    Args:
        chat_key (str): 会话标识
        effect_name (str): 被设置的效果名 (e.g. "心情愉悦", "中毒")
        description (str): 效果的具体描述 (Update the description if specified effect already exists)

    Example:
        ```
        # 假设由于某种原因，你需要添加 "心情愉悦" 效果
        set_effect(chat_key, "心情愉悦", "因为 ...(事件发生) 而感到心情愉悦, ...(更多效果描述)")
        # 如果 "心情愉悦" 效果已经存在，该方法将会更新它的描述

        # 该方法还能用来维护一些自己或他人的状态变量
        last_money_yuan = 50
        spend_money_yuan = 10
        if last_money_yuan - spend_money_yuan > 0:
            set_effect(chat_key, "xxx的财务状况", f"剩余 {last_money_yuan - spend_money_yuan} 元")
        ```
    """
    db_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key)
    channel_data: ChannelData = await db_channel.get_channel_data()
    await channel_data.update_preset_effect(PresetEffect.create(effect_name=effect_name, description=description))
    await db_channel.save_channel_data(channel_data)

    return f"Effect `{effect_name}` added"


@core.agent_collector.mount_method(core.MethodType.BEHAVIOR)
async def remove_effect(chat_key: str, effect_name: str, _ctx: schemas.AgentCtx):
    """移除状态效果标签

    Args:
        chat_key (str): 会话标识
        effect_name (str): 被移除的效果名 (e.g. "精神饱满", "正在看书")

    Example:
        ```
        # 由于某种原因，"精神饱满" 效果不再符合当前场景，需要移除
        remove_effect(chat_key, "精神饱满")
        ```
    """
    db_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key)
    channel_data: ChannelData = await db_channel.get_channel_data()
    success: bool = await channel_data.remove_preset_effect(effect_name, fuzzy=True)
    await db_channel.save_channel_data(channel_data)

    if success:
        return f"Effect `{effect_name}` removed"
    raise ValueError(f"Effect `{effect_name}` not found. Make sure the spelling is correct!")


async def clean_up():
    """清理扩展"""
