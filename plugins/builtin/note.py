"""
# 笔记 (Note)

为 AI 提供一个强大的、持久化的长期记忆系统，解决其对话上下文长度有限的"失忆"问题。

## 设计理念：外置记忆

AI 的对话记忆是滚动的、有长度限制的，就像一个只能记住最近几分钟事情的人。为了让 AI 能够记住关键信息（如用户偏好、重要约定、长期存在的角色状态等），这个笔记插件充当了它的"外置大脑"。

AI 可以将任何需要长期记住的信息，以"标题-内容"的形式记录为一条笔记。这些笔记会被永久保存，并在每次对话开始前自动"提醒"AI，确保它能基于这些关键记忆来与用户互动。

## 主要功能

- **记录笔记**: AI 可以随时将信息记录为一条笔记，并可以设置一个可选的"有效期"。
- **查询笔记**: AI 可以根据标题查询某条笔记的详细内容。
- **删除笔记**: 当一条信息不再重要或已过期时，AI 可以将其删除。
- **状态提示**: 插件会自动将当前所有的笔记列表注入到提示词中，让 AI 时刻清楚地知道自己记住了哪些事情。

## 使用方法

此插件主要由 AI 在后台自动使用。例如：
- 当用户告诉 AI 自己的昵称时，AI 可能会用笔记记下："用户的昵称是XX"。
- 在角色扮演中，当角色获得一个"受伤"状态时，AI 会用笔记记下："手臂受伤了，行动不便"，直到这个状态被解除。
- 它可以作为一个简单的键值数据库来存储和跟踪变量。
"""

import time
from typing import Dict, Optional

from pydantic import BaseModel, Field

from nekro_agent.api import core, schemas
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.models.db_chat_channel import DBChatChannel

plugin = NekroPlugin(
    name="笔记系统插件",
    module_name="note",
    description="提供笔记系统功能，支持设置、获取、删除笔记",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_config()
class NoteConfig(ConfigBase):
    """笔记系统配置"""

    MAX_NOTE_LENGTH: int = Field(default=72, title="单条笔记最大显示长度", description="超出该长度时，会自动摘要显示")
    NOTE_PROMPT_CLEAN_THRESHOLD: int = Field(
        default=12,
        title="笔记提示清理阈值",
        description="超出该长度时，会提示清理过期或无用的笔记",
    )


# 获取配置和插件存储
config = plugin.get_config(NoteConfig)
store = plugin.store


# region: 笔记系统数据模型
class Note(BaseModel):
    """预设状态笔记"""

    title: str
    description: str
    duration: int = 0
    start_time: int
    expire_time: int = 0

    @classmethod
    def create(cls, title: str, description: str, duration: int = 0):
        start_time = int(time.time())
        expire_time = start_time + duration if duration > 0 else 0
        return cls(
            title=title,
            description=description,
            start_time=start_time,
            expire_time=expire_time,
            duration=duration,
        )

    def render_prompts(self) -> str:
        time_diff = time.time() - self.start_time
        time_diff_str = time.strftime("%H:%M:%S", time.gmtime(time_diff))
        extra_diff = time.time() - self.expire_time
        if self.duration > 0 and extra_diff > 0:
            extra_diff_str = f"expires in {time.strftime('%H:%M:%S', time.gmtime(extra_diff))}"
        else:
            extra_diff_str = "expired (use `remove_note` to remove it)"
        description_str: str = (
            self.description
            if len(self.description) < config.MAX_NOTE_LENGTH
            else self.description[: config.MAX_NOTE_LENGTH // 2]
            + "...(note too long, use `get_note` to get the full note...)"
            + self.description[-config.MAX_NOTE_LENGTH // 2 :]
        )
        return f"* note_title: {self.title}\n* note_description: {description_str}\n* time: (started {time_diff_str} ago. {extra_diff_str})"


class ChannelNoteData(BaseModel):
    """聊天频道数据"""

    notes: Dict[str, Note] = {}

    class Config:
        extra = "ignore"

    async def update_note(self, note: Note):
        """更新笔记"""
        self.notes[note.title] = note

    async def remove_note(self, title: str, fuzzy: bool = False) -> bool:
        """移除笔记"""
        if title in self.notes:
            del self.notes[title]
            return True
        if fuzzy:
            for note in self.notes:
                _title = note.replace(" ", "").replace("<", "").replace(">", "")
                if title.replace(" ", "").replace("<", "").replace(">", "") in _title:
                    del self.notes[note]
                    return True
        return False

    def get_note(self, title: str, fuzzy: bool = False) -> Optional[Note]:
        """获取笔记"""
        if title in self.notes:
            return self.notes[title]
        if fuzzy:
            for note in self.notes:
                _title = note.replace(" ", "").replace("<", "").replace(">", "")
                if title.replace(" ", "").replace("<", "").replace(">", "") in _title:
                    return self.notes[note]
        return None

    def render_prompts(self) -> str:
        """渲染提示词"""

        note_str: str = (
            "".join(
                [f"* {note.render_prompts()}\n" for note in list(self.notes.values())],
            )
            if len(self.notes) > 0
            else "No notes. (use `set_note` to add one)"
        )

        note_warning_str: str = (
            "Warning: You have too many notes. (use `remove_note` to remove some expired or useless notes)"
            if len(self.notes) > config.NOTE_PROMPT_CLEAN_THRESHOLD
            else ""
        )

        return "Current Notes:\n" + note_str + "\n" + note_warning_str


# endregion: 笔记系统数据模型


@plugin.mount_prompt_inject_method("note_prompt")
async def note_prompt(_ctx: schemas.AgentCtx) -> str:
    """笔记提示"""
    data = await store.get(chat_key=_ctx.chat_key, store_key="note")
    channel_data: ChannelNoteData = ChannelNoteData.model_validate_json(data) if data else ChannelNoteData()
    return "Current Notes:\n" + channel_data.render_prompts()


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "获取状态笔记")
async def get_note(_ctx: schemas.AgentCtx, chat_key: str, title: str) -> str:
    """Get Note

    Only for too long notes, you can use the method to get the full content.

    Args:
        chat_key (str): Chat Key
        title (str): Note Title

    Returns:
        str: Note Content (return empty string if note not found)

    Example:
        ```
        # You can also use Note System as a K-V database
        import json
        if not get_note(chat_key, "some_data"):
            set_note(chat_key, "some_data", "{}", 0)
            set_note(chat_key, "some_data_schema", "...", 0) # save a structure description note for reference
        data = json.loads(get_note(chat_key, "some_data"))
        data["xxx"] = "xxx"
        set_note(chat_key, "some_data", json.dumps(data, ensure_ascii=False), 0)
        ```
    """
    data = await store.get(chat_key=chat_key, store_key="note")
    channel_data: ChannelNoteData = ChannelNoteData.model_validate_json(data) if data else ChannelNoteData()
    note: Optional[Note] = channel_data.get_note(title, fuzzy=True)
    return note.description if note else ""


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "设置状态笔记")
async def set_note(_ctx: schemas.AgentCtx, chat_key: str, title: str, description: str, duration: int = 0) -> bool:
    """Set Note (适用于 "外观外貌"、"身体部位"、"心理状态" 等效果)

    **Attention**: ALL the chat records you see are **SCROLLING WINDOW** with a length limit, so make sure to remember the important information, otherwise it will be lost!
    This is the ** MOST RECOMMENDED ** way to manage persistent information.

    Args:
        chat_key (str): Chat Key
        title (str): Note Title (Update following arguments if specified `title` already exists)
        description (str): Detailed Description (Recommend format: "[tag] ...(effect description)")
        duration (int): Duration (seconds, 0 means infinite, default is 0)

    Returns:
        bool: Successfully set note

    Example:
        ```
        # 由于某种原因，你变得 "开心"
        set_note(chat_key, "心情愉悦", "[效果] 因为 ...(事件发生) 而感到开心, ...(更多效果描述)", 60*60)
        # 由于摔倒，你的手臂受伤了
        set_note(chat_key, "手臂受伤", "[效果] 因为摔倒而受伤，情况很严重，需要及时治疗")

        # 维护一些自己或用户的状态变量
        set_note(chat_key, "正在维护xxx的财务状况", "[规则] 我正在维护xxx的财务状况, 使用...如果... (design and record very detail scene to keep remember operation rules)")
        last_money_yuan = 50
        spend_money_yuan = 10
        if last_money_yuan - spend_money_yuan > 0:
            set_note(chat_key, "xxx的财务状况", f"[变量] 剩余 {last_money_yuan - spend_money_yuan} 元")

        # 记录关键信息
        set_note(chat_key, "xxx的电子邮箱", "[记忆] xxx@qq.com")
        ```
    """
    data = await store.get(chat_key=chat_key, store_key="note")
    channel_data: ChannelNoteData = ChannelNoteData.model_validate_json(data) if data else ChannelNoteData()
    await channel_data.update_note(
        Note.create(title=title, description=f"{description}", duration=duration),
    )
    await store.set(chat_key=chat_key, store_key="note", value=channel_data.model_dump_json())

    return True


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "移除状态笔记")
async def remove_note(_ctx: schemas.AgentCtx, chat_key: str, title: str) -> str:
    """Remove Note

    Args:
        chat_key (str): Chat Key
        title (str): Note Title to be removed (e.g. "心情愉悦" ... Must be exact match)

    Example:
        ```
        # 由于某种原因，"心情愉悦" 效果不再符合当前场景
        remove_note(chat_key, "心情愉悦")
        ```
    """
    data = await store.get(chat_key=chat_key, store_key="note")
    channel_data: ChannelNoteData = ChannelNoteData.model_validate_json(data) if data else ChannelNoteData()
    success: bool = await channel_data.remove_note(title, fuzzy=True)
    await store.set(chat_key=chat_key, store_key="note", value=channel_data.model_dump_json())

    if success:
        return f"Note `{title}` removed"
    raise ValueError(f"Note `{title}` not found. Make sure the spelling is correct!")


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
