"""CC 语义记忆写入器。

将 CC 任务的输入与输出沉淀为长期语义记忆，供后续委托握手与检索复用。
"""

from __future__ import annotations

from datetime import datetime

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_mem_entity import DBMemEntity, EntityType, MemorySource
from nekro_agent.models.db_mem_paragraph import (
    CognitiveType,
    DBMemParagraph,
    KnowledgeType,
    OriginKind,
)
from nekro_agent.models.db_mem_relation import DBMemRelation
from nekro_agent.services.memory.embedding_service import embed_text
from nekro_agent.services.memory.feature_flags import is_memory_system_enabled
from nekro_agent.services.memory.qdrant_manager import memory_qdrant_manager

logger = get_sub_logger("memory.semantic_writer")


def _build_semantic_content(task_content: str, result_content: str) -> str:
    """构造用于沉淀的第三人称语义记忆文本。"""
    task = task_content.strip().replace("\n", " ")[: config.MEMORY_SEMANTIC_MAX_TASK_LENGTH]
    result = result_content.strip()[: config.MEMORY_SEMANTIC_MAX_RESULT_LENGTH]
    return f"CC 在当前工作区处理了任务“{task}”，并产出以下可复用结论或结果：\n{result}"


async def persist_cc_task_memory(
    workspace_id: int,
    task_content: str,
    result_content: str,
    source_chat_key: str = "__user__",
    origin_ref: str | None = None,
    event_time: datetime | None = None,
) -> DBMemParagraph | None:
    """将 CC 任务结果沉淀为语义记忆。"""
    if not is_memory_system_enabled():
        return None

    task = task_content.strip()
    result = result_content.strip()
    if not task or len(result) < config.MEMORY_SEMANTIC_MIN_RESULT_LENGTH:
        return None

    content = _build_semantic_content(task, result)
    summary = task[: config.MEMORY_SEMANTIC_MAX_SUMMARY_LENGTH]

    if origin_ref:
        existing = await DBMemParagraph.filter(
            workspace_id=workspace_id,
            memory_source="cc",
            cognitive_type=CognitiveType.SEMANTIC,
            origin_kind=OriginKind.TASK,
            origin_ref=origin_ref,
        ).first()
        if existing is not None:
            return existing

    paragraph = await DBMemParagraph.create(
        workspace_id=workspace_id,
        memory_source="cc",
        cognitive_type=CognitiveType.SEMANTIC,
        knowledge_type=KnowledgeType.EXPERIENCE,
        content=content,
        summary=summary,
        event_time=event_time or datetime.now(),
        half_life_seconds=config.MEMORY_SEMANTIC_HALF_LIFE_DAYS * 24 * 3600,
        origin_kind=OriginKind.TASK,
        origin_ref=origin_ref,
        origin_chat_key=source_chat_key,
    )

    try:
        embedding = await embed_text(content)
        await memory_qdrant_manager.upsert_paragraph(
            paragraph_id=paragraph.id,
            embedding=embedding,
            payload=paragraph.to_qdrant_payload(),
        )
        paragraph.embedding_ref = str(paragraph.id)
        await paragraph.save(update_fields=["embedding_ref"])
    except Exception as e:
        logger.warning(f"CC 语义记忆向量化失败，已仅保存数据库记录: {e}")

    logger.info(f"CC 语义记忆已沉淀: workspace={workspace_id}, paragraph_id={paragraph.id}")
    await _persist_cc_task_relations(workspace_id, paragraph.id, task, result)
    return paragraph


async def _persist_cc_task_relations(
    workspace_id: int,
    paragraph_id: int,
    task_content: str,
    result_content: str,
) -> None:
    """从 CC 任务文本中保守生成少量关系。"""
    task_tokens = [token.strip("`\"'“”[]()，。,.:：") for token in task_content.replace("\n", " ").split()]
    result_tokens = [token.strip("`\"'“”[]()，。,.:：") for token in result_content.replace("\n", " ").split()]
    merged = [token for token in task_tokens + result_tokens if 2 <= len(token) <= 32]

    seen: list[str] = []
    for token in merged:
        lowered = token.lower()
        if lowered not in seen:
            seen.append(lowered)
        if len(seen) >= 3:
            break

    if len(seen) < 2:
        return

    entities: list[DBMemEntity] = []
    for name in seen:
        entity, _ = await DBMemEntity.find_or_create(
            workspace_id=workspace_id,
            entity_type=EntityType.CONCEPT,
            name=name,
            source=MemorySource.CC,
        )
        entities.append(entity)

    for idx in range(len(entities) - 1):
        await DBMemRelation.find_or_create(
            workspace_id=workspace_id,
            subject_entity_id=entities[idx].id,
            predicate="related_to",
            object_entity_id=entities[idx + 1].id,
            paragraph_id=paragraph_id,
            memory_source="cc",
            cognitive_type=CognitiveType.SEMANTIC.value,
        )
