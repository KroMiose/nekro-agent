import time
from typing import Optional

from nekro_agent.api import core, schemas
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_channel import ChannelData, PresetNote, PresetStatus

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

    **注意**:
    1. 你必须在**当且仅当**场景发展变化导致**不符合**当前设定状态时调用此方法来更新自身状态, 由于上下文有限，你不能过度频繁使用此方法，否则会丢失较早的状态记录!
    2. 通常与 `set_note` / `remove_note` 配合使用实现持久化记忆

    Args:
        chat_key (str): 会话标识
        setting_name (str): 新状态的人设名 (less than 20 characters)
        description (str): 变化状态描述与原因 (推荐格式 "由于 [事件]，转变为 [新状态的详细描述] [且仍然...(旧状态仍有效信息 可选)]" **事件必须基于上下文进行总结描述尽可能详细地说明人物当前状态、外观、动作等信息**)

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


@core.agent_collector.mount_method(core.MethodType.TOOL)
async def set_note(chat_key: str, title: str, description: str, duration: int, _ctx: schemas.AgentCtx) -> bool:
    """设置状态笔记 适用于 "外观外貌"、"身体部位"、"心理状态" 等效果

    注意: 你所看到的聊天记录均是**有长度限制的滚动呈现**，因此务必及时记住对话中的重要信息，否则会丢失记录!
    This is the ** MOST RECOMMENDED ** way to manage persistent information.

    Args:
        chat_key (str): 会话标识
        title (str): 笔记标题 (Update following arguments if specified `title` already exists)
        description (str): 详细描述 (Recommend format: "[tag] ...(effect description)")
        duration (int): 持续时间 (seconds, 0 means infinite)

    Returns:
        bool: 是否成功

    Example:
        ```
        # 由于某种原因，你变得 "开心"
        set_note(chat_key, "心情愉悦", "[效果] 因为 ...(事件发生) 而感到开心, ...(更多效果描述)", 60*60)
        # 由于摔倒，你的手臂受伤了
        set_note(chat_key, "手臂受伤", "[效果] 因为摔倒而受伤，情况很严重，需要及时治疗", 0)

        # 维护一些自己或他人的状态变量
        set_note(chat_key, "正在维护xxx的财务状况", "[规则] 我正在维护xxx的财务状况, ... (detail scene rules)", 0)
        last_money_yuan = 50
        spend_money_yuan = 10
        if last_money_yuan - spend_money_yuan > 0:
            set_note(chat_key, "xxx的财务状况", "[变量] 剩余 {last_money_yuan - spend_money_yuan} 元", 0)

        # 记录关键信息
        set_note(chat_key, "xxx的电子邮箱", "[记忆] xxx@gmail.com", 0)
        ```
    """
    db_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key)
    channel_data: ChannelData = await db_channel.get_channel_data()
    await channel_data.update_preset_note(
        PresetNote.create(title=title, description=f"{description}", duration=duration),
    )
    await db_channel.save_channel_data(channel_data)

    return True


@core.agent_collector.mount_method(core.MethodType.TOOL)
async def get_note(chat_key: str, title: str, _ctx: schemas.AgentCtx) -> str:
    """获取状态笔记

    Args:
        chat_key (str): 会话标识
        title (str): 笔记标题

    Returns:
        str: 笔记内容 (return empty string if note not found)

    Example:
        ```
        # 将 Note 作为 K-V 数据库使用
        import json
        if not get_note(chat_key, "some_data"):
            set_note(chat_key, "some_data", "{}", 0)
            set_note(chat_key, "some_data_schema", "...", 0) # note 内容过长时会省略显示, 保存一份结构描述笔记给自己参考
        data = json.loads(get_note(chat_key, "some_data"))
        data["xxx"] = "xxx"
        set_note(chat_key, "some_data", json.dumps(data, ensure_ascii=False), 0)
        ```
    """
    db_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key)
    channel_data: ChannelData = await db_channel.get_channel_data()
    note: Optional[PresetNote] = channel_data.get_preset_note(title, fuzzy=True)
    return note.description if note else ""


@core.agent_collector.mount_method(core.MethodType.BEHAVIOR)
async def remove_note(chat_key: str, title: str, _ctx: schemas.AgentCtx):
    """移除状态笔记

    Args:
        chat_key (str): 会话标识
        title (str): 被移除的笔记标题 (e.g. "心情愉悦" ... Must be exact match)

    Example:
        ```
        # 由于某种原因，"心情愉悦" 效果不再符合当前场景
        remove_note(chat_key, "心情愉悦")
        ```
    """
    db_channel: DBChatChannel = await DBChatChannel.get_channel(chat_key)
    channel_data: ChannelData = await db_channel.get_channel_data()
    success: bool = await channel_data.remove_preset_note(title, fuzzy=True)
    await db_channel.save_channel_data(channel_data)

    if success:
        return f"Note `{title}` removed"
    raise ValueError(f"Note `{title}` not found. Make sure the spelling is correct!")


async def clean_up():
    """清理扩展"""
