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
- 当用户告诉 AI 自己的邮箱时，AI 可能会用笔记记下："用户的邮箱是XX"。
- 在角色扮演中，当角色获得一个"受伤"状态时，AI 会用笔记记下："手臂受伤了，行动不便"，直到这个状态被解除。
- 它可以作为一个简单的键值数据库来存储和跟踪变量。
"""

import time
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from nekro_agent.api import core, i18n, schemas
from nekro_agent.api.plugin import (
    ConfigBase,
    ExtraField,
    NekroPlugin,
    SandboxMethodType,
)
from nekro_agent.models.db_chat_channel import DBChatChannel

plugin = NekroPlugin(
    name="笔记系统插件",
    module_name="note",
    description="提供笔记系统功能，支持设置、获取、删除笔记",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="笔记系统插件",
        en_US="Note System Plugin",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="提供笔记系统功能，支持设置、获取、删除笔记",
        en_US="Provides note system features including creating, retrieving and deleting notes",
    ),
    allow_sleep=False,
    sleep_brief="用于持久化记录和读取长期笔记，在需要跨轮次保存关键信息时激活。",
)


@plugin.mount_config()
class NoteConfig(ConfigBase):
    """笔记系统配置"""

    MAX_NOTE_LENGTH: int = Field(
        default=72,
        title="单条笔记最大显示长度",
        description="超出该长度时，会自动摘要显示",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="单条笔记最大显示长度",
                en_US="Max Note Display Length",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="超出该长度时，会自动摘要显示",
                en_US="Notes exceeding this length will be summarized for display",
            ),
        ).model_dump(),
    )
    NOTE_PROMPT_CLEAN_THRESHOLD: int = Field(
        default=12,
        title="笔记提示清理阈值",
        description="超出该长度时，会提示清理过期或无用的笔记",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="笔记提示清理阈值",
                en_US="Note Cleanup Threshold",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="超出该长度时，会提示清理过期或无用的笔记",
                en_US="When exceeded, prompt to clean up expired or unnecessary notes",
            ),
        ).model_dump(),
    )
    NOTE_DETAIL_INJECT_LIMIT: int = Field(
        default=50,
        title="详情注入条数上限",
        description="prompt中展开详情的最近笔记条数，超出部分仅显示标题列表",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="详情注入条数上限",
                en_US="Detail Inject Limit",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="prompt中展开详情的最近笔记条数，超出部分仅显示标题列表",
                en_US="Max number of recent notes with full detail in prompt; older notes show title only",
            ),
        ).model_dump(),
    )
    NOTE_DEDUP_SIMILARITY: float = Field(
        default=0.7,
        title="笔记去重相似度阈值",
        description="新笔记标题与已有笔记标题的相似度超过此值时，覆盖旧笔记而非新建",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="笔记去重相似度阈值",
                en_US="Note Dedup Similarity Threshold",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="新笔记标题与已有笔记标题的相似度超过此值时，覆盖旧笔记而非新建",
                en_US="When a new note title similarity exceeds this threshold against existing titles, the old note is replaced instead of creating a new one",
            ),
        ).model_dump(),
    )


# 获取配置和插件存储
config = plugin.get_config(NoteConfig)
store = plugin.store


def _title_similarity(a: str, b: str) -> float:
    """计算两个标题的相似度 (0~1)"""
    # 去除常见装饰字符后比较
    clean_a = a.replace("'", "").replace("'", "").replace("「", "").replace("」", "").strip()
    clean_b = b.replace("'", "").replace("'", "").replace("「", "").replace("」", "").strip()
    return SequenceMatcher(None, clean_a, clean_b).ratio()


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
        now = time.time()
        remaining = self.expire_time - now
        if self.duration > 0 and remaining > 0:
            extra_diff_str = f"expires in {time.strftime('%H:%M:%S', time.gmtime(remaining))}"
        elif self.duration > 0:
            expired_since = now - self.expire_time
            extra_diff_str = f"expired {time.strftime('%H:%M:%S', time.gmtime(expired_since))} ago (use `remove_note` to remove it)"
        else:
            extra_diff_str = "no expiry"
        description_str: str = (
            self.description
            if len(self.description) < config.MAX_NOTE_LENGTH
            else self.description[: config.MAX_NOTE_LENGTH // 2]
            + "...(note too long, use `get_note` to get the full note...)"
            + self.description[-config.MAX_NOTE_LENGTH // 2 :]
        )
        return f"* note_title: {self.title}\n* note_description: {description_str}\n* time: (started {time_diff_str} ago. {extra_diff_str})"

    def render_title_only(self) -> str:
        """仅渲染标题（用于超出详情注入上限的旧笔记）"""
        time_diff = time.time() - self.start_time
        days = int(time_diff // 86400)
        if days > 0:
            time_brief = f"{days}d ago"
        else:
            hours = int(time_diff // 3600)
            time_brief = f"{hours}h ago" if hours > 0 else "recent"
        return f"  - {self.title} ({time_brief})"


class ChannelNoteData(BaseModel):
    """聊天频道数据"""

    notes: Dict[str, Note] = {}

    class Config:
        extra = "ignore"

    def _find_similar_title(self, title: str) -> Optional[str]:
        """查找与给定标题相似度超过阈值的已有标题，返回最相似的那个"""
        best_match: Optional[str] = None
        best_score: float = 0.0
        threshold = config.NOTE_DEDUP_SIMILARITY

        for existing_title in self.notes:
            if existing_title == title:
                # 完全匹配直接返回（原有逻辑：同标题覆盖）
                return existing_title
            score = _title_similarity(title, existing_title)
            if score > threshold and score > best_score:
                best_score = score
                best_match = existing_title

        return best_match

    async def update_note(self, note: Note):
        """更新笔记（含去重逻辑）"""
        # 先检查是否有相似标题的旧笔记
        similar_title = self._find_similar_title(note.title)
        if similar_title and similar_title != note.title:
            # 删除旧的相似笔记，用新笔记替代
            del self.notes[similar_title]
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
        """渲染提示词（分层注入：最近N条展开详情，其余仅标题列表）"""

        if len(self.notes) == 0:
            return "No notes. (use `set_note` to add one)"

        detail_limit = config.NOTE_DETAIL_INJECT_LIMIT
        all_notes: List[Note] = list(self.notes.values())

        # 按 start_time 排序，最新的在后面
        all_notes_sorted = sorted(all_notes, key=lambda n: n.start_time)

        total = len(all_notes_sorted)

        if total <= detail_limit:
            # 全部展开详情（原有行为）
            note_str = "".join(
                [f"* {note.render_prompts()}\n" for note in all_notes_sorted]
            )
        else:
            # 分层：旧笔记只显示标题，最近 N 条展开详情
            older_notes = all_notes_sorted[: total - detail_limit]
            recent_notes = all_notes_sorted[total - detail_limit :]

            older_section = f"[Older notes ({len(older_notes)} items — ONLY TITLES SHOWN. You MUST call `get_note(chat_key, title)` to retrieve full content before referencing any of these notes.)]\n"
            older_section += "\n".join([note.render_title_only() for note in older_notes])
            older_section += "\n\n"

            recent_section = f"[Recent notes ({len(recent_notes)} items, full details)]\n"
            recent_section += "".join(
                [f"* {note.render_prompts()}\n" for note in recent_notes]
            )

            note_str = older_section + recent_section

        note_warning_str: str = (
            "Warning: You have too many notes. (use `remove_note` to remove some expired or useless notes)"
            if total > config.NOTE_PROMPT_CLEAN_THRESHOLD
            else ""
        )

        return note_str + ("\n" + note_warning_str if note_warning_str else "")


# endregion: 笔记系统数据模型


@plugin.mount_prompt_inject_method("note_prompt")
async def note_prompt(_ctx: schemas.AgentCtx) -> str:
    """笔记提示"""
    data = await store.get(chat_key=_ctx.chat_key, store_key="note")
    channel_data: ChannelNoteData = ChannelNoteData.model_validate_json(data) if data else ChannelNoteData()
    return "Current Notes:\n" + channel_data.render_prompts()


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "获取笔记")
async def get_note(_ctx: schemas.AgentCtx, chat_key: str, title: str) -> str:
    """Get Note

    Retrieve the full content of a note by title. Use this for older notes that only show titles in the prompt,
    or for notes that are too long and got truncated.

    **IMPORTANT**: Results are NOT preserved across execution rounds. You MUST call get_note AND use the result
    (e.g. in send_msg_text) in the SAME code block. Do NOT call get_note alone expecting to use it later.

    Args:
        chat_key (str): Chat Key
        title (str): Note Title (supports fuzzy match)

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
    """Set Note (适用于 "外观外貌"、"身体"、"心理"、"物品" 等效果)

    **Attention**: ALL the chat records you see are **SCROLLING WINDOW** with a length limit, so make sure to remember the important information, otherwise it will be lost!
    This is the ** MOST RECOMMENDED ** way to manage persistent information.

    Note: If a note with a very similar title already exists, it will be automatically replaced (deduplication).

    Args:
        chat_key (str): Chat Key
        title (str): Note Title (Update following arguments if specified `title` already exists; similar titles will be deduplicated)
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
