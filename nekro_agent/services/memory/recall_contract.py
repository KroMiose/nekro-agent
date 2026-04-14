"""记忆检索规划契约与统一常量。"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MemoryIntentType(StrEnum):
    DECISION_RECALL = "decision_recall"
    FACT_LOOKUP = "fact_lookup"
    PREFERENCE_RECALL = "preference_recall"
    EXPERIENCE_RECALL = "experience_recall"
    CONVERSATION_RECALL = "conversation_recall"
    RELATION_LOOKUP = "relation_lookup"
    MIXED = "mixed"


class MemoryAnswerStyle(StrEnum):
    CORE_ONLY = "core_only"
    CORE_PLUS_EVIDENCE = "core_plus_evidence"
    TIMELINE = "timeline"
    PREFERENCE_SUMMARY = "preference_summary"


class MemoryTypeHint(StrEnum):
    PARAGRAPH = "paragraph"
    EPISODE = "episode"
    RELATION = "relation"


class MemoryKnowledgeHint(StrEnum):
    DECISION = "decision"
    FACT = "fact"
    PREFERENCE = "preference"
    EXPERIENCE = "experience"
    CONVERSATION = "conversation"
    EMOTION = "emotion"
    RELATION = "relation"


class MemoryRecallQuerySpec(BaseModel):
    query_text: str
    focus_text: str = ""
    focus_points: list[str] = Field(default_factory=list)
    context_texts: list[str] = Field(default_factory=list)
    target_memory_types: list[MemoryTypeHint] = Field(default_factory=list)
    target_knowledge_types: list[MemoryKnowledgeHint] = Field(default_factory=list)
    importance: float = 1.0
    time_from: datetime | None = None
    time_to: datetime | None = None


class MemoryRecallPlan(BaseModel):
    intent_type: MemoryIntentType = MemoryIntentType.MIXED
    answer_style: MemoryAnswerStyle = MemoryAnswerStyle.CORE_PLUS_EVIDENCE
    prefer_memory_types: list[MemoryTypeHint] = Field(default_factory=list)
    prefer_knowledge_types: list[MemoryKnowledgeHint] = Field(default_factory=list)
    avoid_knowledge_types: list[MemoryKnowledgeHint] = Field(default_factory=list)
    entity_hints: list[str] = Field(default_factory=list)
    queries: list[MemoryRecallQuerySpec] = Field(default_factory=list)


MEMORY_CONTEXT_BLOCK_TITLE = "[相关记忆]"
MEMORY_CONTEXT_FOCUS_TITLE = "当前关注："
MEMORY_CONTEXT_CORE_SECTION = "核心记忆："
MEMORY_CONTEXT_EVIDENCE_SECTION = "支撑线索："

MEMORY_CONTEXT_CATEGORY_LABELS: dict[MemoryKnowledgeHint, str] = {
    MemoryKnowledgeHint.DECISION: "决策",
    MemoryKnowledgeHint.FACT: "事实",
    MemoryKnowledgeHint.PREFERENCE: "偏好",
    MemoryKnowledgeHint.EXPERIENCE: "经验",
    MemoryKnowledgeHint.CONVERSATION: "对话",
    MemoryKnowledgeHint.EMOTION: "情绪",
    MemoryKnowledgeHint.RELATION: "关系",
}


ENHANCED_RECALL_SYSTEM_PROMPT = (
    "你是一个记忆检索规划助手，负责为历史记忆检索生成结构化查询计划。"
)


def build_enhanced_recall_user_prompt(conversation_lines: list[str]) -> str:
    return (
        "请根据最近对话，为记忆检索生成结构化检索计划。\n"
        "目标：找出与当前用户真实关注点相关的历史记忆，而不是机械重复最后一句话。\n"
        "要求：\n"
        "1. 结合最近多轮对话理解用户当前任务。\n"
        "2. 如果最后一句信息量弱，应向前补全真实关注点。\n"
        "3. 可以输出 1 到 3 组 queries，用于不同角度召回。\n"
        "4. 每组 query_text 必须是自然语言检索语句，避免只有关键词堆砌。\n"
        "5. focus_points 应提炼关键约束、实体、目标或问题点。\n"
        "6. context_texts 应包含支撑该检索意图的近期上下文短句。\n"
        "7. 只有在最近对话明确出现时间线索时，才填写 time_from / time_to，否则填 null。\n"
        "8. 额外输出 intent_type、answer_style、prefer_memory_types、prefer_knowledge_types、avoid_knowledge_types、entity_hints。\n"
        "9. intent_type 仅允许: decision_recall, fact_lookup, preference_recall, experience_recall, conversation_recall, relation_lookup, mixed。\n"
        "10. answer_style 仅允许: core_only, core_plus_evidence, timeline, preference_summary。\n"
        "11. prefer_memory_types 仅允许: paragraph, episode, relation。\n"
        "12. prefer_knowledge_types / avoid_knowledge_types 仅允许: decision, fact, preference, experience, conversation, emotion, relation。\n"
        "13. 每组 query 可附带 target_memory_types、target_knowledge_types、importance。\n"
        '14. 严格输出 JSON，对象格式为 {"queries":[...] }。\n'
        "15. 如果最近对话不足以构造有效检索计划，返回空数组 queries。\n\n"
        "JSON Schema:\n"
        "{\n"
        '  "intent_type": "mixed",\n'
        '  "answer_style": "core_plus_evidence",\n'
        '  "prefer_memory_types": ["paragraph"],\n'
        '  "prefer_knowledge_types": ["fact"],\n'
        '  "avoid_knowledge_types": ["emotion"],\n'
        '  "entity_hints": ["关键实体"],\n'
        '  "queries": [\n'
        "    {\n"
        '      "query_text": "自然语言检索语句",\n'
        '      "focus_text": "本组检索的核心关注点",\n'
        '      "focus_points": ["关键点1", "关键点2"],\n'
        '      "context_texts": ["相关上下文1", "相关上下文2"],\n'
        '      "target_memory_types": ["paragraph"],\n'
        '      "target_knowledge_types": ["fact"],\n'
        '      "importance": 1.0,\n'
        '      "time_from": null,\n'
        '      "time_to": null\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "最近对话：\n"
        + "\n".join(conversation_lines)
    )
