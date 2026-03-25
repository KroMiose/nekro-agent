"""记忆检索服务

提供语义检索能力，为 NA 上下文注入提供记忆支持。
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from tortoise.expressions import Q

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_mem_entity import DBMemEntity
from nekro_agent.models.db_mem_episode import DBMemEpisode
from nekro_agent.models.db_mem_paragraph import CognitiveType, DBMemParagraph
from nekro_agent.models.db_mem_reinforcement_log import (
    DBMemReinforcementLog,
    TargetType,
    TriggerSource,
)
from nekro_agent.models.db_mem_relation import DBMemRelation
from nekro_agent.services.memory.embedding_service import embed_text
from nekro_agent.services.memory.feature_flags import is_memory_system_enabled
from nekro_agent.services.memory.qdrant_manager import memory_qdrant_manager

logger = get_sub_logger("memory.retriever")


@dataclass
class RetrievedMemory:
    """检索到的记忆"""

    target_id: int
    source_type: str
    episode_id: int | None
    paragraph_id: int | None
    relation_id: int | None
    content: str
    summary: str
    cognitive_type: str
    knowledge_type: str
    similarity_score: float
    effective_weight: float
    event_time: datetime | None
    origin_chat_key: str | None


@dataclass
class RetrievalResult:
    """检索结果"""

    memories: list[RetrievedMemory]
    query_embedding_time_ms: float
    search_time_ms: float
    total_candidates: int


@dataclass
class MemoryRecallQuery:
    """面向上下文注入的检索查询。"""

    query_text: str
    focus_text: str
    focus_points: list[str]
    context_texts: list[str]
    time_from: datetime | None = None
    time_to: datetime | None = None


class MemoryRetriever:
    """记忆检索器

    职责：
    1. 语义检索相关记忆
    2. 计算有效权重
    3. 记录访问日志（用于后续强化）
    """

    def __init__(self, workspace_id: int):
        self.workspace_id = workspace_id

    async def retrieve(
        self,
        query: str,
        limit: int | None = None,
        min_similarity: float | None = None,
        cognitive_type: CognitiveType | None = None,
        include_inactive: bool = False,
        record_access: bool = True,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
    ) -> RetrievalResult:
        """检索相关记忆

        Args:
            query: 查询文本
            limit: 返回数量上限
            min_similarity: 最低相似度阈值
            cognitive_type: 可选，过滤认知类型
            include_inactive: 是否包含已失活记忆
            record_access: 是否记录访问日志

        Returns:
            检索结果
        """
        if not is_memory_system_enabled():
            return RetrievalResult(
                memories=[],
                query_embedding_time_ms=0,
                search_time_ms=0,
                total_candidates=0,
            )

        resolved_limit = limit if limit is not None else config.MEMORY_RETRIEVAL_DEFAULT_LIMIT
        resolved_min_similarity = (
            min_similarity if min_similarity is not None else config.MEMORY_RETRIEVAL_MIN_SIMILARITY
        )
        # 生成查询向量
        t0 = time.perf_counter()
        try:
            query_embedding = await embed_text(query)
        except Exception as e:
            logger.warning(f"查询向量化失败: {e}")
            return RetrievalResult(
                memories=[],
                query_embedding_time_ms=0,
                search_time_ms=0,
                total_candidates=0,
            )
        embedding_time = (time.perf_counter() - t0) * 1000

        # 向量搜索
        t1 = time.perf_counter()
        search_results = await memory_qdrant_manager.search(
            query_vector=query_embedding,
            workspace_id=self.workspace_id,
            limit=resolved_limit * 2,  # 多取一些用于后处理
            score_threshold=resolved_min_similarity,
            cognitive_type=cognitive_type.value if cognitive_type else None,
            include_inactive=include_inactive,
            event_time_from=int(time_from.timestamp()) if time_from else None,
            event_time_to=int(time_to.timestamp()) if time_to else None,
        )
        search_time = (time.perf_counter() - t1) * 1000

        # 获取段落详情并计算有效权重
        paragraph_candidates: dict[int, RetrievedMemory] = {}
        paragraph_ids = [r["id"] for r in search_results]

        paragraphs = await DBMemParagraph.filter(
            id__in=paragraph_ids,
            workspace_id=self.workspace_id,
        ).all()
        paragraph_map = {p.id: p for p in paragraphs}

        for result in search_results:
            para_id = result["id"]
            if para_id not in paragraph_map:
                continue

            paragraph = paragraph_map[para_id]
            similarity = result["score"]

            # 计算有效权重
            effective_weight = self._compute_effective_weight(paragraph, similarity)

            paragraph_candidates[para_id] = RetrievedMemory(
                target_id=para_id,
                source_type="paragraph",
                episode_id=paragraph.episode_id,
                paragraph_id=para_id,
                relation_id=None,
                content=paragraph.content,
                summary=paragraph.summary or "",
                cognitive_type=paragraph.cognitive_type.value,
                knowledge_type=paragraph.knowledge_type.value,
                similarity_score=similarity,
                effective_weight=effective_weight,
                event_time=paragraph.event_time,
                origin_chat_key=paragraph.origin_chat_key,
            )

        relation_memories = await self._retrieve_relation_memories(
            query=query,
            limit=resolved_limit,
            paragraph_candidates=paragraph_candidates,
            include_inactive=include_inactive,
        )
        episode_memories = await self._retrieve_episode_memories(
            query=query,
            limit=max(2, min(4, resolved_limit)),
            paragraph_candidates=paragraph_candidates,
            include_inactive=include_inactive,
            time_from=time_from,
            time_to=time_to,
        )

        memories = list(paragraph_candidates.values()) + relation_memories + episode_memories
        # 按有效权重排序
        memories.sort(key=lambda m: m.effective_weight, reverse=True)
        memories = memories[:resolved_limit]

        # 记录访问日志
        if record_access and memories:
            await self._record_access(memories, query)

        logger.debug(
            f"记忆检索完成: query={query[:30]}..., "
            f"results={len(memories)}, embedding={embedding_time:.1f}ms, search={search_time:.1f}ms",
        )

        return RetrievalResult(
            memories=memories,
            query_embedding_time_ms=embedding_time,
            search_time_ms=search_time,
            total_candidates=len(search_results) + len(relation_memories) + len(episode_memories),
        )

    def _compute_effective_weight(
        self,
        paragraph: DBMemParagraph,
        similarity: float,
    ) -> float:
        """计算有效权重

        综合考虑：
        - 基础权重（衰减后）
        - 相似度分数
        - 认知类型加成
        - 近期记忆加成
        """
        # 基础有效权重（包含衰减）
        base_weight = paragraph.compute_effective_weight(time.time())

        # 相似度加权
        score = base_weight * similarity

        # 情景记忆加成（更具体，更有价值）
        if paragraph.cognitive_type == CognitiveType.EPISODIC:
            score *= config.MEMORY_RETRIEVAL_EPISODIC_BOOST

        # 近期记忆加成
        if paragraph.event_time:
            event_time = self._normalize_datetime(paragraph.event_time)
            hours_ago = (datetime.now(timezone.utc) - event_time).total_seconds() / 3600
            if hours_ago < config.MEMORY_RETRIEVAL_RECENT_BOOST_HOURS:
                score *= config.MEMORY_RETRIEVAL_RECENT_BOOST_FACTOR

        return score

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        """统一转为 UTC aware datetime，避免 naive/aware 混算。"""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    async def _retrieve_relation_memories(
        self,
        query: str,
        limit: int,
        paragraph_candidates: dict[int, RetrievedMemory],
        include_inactive: bool,
    ) -> list[RetrievedMemory]:
        """从实体关系图谱中检索相关记忆，并对关联段落进行加权。"""
        terms = self._tokenize_query(query)
        if not terms:
            return []

        entity_query = Q()
        for term in terms[:5]:
            entity_query |= Q(canonical_name__icontains=term) | Q(name__icontains=term)

        matched_entities = await DBMemEntity.filter(
            entity_query,
            workspace_id=self.workspace_id,
            is_inactive=False,
        ).limit(config.MEMORY_RETRIEVAL_RELATION_MATCH_LIMIT)
        entity_map = {entity.id: entity for entity in matched_entities}
        matched_ids = list(entity_map.keys())

        relation_query = Q()
        if matched_ids:
            relation_query |= Q(subject_entity_id__in=matched_ids) | Q(object_entity_id__in=matched_ids)
        for term in terms[:3]:
            relation_query |= Q(predicate__icontains=term)

        if not relation_query.children:
            return []

        relation_qs = DBMemRelation.filter(
            relation_query,
            workspace_id=self.workspace_id,
        )
        if not include_inactive:
            relation_qs = relation_qs.filter(is_inactive=False)
        relations = await relation_qs.order_by("-update_time").limit(limit * 3)

        missing_entity_ids = {
            relation.subject_entity_id for relation in relations if relation.subject_entity_id not in entity_map
        } | {
            relation.object_entity_id for relation in relations if relation.object_entity_id not in entity_map
        }
        if missing_entity_ids:
            extra_entities = await DBMemEntity.filter(id__in=list(missing_entity_ids), workspace_id=self.workspace_id)
            entity_map.update({entity.id: entity for entity in extra_entities})

        relation_memories: list[RetrievedMemory] = []
        for relation in relations:
            subject_name = entity_map.get(relation.subject_entity_id).canonical_name if relation.subject_entity_id in entity_map else str(relation.subject_entity_id)
            object_name = entity_map.get(relation.object_entity_id).canonical_name if relation.object_entity_id in entity_map else str(relation.object_entity_id)

            match_score = self._compute_relation_match_score(query, subject_name, relation.predicate, object_name)
            effective_weight = (
                relation.compute_effective_weight(time.time())
                * match_score
                * config.MEMORY_RETRIEVAL_RELATION_BOOST
            )
            summary = f"{subject_name} - {relation.predicate} - {object_name}"
            content = f"关系记忆：{subject_name} {relation.predicate} {object_name}"

            if relation.paragraph_id:
                paragraph = paragraph_candidates.get(relation.paragraph_id)
                if paragraph is None:
                    linked = await DBMemParagraph.get_or_none(
                        id=relation.paragraph_id,
                        workspace_id=self.workspace_id,
                    )
                    if linked is not None:
                        paragraph = RetrievedMemory(
                            target_id=linked.id,
                            source_type="paragraph",
                            episode_id=linked.episode_id,
                            paragraph_id=linked.id,
                            relation_id=None,
                            content=linked.content,
                            summary=linked.summary or "",
                            cognitive_type=linked.cognitive_type.value,
                            knowledge_type=linked.knowledge_type.value,
                            similarity_score=match_score,
                            effective_weight=self._compute_effective_weight(linked, match_score),
                            event_time=linked.event_time,
                            origin_chat_key=linked.origin_chat_key,
                        )
                        paragraph_candidates[linked.id] = paragraph

                if paragraph is not None:
                    paragraph.effective_weight += effective_weight * 0.35
                    paragraph.similarity_score = max(paragraph.similarity_score, match_score)

            relation_memories.append(
                RetrievedMemory(
                    target_id=relation.id,
                    source_type="relation",
                    episode_id=None,
                    paragraph_id=relation.paragraph_id,
                    relation_id=relation.id,
                    content=content,
                    summary=summary,
                    cognitive_type=relation.cognitive_type,
                    knowledge_type="relation",
                    similarity_score=match_score,
                    effective_weight=effective_weight,
                    event_time=None,
                    origin_chat_key=None,
                )
            )

        return relation_memories

    async def _retrieve_episode_memories(
        self,
        query: str,
        limit: int,
        paragraph_candidates: dict[int, RetrievedMemory],
        include_inactive: bool,
        time_from: datetime | None,
        time_to: datetime | None,
    ) -> list[RetrievedMemory]:
        """检索 Episode 级事件记忆，并给关联段落做轻量加权。"""
        terms = self._tokenize_query(query)
        candidate_ids = {
            mem.episode_id
            for mem in paragraph_candidates.values()
            if mem.source_type == "paragraph" and mem.episode_id is not None
        }

        query_q = Q()
        for term in terms[:4]:
            query_q |= Q(title__icontains=term) | Q(narrative_summary__icontains=term)

        episode_qs = DBMemEpisode.filter(workspace_id=self.workspace_id)
        if not include_inactive:
            episode_qs = episode_qs.filter(is_inactive=False)
        if time_from:
            episode_qs = episode_qs.filter(Q(time_end__gte=time_from) | Q(time_start__gte=time_from))
        if time_to:
            episode_qs = episode_qs.filter(Q(time_start__lte=time_to) | Q(time_end__lte=time_to))

        if candidate_ids and query_q.children:
            episodes = await episode_qs.filter(Q(id__in=list(candidate_ids)) | query_q).limit(limit * 4)
        elif candidate_ids:
            episodes = await episode_qs.filter(id__in=list(candidate_ids)).limit(limit * 3)
        elif query_q.children:
            episodes = await episode_qs.filter(query_q).limit(limit * 3)
        else:
            return []

        memories: list[RetrievedMemory] = []
        seen_ids: set[int] = set()
        for episode in episodes:
            if episode.id in seen_ids:
                continue
            seen_ids.add(episode.id)

            match_score = self._compute_episode_match_score(query, episode)
            event_time = episode.time_end or episode.time_start
            recent_bonus = 1.0
            if event_time:
                hours_ago = (datetime.now(timezone.utc) - self._normalize_datetime(event_time)).total_seconds() / 3600
                if hours_ago < config.MEMORY_RETRIEVAL_RECENT_BOOST_HOURS:
                    recent_bonus = config.MEMORY_RETRIEVAL_RECENT_BOOST_FACTOR

            effective_weight = episode.base_weight * match_score * 1.18 * recent_bonus
            memories.append(
                RetrievedMemory(
                    target_id=episode.id,
                    source_type="episode",
                    episode_id=episode.id,
                    paragraph_id=None,
                    relation_id=None,
                    content=episode.narrative_summary,
                    summary=episode.title,
                    cognitive_type=CognitiveType.EPISODIC.value,
                    knowledge_type="experience",
                    similarity_score=match_score,
                    effective_weight=effective_weight,
                    event_time=event_time,
                    origin_chat_key=episode.origin_chat_key,
                )
            )

            for paragraph in paragraph_candidates.values():
                if paragraph.source_type == "paragraph" and paragraph.episode_id == episode.id:
                    paragraph.effective_weight += effective_weight * 0.18

        memories.sort(key=lambda mem: (-mem.effective_weight, -mem.similarity_score))
        return memories[:limit]

    @staticmethod
    def _tokenize_query(query: str) -> list[str]:
        """保守切分查询词，兼顾中文短句和英文 token。"""
        compact = query.strip().lower()
        if not compact:
            return []
        tokens = [token for token in re.split(r"[\s,，。.!！?:：;；/|]+", compact) if token]
        if compact not in tokens:
            tokens.insert(0, compact)
        seen: list[str] = []
        for token in tokens:
            if token not in seen and len(token) >= 2:
                seen.append(token)
        return seen[:8]

    @staticmethod
    def _compute_relation_match_score(
        query: str,
        subject_name: str,
        predicate: str,
        object_name: str,
    ) -> float:
        """计算 query 与关系三元组的匹配分数。"""
        query_lower = query.lower()
        score = 0.55
        if subject_name.lower() in query_lower:
            score += 0.2
        if object_name.lower() in query_lower:
            score += 0.2
        if predicate.lower() in query_lower:
            score += 0.15
        return min(score, 1.0)

    @staticmethod
    def _compute_episode_match_score(query: str, episode: DBMemEpisode) -> float:
        """计算查询与 Episode 的匹配分数。"""
        query_lower = query.lower()
        title = (episode.title or "").lower()
        summary = (episode.narrative_summary or "").lower()
        query_tokens = [token for token in re.split(r"[\s,，。.!！?:：;；/|]+", query_lower) if len(token) >= 2]

        score = 0.58
        if title and title in query_lower:
            score += 0.22
        elif any(token in title for token in query_tokens):
            score += 0.1
        if summary and any(token in summary for token in query_tokens):
            score += 0.14
        if episode.participant_entity_ids:
            score += min(0.08, len(episode.participant_entity_ids) * 0.01)
        return min(score, 1.0)

    async def _record_access(
        self,
        memories: list[RetrievedMemory],
        query: str,
    ) -> None:
        """记录访问日志"""
        try:
            for mem in memories[:5]:  # 只记录前 5 条
                if mem.source_type == "episode":
                    continue
                await DBMemReinforcementLog.log_reinforcement(
                    workspace_id=self.workspace_id,
                    target_type=TargetType.RELATION if mem.source_type == "relation" else TargetType.PARAGRAPH,
                    target_id=mem.target_id,
                    trigger_source=TriggerSource.NA_RETRIEVAL,
                    trigger_ref=query[:100],
                    boost_amount=0.0,  # 检索访问不直接增加权重
                )
        except Exception as e:
            logger.debug(f"记录访问日志失败: {e}")

    async def retrieve_by_entity(
        self,
        entity_name: str,
        limit: int | None = None,
    ) -> list[RetrievedMemory]:
        """按实体名称检索相关记忆

        Args:
            entity_name: 实体名称
            limit: 返回数量上限

        Returns:
            相关记忆列表
        """
        # 使用实体名称作为查询
        result = await self.retrieve(
            query=entity_name,
            limit=limit or config.MEMORY_RETRIEVAL_DEFAULT_LIMIT,
            min_similarity=0.6,  # 实体查询使用更高阈值
        )
        return result.memories

    async def get_recent_memories(
        self,
        hours: int = 24,
        limit: int = 20,
    ) -> list[RetrievedMemory]:
        """获取近期记忆

        Args:
            hours: 时间范围（小时）
            limit: 返回数量上限

        Returns:
            近期记忆列表
        """

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        paragraphs = await DBMemParagraph.filter(
            workspace_id=self.workspace_id,
            event_time__gte=cutoff,
            is_inactive=False,
        ).order_by("-event_time").limit(limit)

        return [
            RetrievedMemory(
                target_id=p.id,
                source_type="paragraph",
                episode_id=p.episode_id,
                paragraph_id=p.id,
                relation_id=None,
                content=p.content,
                summary=p.summary or "",
                cognitive_type=p.cognitive_type.value,
                knowledge_type=p.knowledge_type.value,
                similarity_score=1.0,  # 时间查询不涉及相似度
                effective_weight=p.compute_effective_weight(time.time()),
                event_time=p.event_time,
                origin_chat_key=p.origin_chat_key,
            )
            for p in paragraphs
        ]


async def retrieve_memories(
    workspace_id: int,
    query: str,
    limit: int | None = None,
    time_from: datetime | None = None,
    time_to: datetime | None = None,
) -> list[RetrievedMemory]:
    """便捷函数：检索记忆"""
    retriever = MemoryRetriever(workspace_id)
    result = await retriever.retrieve(query, limit=limit, time_from=time_from, time_to=time_to)
    return result.memories


async def compile_memories_for_context(
    recall_query: MemoryRecallQuery,
    memories: list[RetrievedMemory],
    max_length: int = 2000,
) -> str:
    """将检索候选编排为真正用于 prompt 注入的上下文块。"""
    if not memories:
        return ""

    selected = _select_context_memories(memories)
    if not selected:
        return ""

    lines: list[str] = ["[相关记忆]"]
    current_length = len(lines[0])

    focus_points = [point for point in recall_query.focus_points if point.strip()]
    if focus_points:
        title = "当前关注："
        if current_length + len(title) + 1 <= max_length:
            lines.append(title)
            current_length += len(title) + 1
        for point in focus_points[:4]:
            focus_line = f"- {point[:120]}"
            if current_length + len(focus_line) + 1 > max_length:
                break
            lines.append(focus_line)
            current_length += len(focus_line) + 1
    elif recall_query.focus_text:
        focus_line = f"当前关注：{recall_query.focus_text[:120]}"
        if current_length + len(focus_line) + 1 <= max_length:
            lines.append(focus_line)
            current_length += len(focus_line) + 1

    category_order = ["decision", "fact", "preference", "experience", "conversation", "emotion", "relation"]
    category_titles = {
        "decision": "相关决策",
        "fact": "相关事实",
        "preference": "相关偏好",
        "experience": "相关经验",
        "conversation": "相关对话",
        "emotion": "相关情绪",
        "relation": "相关关系",
    }

    grouped: dict[str, list[RetrievedMemory]] = {key: [] for key in category_order}
    for mem in selected:
        key = "relation" if mem.source_type == "relation" else mem.knowledge_type
        grouped.setdefault(key, []).append(mem)

    for key in category_order:
        items = grouped.get(key) or []
        if not items:
            continue

        title = category_titles.get(key, "相关记忆")
        if current_length + len(title) + 1 > max_length:
            break
        lines.append(f"{title}：")
        current_length += len(title) + 1

        for mem in items:
            line = _format_compiled_memory_line(mem)
            if current_length + len(line) + 1 > max_length:
                break
            lines.append(line)
            current_length += len(line) + 1

    return "\n".join(lines)


async def format_memories_for_context(
    memories: list[RetrievedMemory],
    max_length: int = 2000,
) -> str:
    """格式化记忆为上下文字符串

    Args:
        memories: 记忆列表
        max_length: 最大长度

    Returns:
        格式化后的字符串
    """
    return await compile_memories_for_context(
        recall_query=MemoryRecallQuery(query_text="", focus_text="", focus_points=[], context_texts=[]),
        memories=memories,
        max_length=max_length,
    )


def _select_context_memories(memories: list[RetrievedMemory]) -> list[RetrievedMemory]:
    """按类型和价值选出用于上下文编排的候选。"""
    paragraph_memories = [mem for mem in memories if mem.source_type == "paragraph"]
    episode_memories = [mem for mem in memories if mem.source_type == "episode"]
    relation_memories = [mem for mem in memories if mem.source_type == "relation"]

    episode_memories.sort(key=lambda mem: (-mem.similarity_score, -mem.effective_weight))
    paragraph_memories.sort(
        key=lambda mem: (
            -mem.similarity_score,
            -mem.effective_weight,
            0 if mem.cognitive_type == "semantic" else 1,
        )
    )
    relation_memories.sort(key=lambda mem: (-mem.similarity_score, -mem.effective_weight))

    selected: list[RetrievedMemory] = []
    seen_ids: set[tuple[str, int]] = set()
    quota_by_type = {"decision": 3, "fact": 3, "preference": 2, "experience": 4, "conversation": 2, "emotion": 1}
    used_by_type = {key: 0 for key in quota_by_type}

    for mem in episode_memories[:3]:
        memory_key = (mem.source_type, mem.target_id)
        if memory_key in seen_ids:
            continue
        selected.append(mem)
        seen_ids.add(memory_key)
        used_by_type["experience"] = min(quota_by_type["experience"], used_by_type["experience"] + 1)

    for mem in paragraph_memories:
        memory_key = (mem.source_type, mem.target_id)
        if memory_key in seen_ids:
            continue
        knowledge_type = mem.knowledge_type if mem.knowledge_type in quota_by_type else "conversation"
        if used_by_type[knowledge_type] >= quota_by_type[knowledge_type]:
            continue
        selected.append(mem)
        seen_ids.add(memory_key)
        used_by_type[knowledge_type] += 1
        if len(selected) >= 9:
            break

    for mem in relation_memories[:3]:
        memory_key = (mem.source_type, mem.target_id)
        if memory_key in seen_ids:
            continue
        selected.append(mem)
        seen_ids.add(memory_key)

    return selected


def _format_compiled_memory_line(mem: RetrievedMemory) -> str:
    """将单条记忆编排为更适合 prompt 的上下文行。"""
    if mem.source_type == "relation":
        return f"- {mem.summary}"
    if mem.source_type == "episode":
        time_str = mem.event_time.strftime("%m-%d %H:%M") if mem.event_time else "未知时间"
        title = re.sub(r"\s+", " ", (mem.summary or "").strip()) or "事件"
        narrative = re.sub(r"\s+", " ", (mem.content or "").strip())[:160]
        return f"- [事件 {time_str}] {title}：{narrative}"

    time_str = mem.event_time.strftime("%m-%d %H:%M") if mem.event_time else "未知时间"
    content = re.sub(r"\s+", " ", (mem.content or "").strip())
    summary = re.sub(r"\s+", " ", (mem.summary or "").strip())
    body = content or summary
    if summary and summary not in body and len(summary) > 6:
        body = f"{summary}：{body}"
    body = body[:140]
    return f"- [{time_str}] {body}"
