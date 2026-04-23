from __future__ import annotations

import asyncio
import hashlib
import time
from datetime import datetime, timezone
from typing import Any

from tortoise.backends.base.client import BaseDBAsyncClient

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_kb_chunk import DBKBChunk
from nekro_agent.models.db_kb_document import DBKBDocument
from nekro_agent.services.kb.chunker import split_text_into_chunks
from nekro_agent.services.kb.extractors import extract_source_file
from nekro_agent.services.kb.qdrant_manager import kb_qdrant_manager
from nekro_agent.services.kb.reference_detector import detect_and_sync_document_references
from nekro_agent.services.memory.embedding_service import embed_batch, get_memory_embedding_dimension
from nekro_agent.services.system_broadcast import KbIndexProgressEvent, publish_kb_index_progress
from nekro_agent.services.workspace.manager import WorkspaceService

logger = get_sub_logger("kb.index")

PREVIEW_MAX_CHARS = 360
_INDEX_BATCH_SIZE = 10
_index_tasks: dict[int, Any] = {}
_pending_rebuilds: set[int] = set()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _preview_text(text: str, max_chars: int = PREVIEW_MAX_CHARS) -> str:
    normalized = " ".join(text.strip().split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 1]}…"


async def _publish_index_progress(
    document: DBKBDocument,
    *,
    active: bool = True,
    phase: str,
    started_at: int,
    progress_percent: int,
    total_chunks: int = 0,
    processed_chunks: int = 0,
    error_summary: str = "",
    expires_in_ms: int = 5000,
) -> None:
    await publish_kb_index_progress(
        KbIndexProgressEvent(
            workspace_id=document.workspace_id,
            document_id=document.id,
            active=active,
            title=document.title,
            source_path=document.source_path,
            phase=phase,  # type: ignore[arg-type]
            started_at=started_at,
            updated_at=int(time.time() * 1000),
            progress_percent=max(0, min(100, int(progress_percent))),
            total_chunks=max(0, int(total_chunks)),
            processed_chunks=max(0, int(processed_chunks)),
            expires_in_ms=expires_in_ms,
            error_summary=error_summary[:500],
        )
    )


async def ensure_kb_collection() -> bool:
    return await kb_qdrant_manager.ensure_collection(get_memory_embedding_dimension())


async def index_document(document: DBKBDocument) -> int:
    started_at = int(time.time() * 1000)
    WorkspaceService.ensure_kb_dirs(document.workspace_id)
    document.extract_status = "extracting"
    document.sync_status = "pending"
    document.last_error = None
    await document.save(update_fields=["extract_status", "sync_status", "last_error", "update_time"])
    await _publish_index_progress(document, phase="extracting", started_at=started_at, progress_percent=5)

    source_file = WorkspaceService.resolve_kb_source_path(document.workspace_id, document.source_path)
    extracted = extract_source_file(source_file, document.file_name)
    normalized_text = extracted.text.strip()
    normalized_rel_path = document.normalized_text_path or f"{document.id}.md"
    normalized_file = WorkspaceService.resolve_kb_normalized_path(document.workspace_id, normalized_rel_path)
    normalized_file.parent.mkdir(parents=True, exist_ok=True)
    normalized_file.write_text(normalized_text, encoding="utf-8")

    document.normalized_text_path = normalized_rel_path
    document.normalized_text_hash = _hash_text(normalized_text)
    document.extract_status = "ready"
    document.sync_status = "indexing"
    await document.save(
        update_fields=[
            "normalized_text_path",
            "normalized_text_hash",
            "extract_status",
            "sync_status",
            "update_time",
        ]
    )
    await _publish_index_progress(document, phase="chunking", started_at=started_at, progress_percent=20)

    existing_chunks = await DBKBChunk.filter(document_id=document.id).all()
    if existing_chunks:
        await kb_qdrant_manager.delete_chunk_points([chunk.id for chunk in existing_chunks])
        await DBKBChunk.filter(document_id=document.id).delete()

    drafts = split_text_into_chunks(normalized_text)
    if not drafts:
        document.chunk_count = 0
        document.sync_status = "ready"
        document.last_indexed_at = datetime.now(timezone.utc)
        await document.save(update_fields=["chunk_count", "sync_status", "last_indexed_at", "update_time"])
        await _publish_index_progress(
            document, phase="ready", started_at=started_at, progress_percent=100, expires_in_ms=4000
        )
        await detect_and_sync_document_references(document.workspace_id, document.id)
        return 0

    created_chunks: list[DBKBChunk] = []
    for index, draft in enumerate(drafts):
        created_chunks.append(
            await DBKBChunk.create(
                workspace_id=document.workspace_id,
                document_id=document.id,
                chunk_index=index,
                heading_path=draft.heading_path,
                char_start=draft.char_start,
                char_end=draft.char_end,
                token_count=_estimate_tokens(draft.content),
            )
        )
    await _publish_index_progress(
        document,
        phase="embedding",
        started_at=started_at,
        progress_percent=35,
        total_chunks=len(created_chunks),
        processed_chunks=0,
    )

    points: list[tuple[int, list[float], dict[str, object]]] = []
    processed_chunks = 0
    for batch_start in range(0, len(created_chunks), _INDEX_BATCH_SIZE):
        db_batch = created_chunks[batch_start : batch_start + _INDEX_BATCH_SIZE]
        draft_batch = drafts[batch_start : batch_start + _INDEX_BATCH_SIZE]
        embeddings = await embed_batch([draft.content for draft in draft_batch])
        for db_chunk, draft, embedding in zip(db_batch, draft_batch, embeddings, strict=False):
            if embedding is None:
                processed_chunks += 1
                continue
            db_chunk.embedding_ref = str(db_chunk.id)
            await db_chunk.save(update_fields=["embedding_ref", "update_time"])
            points.append(
                (
                    db_chunk.id,
                    embedding,
                    db_chunk.to_qdrant_payload(
                        document=document,
                        content_preview=_preview_text(draft.content),
                    ),
                )
            )
            processed_chunks += 1
        await _publish_index_progress(
            document,
            phase="embedding",
            started_at=started_at,
            progress_percent=35 + int((processed_chunks / max(1, len(created_chunks))) * 50),
            total_chunks=len(created_chunks),
            processed_chunks=processed_chunks,
        )

    await _publish_index_progress(
        document,
        phase="upserting",
        started_at=started_at,
        progress_percent=90,
        total_chunks=len(created_chunks),
        processed_chunks=processed_chunks,
    )
    await kb_qdrant_manager.batch_upsert(points)
    document.chunk_count = len(created_chunks)
    document.sync_status = "ready"
    document.last_indexed_at = datetime.now(timezone.utc)
    document.last_error = None
    await document.save(update_fields=["chunk_count", "sync_status", "last_indexed_at", "last_error", "update_time"])
    await _publish_index_progress(
        document,
        phase="ready",
        started_at=started_at,
        progress_percent=100,
        total_chunks=len(created_chunks),
        processed_chunks=processed_chunks,
        expires_in_ms=4000,
    )
    await detect_and_sync_document_references(document.workspace_id, document.id)
    return len(created_chunks)


async def rebuild_document(document: DBKBDocument) -> int:
    try:
        return await index_document(document)
    except Exception as e:
        logger.warning(f"知识库文档索引失败: workspace={document.workspace_id}, document_id={document.id}, error={e}")
        document.extract_status = "failed"
        document.sync_status = "failed"
        document.last_error = str(e)
        await document.save(update_fields=["extract_status", "sync_status", "last_error", "update_time"])
        await _publish_index_progress(
            document,
            phase="failed",
            started_at=int(time.time() * 1000),
            progress_percent=100,
            error_summary=str(e),
            expires_in_ms=8000,
        )
        raise


async def _run_rebuild_document_task(document_id: int) -> None:
    task = _index_tasks.get(document_id)
    try:
        while True:
            _pending_rebuilds.discard(document_id)
            document = await DBKBDocument.get_or_none(id=document_id)
            if document is None:
                return
            try:
                await rebuild_document(document)
            except Exception as e:
                logger.warning(f"后台知识库索引任务失败: document_id={document_id}, error={e}")
            if document_id not in _pending_rebuilds:
                return
            logger.info(f"知识库文档收到新的重建请求，继续重跑索引: document_id={document_id}")
    except Exception as e:
        logger.warning(f"后台知识库索引任务失败: document_id={document_id}, error={e}")
    finally:
        _pending_rebuilds.discard(document_id)
        if _index_tasks.get(document_id) is task:
            _index_tasks.pop(document_id, None)


async def schedule_rebuild_document(document: DBKBDocument) -> bool:
    existing = _index_tasks.get(document.id)
    if existing is not None and not existing.done():
        _pending_rebuilds.add(document.id)
        return True

    started_at = int(time.time() * 1000)
    await _publish_index_progress(
        document,
        phase="queued",
        started_at=started_at,
        progress_percent=0,
        expires_in_ms=3000,
    )
    task = asyncio.create_task(_run_rebuild_document_task(document.id))
    _index_tasks[document.id] = task
    return True


async def cancel_rebuild_document(document_id: int) -> bool:
    existing = _index_tasks.get(document_id)
    if existing is None or existing.done():
        return False
    existing.cancel()
    try:
        await existing
    except asyncio.CancelledError:
        pass
    return True


async def rebuild_workspace_documents(workspace_id: int) -> tuple[int, int]:
    """将工作区所有文档提交到后台索引队列。返回 (已调度数, 已跳过数)。"""
    documents = await DBKBDocument.filter(workspace_id=workspace_id).all()
    scheduled = 0
    skipped = 0
    for document in documents:
        if await schedule_rebuild_document(document):
            scheduled += 1
        else:
            skipped += 1
    return scheduled, skipped


async def delete_document_files(document: DBKBDocument) -> None:
    source_file = WorkspaceService.resolve_kb_source_path(document.workspace_id, document.source_path)
    if source_file.exists():
        source_file.unlink()
    if document.normalized_text_path:
        normalized_file = WorkspaceService.resolve_kb_normalized_path(
            document.workspace_id, document.normalized_text_path
        )
        if normalized_file.exists():
            normalized_file.unlink()


async def delete_document_index(document: DBKBDocument) -> None:
    chunks = await DBKBChunk.filter(document_id=document.id).all()
    if chunks:
        await kb_qdrant_manager.delete_chunk_points([chunk.id for chunk in chunks])
        await DBKBChunk.filter(document_id=document.id).delete()


async def list_document_chunk_ids(document_id: int) -> list[int]:
    chunk_ids = await DBKBChunk.filter(document_id=document_id).values_list("id", flat=True)
    return [int(chunk_id) for chunk_id in chunk_ids]


async def delete_document_chunk_rows(
    document_id: int,
    *,
    using_db: BaseDBAsyncClient | None = None,
) -> int:
    queryset = DBKBChunk.filter(document_id=document_id)
    if using_db is not None:
        queryset = queryset.using_db(using_db)
    return await queryset.delete()


async def delete_document_vector_points(chunk_ids: list[int]) -> int:
    if not chunk_ids:
        return 0
    await kb_qdrant_manager.delete_chunk_points(chunk_ids)
    return len(chunk_ids)


async def sync_document_index_metadata(document: DBKBDocument) -> int:
    chunk_ids = await DBKBChunk.filter(document_id=document.id).values_list("id", flat=True)
    if not chunk_ids:
        return 0
    await kb_qdrant_manager.set_payload(
        chunk_ids=list(chunk_ids),
        payload={
            "category": document.category,
            "tags": document.tags if isinstance(document.tags, list) else [],
            "is_enabled": document.is_enabled,
        },
    )
    return len(chunk_ids)
