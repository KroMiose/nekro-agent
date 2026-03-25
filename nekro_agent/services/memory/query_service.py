"""记忆查询服务。

为插件、路由和其他上层调用提供统一的只读记忆查询能力。
"""

from __future__ import annotations

import time
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_mem_entity import DBMemEntity
from nekro_agent.models.db_mem_episode import DBMemEpisode
from nekro_agent.models.db_mem_paragraph import CognitiveType, DBMemParagraph, KnowledgeType
from nekro_agent.models.db_mem_relation import DBMemRelation
from nekro_agent.services.memory.retriever import RetrievedMemory, retrieve_memories


class MemoryObjectType(StrEnum):
    PARAGRAPH = "paragraph"
    RELATION = "relation"
    ENTITY = "entity"
    EPISODE = "episode"


class MemorySearchItem(BaseModel):
    target_id: int
    source_type: str
    episode_id: int | None = None
    paragraph_id: int | None = None
    relation_id: int | None = None
    summary: str
    content_preview: str
    cognitive_type: str
    knowledge_type: str
    similarity_score: float
    effective_weight: float
    event_time: str | None = None
    origin_chat_key: str | None = None


class MemorySearchResponse(BaseModel):
    workspace_id: int
    query: str
    total: int
    items: list[MemorySearchItem] = Field(default_factory=list)


class MemoryTraceAnchorMessage(BaseModel):
    db_id: int
    message_id: str
    sender_name: str
    send_timestamp: int
    content_preview: str


class MemoryOriginTraceResponse(BaseModel):
    workspace_id: int
    memory_type: str
    memory_id: int
    origin_kind: str | None = None
    origin_ref: str | None = None
    origin_chat_key: str | None = None
    anchor_msg_id: str | None = None
    anchor_msg_id_start: str | None = None
    anchor_msg_id_end: str | None = None
    anchor_timestamp_start: int | None = None
    anchor_timestamp_end: int | None = None
    messages: list[MemoryTraceAnchorMessage] = Field(default_factory=list)


class MemoryDetailRelationItem(BaseModel):
    id: int
    subject_entity_id: int
    subject_name: str
    predicate: str
    object_entity_id: int
    object_name: str
    paragraph_id: int | None = None
    effective_weight: float


class MemoryDetailResponse(BaseModel):
    workspace_id: int
    memory_type: str
    memory_id: int
    title: str
    summary: str | None = None
    content: str | None = None
    metadata: dict[str, str | int | float | bool | None | list[int] | list[str]] = Field(default_factory=dict)
    related_relations: list[MemoryDetailRelationItem] = Field(default_factory=list)
    related_paragraph_ids: list[int] = Field(default_factory=list)
    related_entity_ids: list[int] = Field(default_factory=list)


def _build_search_item(memory: RetrievedMemory) -> MemorySearchItem:
    preview = memory.content.strip().replace("\n", " ")
    return MemorySearchItem(
        target_id=memory.target_id,
        source_type=memory.source_type,
        episode_id=memory.episode_id,
        paragraph_id=memory.paragraph_id,
        relation_id=memory.relation_id,
        summary=memory.summary or preview[:120],
        content_preview=preview[:240],
        cognitive_type=memory.cognitive_type,
        knowledge_type=memory.knowledge_type,
        similarity_score=round(memory.similarity_score, 4),
        effective_weight=round(memory.effective_weight, 4),
        event_time=memory.event_time.isoformat() if memory.event_time else None,
        origin_chat_key=memory.origin_chat_key,
    )


def _parse_cognitive_type(value: str | None) -> CognitiveType | None:
    if not value or not value.strip():
        return None
    return CognitiveType(value.strip().lower())


def _parse_knowledge_type(value: str | None) -> KnowledgeType | None:
    if not value or not value.strip():
        return None
    return KnowledgeType(value.strip().lower())


async def search_workspace_memories(
    workspace_id: int,
    query: str,
    *,
    limit: int = 6,
    cognitive_type: str | None = None,
    knowledge_type: str | None = None,
    time_from: datetime | None = None,
    time_to: datetime | None = None,
) -> MemorySearchResponse:
    resolved_cognitive_type = _parse_cognitive_type(cognitive_type)
    resolved_knowledge_type = _parse_knowledge_type(knowledge_type)
    memories = await retrieve_memories(
        workspace_id=workspace_id,
        query=query,
        limit=limit,
        time_from=time_from,
        time_to=time_to,
    )

    filtered_memories: list[RetrievedMemory] = []
    for memory in memories:
        if resolved_cognitive_type and memory.cognitive_type != resolved_cognitive_type.value:
            continue
        if resolved_knowledge_type and memory.knowledge_type != resolved_knowledge_type.value:
            continue
        filtered_memories.append(memory)

    return MemorySearchResponse(
        workspace_id=workspace_id,
        query=query,
        total=len(filtered_memories),
        items=[_build_search_item(memory) for memory in filtered_memories],
    )


async def get_workspace_memory_detail(
    workspace_id: int,
    memory_type: MemoryObjectType,
    memory_id: int,
) -> MemoryDetailResponse:
    now_ts = time.time()

    if memory_type == MemoryObjectType.PARAGRAPH:
        paragraph = await DBMemParagraph.get_or_none(id=memory_id, workspace_id=workspace_id)
        if paragraph is None:
            raise ValueError(f"未找到段落记忆 {memory_id}")
        relations = await DBMemRelation.filter(workspace_id=workspace_id, paragraph_id=paragraph.id, is_inactive=False).all()
        entity_ids = list({rel.subject_entity_id for rel in relations} | {rel.object_entity_id for rel in relations})
        entities = {
            entity.id: entity
            for entity in await DBMemEntity.filter(workspace_id=workspace_id, id__in=entity_ids).all()
        }
        return MemoryDetailResponse(
            workspace_id=workspace_id,
            memory_type=memory_type.value,
            memory_id=paragraph.id,
            title=paragraph.summary or paragraph.content[:80],
            summary=paragraph.summary,
            content=paragraph.content,
            metadata={
                "memory_source": paragraph.memory_source,
                "cognitive_type": paragraph.cognitive_type.value,
                "knowledge_type": paragraph.knowledge_type.value,
                "effective_weight": round(paragraph.compute_effective_weight(now_ts), 4),
                "event_time": paragraph.event_time.isoformat() if paragraph.event_time else None,
                "origin_kind": paragraph.origin_kind.value,
                "origin_ref": paragraph.origin_ref,
                "origin_chat_key": paragraph.origin_chat_key,
                "episode_id": paragraph.episode_id,
                "is_inactive": paragraph.is_inactive,
            },
            related_relations=[
                MemoryDetailRelationItem(
                    id=relation.id,
                    subject_entity_id=relation.subject_entity_id,
                    subject_name=entities.get(relation.subject_entity_id).canonical_name
                    if relation.subject_entity_id in entities else str(relation.subject_entity_id),
                    predicate=relation.predicate,
                    object_entity_id=relation.object_entity_id,
                    object_name=entities.get(relation.object_entity_id).canonical_name
                    if relation.object_entity_id in entities else str(relation.object_entity_id),
                    paragraph_id=relation.paragraph_id,
                    effective_weight=round(relation.compute_effective_weight(now_ts), 4),
                )
                for relation in relations
            ],
            related_entity_ids=entity_ids,
        )

    if memory_type == MemoryObjectType.RELATION:
        relation = await DBMemRelation.get_or_none(id=memory_id, workspace_id=workspace_id)
        if relation is None:
            raise ValueError(f"未找到关系记忆 {memory_id}")
        entities = {
            entity.id: entity
            for entity in await DBMemEntity.filter(
                workspace_id=workspace_id,
                id__in=[relation.subject_entity_id, relation.object_entity_id],
            ).all()
        }
        return MemoryDetailResponse(
            workspace_id=workspace_id,
            memory_type=memory_type.value,
            memory_id=relation.id,
            title=f"{entities.get(relation.subject_entity_id).canonical_name if relation.subject_entity_id in entities else relation.subject_entity_id} -> {relation.predicate} -> {entities.get(relation.object_entity_id).canonical_name if relation.object_entity_id in entities else relation.object_entity_id}",
            metadata={
                "memory_source": relation.memory_source,
                "cognitive_type": relation.cognitive_type,
                "paragraph_id": relation.paragraph_id,
                "effective_weight": round(relation.compute_effective_weight(now_ts), 4),
                "is_inactive": relation.is_inactive,
            },
            related_entity_ids=[relation.subject_entity_id, relation.object_entity_id],
            related_paragraph_ids=[relation.paragraph_id] if relation.paragraph_id is not None else [],
        )

    if memory_type == MemoryObjectType.ENTITY:
        entity = await DBMemEntity.get_or_none(id=memory_id, workspace_id=workspace_id)
        if entity is None:
            raise ValueError(f"未找到实体记忆 {memory_id}")
        relations = await DBMemRelation.filter(
            workspace_id=workspace_id,
            is_inactive=False,
        ).filter(subject_entity_id=entity.id).limit(10)
        reverse_relations = await DBMemRelation.filter(
            workspace_id=workspace_id,
            is_inactive=False,
        ).filter(object_entity_id=entity.id).limit(10)
        all_entity_ids = list({rel.subject_entity_id for rel in relations + reverse_relations} | {rel.object_entity_id for rel in relations + reverse_relations})
        entities = {
            item.id: item
            for item in await DBMemEntity.filter(workspace_id=workspace_id, id__in=all_entity_ids).all()
        }
        relation_items = [
            MemoryDetailRelationItem(
                id=relation.id,
                subject_entity_id=relation.subject_entity_id,
                subject_name=entities.get(relation.subject_entity_id).canonical_name
                if relation.subject_entity_id in entities else str(relation.subject_entity_id),
                predicate=relation.predicate,
                object_entity_id=relation.object_entity_id,
                object_name=entities.get(relation.object_entity_id).canonical_name
                if relation.object_entity_id in entities else str(relation.object_entity_id),
                paragraph_id=relation.paragraph_id,
                effective_weight=round(relation.compute_effective_weight(now_ts), 4),
            )
            for relation in list(relations) + list(reverse_relations)
        ]
        related_paragraph_ids = sorted({item.paragraph_id for item in relation_items if item.paragraph_id is not None})
        return MemoryDetailResponse(
            workspace_id=workspace_id,
            memory_type=memory_type.value,
            memory_id=entity.id,
            title=entity.canonical_name,
            summary=entity.name,
            metadata={
                "entity_type": entity.entity_type.value,
                "canonical_name": entity.canonical_name,
                "appearance_count": entity.appearance_count,
                "source_hint": entity.source_hint.value,
                "is_inactive": entity.is_inactive,
                "aliases": entity.aliases if isinstance(entity.aliases, list) else [],
            },
            related_relations=relation_items,
            related_paragraph_ids=related_paragraph_ids,
            related_entity_ids=all_entity_ids,
        )

    if memory_type == MemoryObjectType.EPISODE:
        episode = await DBMemEpisode.get_or_none(id=memory_id, workspace_id=workspace_id)
        if episode is None:
            raise ValueError(f"未找到 Episode 记忆 {memory_id}")
        return MemoryDetailResponse(
            workspace_id=workspace_id,
            memory_type=memory_type.value,
            memory_id=episode.id,
            title=episode.title,
            summary=episode.narrative_summary[:200],
            content=episode.narrative_summary,
            metadata={
                "origin_chat_key": episode.origin_chat_key,
                "time_start": episode.time_start.isoformat() if episode.time_start else None,
                "time_end": episode.time_end.isoformat() if episode.time_end else None,
                "base_weight": episode.base_weight,
                "is_inactive": episode.is_inactive,
            },
            related_paragraph_ids=list(episode.paragraph_ids),
            related_entity_ids=list(episode.participant_entity_ids),
        )

    raise ValueError(f"不支持的记忆类型: {memory_type}")


async def trace_workspace_memory_origin(
    workspace_id: int,
    memory_type: MemoryObjectType,
    memory_id: int,
) -> MemoryOriginTraceResponse:
    if memory_type == MemoryObjectType.PARAGRAPH:
        paragraph = await DBMemParagraph.get_or_none(id=memory_id, workspace_id=workspace_id)
        if paragraph is None:
            raise ValueError(f"未找到段落记忆 {memory_id}")
        messages: list[MemoryTraceAnchorMessage] = []
        anchor_message_ids = [
            msg_id
            for msg_id in [paragraph.anchor_msg_id, paragraph.anchor_msg_id_start, paragraph.anchor_msg_id_end]
            if msg_id
        ]
        if anchor_message_ids:
            db_messages = await DBChatMessage.filter(
                chat_key=paragraph.origin_chat_key,
                message_id__in=anchor_message_ids,
            ).order_by("send_timestamp")
            messages = [
                MemoryTraceAnchorMessage(
                    db_id=message.id,
                    message_id=message.message_id,
                    sender_name=message.sender_nickname or message.sender_name,
                    send_timestamp=message.send_timestamp,
                    content_preview=message.content_text[:200],
                )
                for message in db_messages
            ]
        return MemoryOriginTraceResponse(
            workspace_id=workspace_id,
            memory_type=memory_type.value,
            memory_id=paragraph.id,
            origin_kind=paragraph.origin_kind.value,
            origin_ref=paragraph.origin_ref,
            origin_chat_key=paragraph.origin_chat_key,
            anchor_msg_id=paragraph.anchor_msg_id,
            anchor_msg_id_start=paragraph.anchor_msg_id_start,
            anchor_msg_id_end=paragraph.anchor_msg_id_end,
            anchor_timestamp_start=paragraph.anchor_timestamp_start,
            anchor_timestamp_end=paragraph.anchor_timestamp_end,
            messages=messages,
        )

    if memory_type == MemoryObjectType.RELATION:
        relation = await DBMemRelation.get_or_none(id=memory_id, workspace_id=workspace_id)
        if relation is None:
            raise ValueError(f"未找到关系记忆 {memory_id}")
        if relation.paragraph_id is None:
            return MemoryOriginTraceResponse(
                workspace_id=workspace_id,
                memory_type=memory_type.value,
                memory_id=relation.id,
            )
        return await trace_workspace_memory_origin(workspace_id, MemoryObjectType.PARAGRAPH, relation.paragraph_id)

    if memory_type == MemoryObjectType.EPISODE:
        episode = await DBMemEpisode.get_or_none(id=memory_id, workspace_id=workspace_id)
        if episode is None:
            raise ValueError(f"未找到 Episode 记忆 {memory_id}")
        return MemoryOriginTraceResponse(
            workspace_id=workspace_id,
            memory_type=memory_type.value,
            memory_id=episode.id,
            origin_chat_key=episode.origin_chat_key,
            anchor_timestamp_start=int(episode.time_start.timestamp()) if episode.time_start else None,
            anchor_timestamp_end=int(episode.time_end.timestamp()) if episode.time_end else None,
        )

    if memory_type == MemoryObjectType.ENTITY:
        entity = await DBMemEntity.get_or_none(id=memory_id, workspace_id=workspace_id)
        if entity is None:
            raise ValueError(f"未找到实体记忆 {memory_id}")
        return MemoryOriginTraceResponse(
            workspace_id=workspace_id,
            memory_type=memory_type.value,
            memory_id=entity.id,
            origin_kind="entity",
        )

    raise ValueError(f"不支持的记忆类型: {memory_type}")
