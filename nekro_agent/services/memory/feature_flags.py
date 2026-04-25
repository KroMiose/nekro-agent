"""记忆系统功能开关辅助。"""

from __future__ import annotations

from enum import StrEnum

from nekro_agent.core.config import config
from nekro_agent.schemas.errors import ValidationError


class MemoryOperation(StrEnum):
    CONTEXT_INJECTION = "context_injection"
    RETRIEVAL = "retrieval"
    CONSOLIDATION = "consolidation"
    CC_HANDSHAKE = "cc_handshake"
    CC_SEMANTIC_PERSIST = "cc_semantic_persist"
    REBUILD = "rebuild"
    PRUNE = "prune"
    EPISODE_AGGREGATION = "episode_aggregation"
    SCHEDULER = "scheduler"


_MEMORY_OPERATION_LABELS: dict[MemoryOperation, str] = {
    MemoryOperation.CONTEXT_INJECTION: "记忆上下文注入",
    MemoryOperation.RETRIEVAL: "记忆检索",
    MemoryOperation.CONSOLIDATION: "记忆沉淀",
    MemoryOperation.CC_HANDSHAKE: "CC 记忆握手",
    MemoryOperation.CC_SEMANTIC_PERSIST: "CC 语义记忆沉淀",
    MemoryOperation.REBUILD: "记忆重建",
    MemoryOperation.PRUNE: "记忆清理",
    MemoryOperation.EPISODE_AGGREGATION: "Episode 聚合",
    MemoryOperation.SCHEDULER: "记忆调度器",
}


def is_memory_system_enabled() -> bool:
    """返回记忆系统总开关状态。"""
    return bool(config.MEMORY_ENABLE_SYSTEM)


def get_memory_disabled_reason(operation: MemoryOperation) -> str:
    """构造统一的禁用提示。"""
    operation_label = _MEMORY_OPERATION_LABELS[operation]
    return f"记忆系统已禁用，无法执行{operation_label}"


def ensure_memory_system_enabled(operation: MemoryOperation) -> None:
    """要求记忆系统已启用，否则抛出统一错误。"""
    if not is_memory_system_enabled():
        raise ValidationError(reason=get_memory_disabled_reason(operation))
