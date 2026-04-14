"""CC Prompt 元信息封装

将发给 CC 的 prompt 中的结构化元信息（时间、来源频道、记忆握手、系统附加段等）
与实际任务正文分离，方便日志存储和前端结构化渲染。

对 CC 侧完全透明：to_prompt() 输出格式与改造前完全一致，CC sandbox 无感知。
"""

import json
from dataclasses import dataclass, field


@dataclass
class CcPromptMeta:
    """发送给 CC 时注入的元信息摘要，用于日志存储和前端渲染。"""

    current_time: str
    """本机时区格式化的当前时间，如 "2026-04-10 15:30 CST"。"""

    source_chat_key: str
    """任务来源频道 chat_key；用户直发时为 "__user__"。"""

    memory_count: int = 0
    """注入的语义记忆条数（仅用户直发路径有）。"""

    has_context_overflow: bool = False
    """_na_context.md 是否因超限而附加了整理指令。"""

    has_manual_context_note: bool = False
    """_na_context.md 是否因用户手动修订而附加了注意事项。"""


@dataclass
class CcPromptEnvelope:
    """一次 CC 任务委托的完整 prompt 封装。

    Fields
    ------
    meta          元信息（时间、来源频道等）
    task_body     用户/NA 的实际任务正文，不含任何元信息前缀
    memory_lines  语义记忆握手列表（仅用户直发路径）
    system_notes  系统附加段文本列表（_na_context 超限 / 手动修订提示等）
    """

    meta: CcPromptMeta
    task_body: str
    memory_lines: list[str] = field(default_factory=list)
    system_notes: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # 构造辅助方法
    # ------------------------------------------------------------------

    @classmethod
    def for_na_path(
        cls,
        *,
        source_chat_key: str,
        current_time: str,
        task_body: str,
        system_notes: list[str] | None = None,
        has_context_overflow: bool = False,
        has_manual_context_note: bool = False,
    ) -> "CcPromptEnvelope":
        """为 NA → CC 委托路径构建封装（无记忆握手）。"""
        return cls(
            meta=CcPromptMeta(
                current_time=current_time,
                source_chat_key=source_chat_key,
                has_context_overflow=has_context_overflow,
                has_manual_context_note=has_manual_context_note,
            ),
            task_body=task_body,
            memory_lines=[],
            system_notes=system_notes or [],
        )

    @classmethod
    def for_user_path(
        cls,
        *,
        current_time: str,
        task_body: str,
        memory_lines: list[str] | None = None,
    ) -> "CcPromptEnvelope":
        """为用户直发路径构建封装（含记忆握手，无来源频道前缀）。"""
        return cls(
            meta=CcPromptMeta(
                current_time=current_time,
                source_chat_key="__user__",
                memory_count=len(memory_lines or []),
            ),
            task_body=task_body,
            memory_lines=memory_lines or [],
            system_notes=[],
        )

    # ------------------------------------------------------------------
    # 输出方法
    # ------------------------------------------------------------------

    def to_prompt(self) -> str:
        """生成发送给 CC 的完整 prompt 字符串。

        NA 路径格式（与改造前完全一致）：
            [任务来源频道: {key}] [当前时间: {time}]

            {task_body}

            ---
            [系统附加] ...（若有）

        用户直发路径格式（与改造前完全一致）：
            [当前时间: {time}]

            [统一记忆握手]
            ...记忆列表...（若有）

            [当前任务]
            {task_body}
        """
        if self.meta.source_chat_key != "__user__":
            # NA 路径
            header = f"[任务来源频道: {self.meta.source_chat_key}] [当前时间: {self.meta.current_time}]"
            parts = [header, "", self.task_body]
            for note in self.system_notes:
                parts.extend(["", "---", note])
            return "\n".join(parts)
        else:
            # 用户直发路径
            time_header = f"[当前时间: {self.meta.current_time}]"
            if not self.memory_lines:
                return f"{time_header}\n\n{self.task_body}"
            memory_block = (
                "[统一记忆握手]\n"
                "以下内容来自当前工作区的历史记忆，请在执行任务时优先参考；若与工作区现状冲突，以实际工作区状态为准。\n"
                + "\n".join(self.memory_lines)
            )
            return f"{time_header}\n\n{memory_block}\n\n[当前任务]\n{self.task_body}"

    def to_metadata_json(self) -> str:
        """序列化为存入 DBWorkspaceCommLog.extra_data 的 JSON 字符串。"""
        return json.dumps(
            {
                "current_time": self.meta.current_time,
                "source_chat_key": self.meta.source_chat_key,
                "memory_count": self.meta.memory_count,
                "has_context_overflow": self.meta.has_context_overflow,
                "has_manual_context_note": self.meta.has_manual_context_note,
            },
            ensure_ascii=False,
        )
