"""记忆维护服务。

提供结构化记忆的清理能力，供路由、命令与后台调度统一复用。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_mem_entity import DBMemEntity
from nekro_agent.models.db_mem_paragraph import DBMemParagraph
from nekro_agent.models.db_mem_reinforcement_log import DBMemReinforcementLog
from nekro_agent.models.db_mem_relation import DBMemRelation
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.services.memory.feature_flags import MemoryOperation, ensure_memory_system_enabled
from nekro_agent.services.memory.qdrant_manager import memory_qdrant_manager

logger = get_sub_logger("memory.maintenance")


@dataclass
class MemoryPruneResult:
    paragraphs_pruned: int = 0
    relations_pruned: int = 0
    entities_pruned: int = 0
    logs_pruned: int = 0


async def prune_workspace_memories(workspace_id: int) -> MemoryPruneResult:
    """清理单个工作区的低价值记忆。"""
    ensure_memory_system_enabled(MemoryOperation.PRUNE)

    now_ts = time.time()
    paragraph_candidates = await DBMemParagraph.filter(
        workspace_id=workspace_id,
        is_inactive=False,
        is_protected=False,
        is_frozen=False,
    ).all()
    prunable_paragraphs = [
        paragraph
        for paragraph in paragraph_candidates
        if paragraph.compute_effective_weight(now_ts) < config.MEMORY_PRUNE_PARAGRAPH_THRESHOLD
    ]

    pruned_paragraph_ids: list[int] = []
    for paragraph in prunable_paragraphs:
        paragraph.is_inactive = True
        paragraph.last_manual_action = "prune"
        paragraph.last_manual_action_at = datetime.now(timezone.utc)
        await paragraph.save(update_fields=["is_inactive", "last_manual_action", "last_manual_action_at", "update_time"])
        await memory_qdrant_manager.delete_paragraph(paragraph.id)
        pruned_paragraph_ids.append(paragraph.id)

    relation_candidates = await DBMemRelation.filter(
        workspace_id=workspace_id,
        is_inactive=False,
    ).all()
    prunable_relations = [
        relation
        for relation in relation_candidates
        if relation.compute_effective_weight(now_ts) < config.MEMORY_PRUNE_RELATION_THRESHOLD
        or relation.paragraph_id in pruned_paragraph_ids
    ]
    for relation in prunable_relations:
        relation.is_inactive = True
        await relation.save(update_fields=["is_inactive", "update_time"])

    active_entity_ids = {
        entity_id
        for pair in await DBMemRelation.filter(workspace_id=workspace_id, is_inactive=False).values_list(
            "subject_entity_id", "object_entity_id"
        )
        for entity_id in pair
    }
    entity_candidates = await DBMemEntity.filter(workspace_id=workspace_id, is_inactive=False).all()
    pruned_entity_ids: list[int] = []
    for entity in entity_candidates:
        if entity.id in active_entity_ids:
            continue
        if entity.appearance_count > 1:
            continue
        entity.is_inactive = True
        await entity.save(update_fields=["is_inactive", "update_time"])
        pruned_entity_ids.append(entity.id)

    # 清理过期的强化日志（默认保留30天）
    log_retention_seconds = config.MEMORY_LOG_RETENTION_DAYS * 86400
    log_cutoff_ts = now_ts - log_retention_seconds
    log_cutoff_dt = datetime.fromtimestamp(log_cutoff_ts, tz=timezone.utc)
    logs_deleted = await DBMemReinforcementLog.filter(
        workspace_id=workspace_id,
        create_time__lt=log_cutoff_dt,
    ).delete()

    result = MemoryPruneResult(
        paragraphs_pruned=len(pruned_paragraph_ids),
        relations_pruned=len(prunable_relations),
        entities_pruned=len(pruned_entity_ids),
        logs_pruned=logs_deleted,
    )
    logger.info(
        f"记忆清理完成: workspace={workspace_id}, "
        f"paragraphs={result.paragraphs_pruned}, relations={result.relations_pruned}, "
        f"entities={result.entities_pruned}, logs={result.logs_pruned}",
    )
    return result


async def prune_all_workspaces() -> dict[int, MemoryPruneResult]:
    """清理所有工作区的低价值记忆。"""
    results: dict[int, MemoryPruneResult] = {}
    workspace_ids = await DBWorkspace.all().values_list("id", flat=True)
    for workspace_id in workspace_ids:
        try:
            results[workspace_id] = await prune_workspace_memories(workspace_id)
        except Exception as e:
            logger.warning(f"工作区记忆清理失败: workspace={workspace_id}, error={e}")
    return results
