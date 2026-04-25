"""Episode 聚合服务。

将时间接近、聊天来源一致的 episodic paragraph 聚合为完整事件。
当前先走确定性聚合，避免在核心链路里增加额外 LLM 开销。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_mem_entity import DBMemEntity
from nekro_agent.models.db_mem_episode import DBMemEpisode, EpisodePhase
from nekro_agent.models.db_mem_paragraph import CognitiveType, DBMemParagraph
from nekro_agent.models.db_mem_relation import DBMemRelation
from nekro_agent.services.memory.feature_flags import is_memory_system_enabled

logger = get_sub_logger("memory.episode")


@dataclass
class EpisodeAggregationResult:
    episodes_created: int = 0
    paragraphs_bound: int = 0


class EpisodeAggregator:
    """Episode 聚合器。"""

    def __init__(self, workspace_id: int):
        self.workspace_id = workspace_id

    async def auto_consolidate_episodes(self, chat_key: str | None = None) -> EpisodeAggregationResult:
        result = EpisodeAggregationResult()
        if not config.MEMORY_EPISODE_ENABLED or not config.MEMORY_EPISODE_AUTO_CONSOLIDATE:
            return result

        groups = await self._collect_candidate_groups(chat_key)
        for paragraphs in groups:
            episode = await self._create_episode(paragraphs)
            if episode is None:
                continue
            result.episodes_created += 1
            result.paragraphs_bound += len(paragraphs)

        if result.episodes_created:
            logger.info(
                f"Episode 聚合完成: workspace={self.workspace_id}, "
                f"episodes={result.episodes_created}, paragraphs={result.paragraphs_bound}"
            )
        return result

    async def _collect_candidate_groups(self, chat_key: str | None) -> list[list[DBMemParagraph]]:
        qs = DBMemParagraph.filter(
            workspace_id=self.workspace_id,
            cognitive_type=CognitiveType.EPISODIC,
            episode_id__isnull=True,
            is_inactive=False,
        ).order_by("event_time", "id")
        if chat_key:
            qs = qs.filter(origin_chat_key=chat_key)

        paragraphs = await qs.limit(config.MEMORY_EPISODE_SCAN_LIMIT)
        if not paragraphs:
            return []

        groups: list[list[DBMemParagraph]] = []
        current: list[DBMemParagraph] = []
        gap = timedelta(minutes=config.MEMORY_EPISODE_TIME_GAP_MINUTES)

        for paragraph in paragraphs:
            if paragraph.event_time is None:
                continue
            if not current:
                current = [paragraph]
                continue

            prev = current[-1]
            close_in_time = (
                prev.event_time is not None
                and paragraph.event_time is not None
                and abs(paragraph.event_time - prev.event_time) <= gap
            )
            same_chat = paragraph.origin_chat_key == prev.origin_chat_key
            if close_in_time and same_chat:
                current.append(paragraph)
            else:
                if len(current) >= config.MEMORY_EPISODE_MIN_PARAGRAPHS:
                    groups.append(current)
                current = [paragraph]

        if len(current) >= config.MEMORY_EPISODE_MIN_PARAGRAPHS:
            groups.append(current)
        return groups

    async def _create_episode(self, paragraphs: list[DBMemParagraph]) -> DBMemEpisode | None:
        paragraph_ids = [p.id for p in paragraphs]
        if not paragraph_ids:
            return None

        existing = await DBMemEpisode.filter(
            workspace_id=self.workspace_id,
            origin_chat_key=paragraphs[0].origin_chat_key,
            time_start=paragraphs[0].event_time,
            time_end=paragraphs[-1].event_time,
        ).first()
        if existing:
            return None

        participant_entity_ids = await self._collect_participant_entity_ids(paragraph_ids)
        title = await self._build_title(paragraphs, participant_entity_ids)
        narrative_summary = self._build_narrative_summary(paragraphs)
        phase_mapping = self._build_phase_mapping(paragraphs)

        episode = await DBMemEpisode.create(
            workspace_id=self.workspace_id,
            origin_chat_key=paragraphs[0].origin_chat_key,
            title=title,
            narrative_summary=narrative_summary,
            time_start=paragraphs[0].event_time,
            time_end=paragraphs[-1].event_time,
            participant_entity_ids=participant_entity_ids,
            paragraph_ids=paragraph_ids,
            phase_mapping=phase_mapping,
            base_weight=sum(max(0.2, p.base_weight) for p in paragraphs) / len(paragraphs),
        )

        phase_by_paragraph = self._build_paragraph_phase_map(paragraphs)
        for paragraph in paragraphs:
            paragraph.episode_id = episode.id
            paragraph.episode_phase = phase_by_paragraph.get(paragraph.id)
            await paragraph.save(update_fields=["episode_id", "episode_phase", "update_time"])
        return episode

    async def _collect_participant_entity_ids(self, paragraph_ids: list[int]) -> list[int]:
        relations = await DBMemRelation.filter(
            workspace_id=self.workspace_id,
            paragraph_id__in=paragraph_ids,
            is_inactive=False,
        ).all()
        ids = sorted({r.subject_entity_id for r in relations} | {r.object_entity_id for r in relations})
        return ids[:16]

    async def _build_title(self, paragraphs: list[DBMemParagraph], entity_ids: list[int]) -> str:
        entity_names: list[str] = []
        if entity_ids:
            entities = await DBMemEntity.filter(workspace_id=self.workspace_id, id__in=entity_ids).limit(4)
            entity_names = [e.canonical_name for e in entities if e.canonical_name]

        if entity_names:
            joined = "、".join(entity_names[:3])
            return f"{joined}相关事件"

        summary = paragraphs[0].summary or paragraphs[0].content
        return summary[:48]

    def _build_narrative_summary(self, paragraphs: list[DBMemParagraph]) -> str:
        pieces: list[str] = []
        for paragraph in paragraphs[:6]:
            text = (paragraph.content or paragraph.summary or "").strip().replace("\n", " ")
            if text:
                pieces.append(text[:80])
        return "；".join(pieces)[:1200]

    def _build_phase_mapping(self, paragraphs: list[DBMemParagraph]) -> dict[str, list[int]]:
        phase_by_paragraph = self._build_paragraph_phase_map(paragraphs)
        mapping: dict[str, list[int]] = {phase.value: [] for phase in EpisodePhase}
        for paragraph in paragraphs:
            phase = phase_by_paragraph.get(paragraph.id)
            if phase is not None:
                mapping[phase.value].append(paragraph.id)
        return {key: value for key, value in mapping.items() if value}

    def _build_paragraph_phase_map(self, paragraphs: list[DBMemParagraph]) -> dict[int, EpisodePhase]:
        count = len(paragraphs)
        phase_map: dict[int, EpisodePhase] = {}
        for idx, paragraph in enumerate(paragraphs):
            if count <= 3:
                phase = [EpisodePhase.OPENING, EpisodePhase.DEVELOPMENT, EpisodePhase.RESOLUTION][min(idx, 2)]
            else:
                ratio = idx / max(1, count - 1)
                if ratio < 0.25:
                    phase = EpisodePhase.OPENING
                elif ratio < 0.65:
                    phase = EpisodePhase.DEVELOPMENT
                elif ratio < 0.85:
                    phase = EpisodePhase.CLIMAX
                else:
                    phase = EpisodePhase.RESOLUTION
            phase_map[paragraph.id] = phase
        return phase_map


async def aggregate_workspace_episodes(workspace_id: int, chat_key: str | None = None) -> EpisodeAggregationResult:
    if not is_memory_system_enabled():
        return EpisodeAggregationResult()

    aggregator = EpisodeAggregator(workspace_id)
    return await aggregator.auto_consolidate_episodes(chat_key)
