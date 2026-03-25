"""记忆系统服务模块

提供统一双态记忆系统的核心功能：
- 情景记忆（Episodic）与语义记忆（Semantic）的双态存储
- 向量化检索与关系图谱
- 记忆生命周期管理（衰减、强化、清理）
- 记忆维护调度
"""

from nekro_agent.services.memory.consolidator import (
    ConsolidationResult,
    EpisodicConsolidator,
    PersonaContext,
    consolidate_workspace,
)
from nekro_agent.services.memory.embedding_service import (
    EmbeddingService,
    embed_batch,
    embed_text,
    embedding_service,
)
from nekro_agent.services.memory.episode_aggregator import (
    EpisodeAggregationResult,
    EpisodeAggregator,
    aggregate_workspace_episodes,
)
from nekro_agent.services.memory.qdrant_manager import (
    MEMORY_PARAGRAPH_COLLECTION,
    MemoryQdrantManager,
    memory_qdrant_manager,
)
from nekro_agent.services.memory.retriever import (
    MemoryRecallQuery,
    MemoryRetriever,
    RetrievalResult,
    RetrievedMemory,
    compile_memories_for_context,
    format_memories_for_context,
    retrieve_memories,
)
from nekro_agent.services.memory.scheduler import (
    MemoryMaintenanceScheduler,
    memory_scheduler,
)
from nekro_agent.services.memory.semantic_writer import persist_cc_task_memory

__all__ = [
    # Consolidator
    "ConsolidationResult",
    "EpisodicConsolidator",
    "PersonaContext",
    "consolidate_workspace",
    # Embedding
    "EmbeddingService",
    "embed_batch",
    "embed_text",
    "embedding_service",
    # Episode
    "EpisodeAggregationResult",
    "EpisodeAggregator",
    "aggregate_workspace_episodes",
    # Qdrant
    "MEMORY_PARAGRAPH_COLLECTION",
    "MemoryQdrantManager",
    "memory_qdrant_manager",
    # Retriever
    "MemoryRetriever",
    "MemoryRecallQuery",
    "RetrievalResult",
    "RetrievedMemory",
    "compile_memories_for_context",
    "format_memories_for_context",
    "retrieve_memories",
    # Scheduler
    "MemoryMaintenanceScheduler",
    "memory_scheduler",
    # Semantic Writer
    "persist_cc_task_memory",
]
