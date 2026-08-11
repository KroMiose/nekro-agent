from __future__ import annotations

import asyncio
import hashlib
import time
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_kb_chunk import DBKBChunk
from nekro_agent.models.db_kb_document import DBKBDocument
from nekro_agent.services.kb.chunker import ChunkDraft, split_text_into_chunks
from nekro_agent.services.kb.extractors import extract_source_file
from nekro_agent.services.kb.qdrant_manager import kb_qdrant_manager
from nekro_agent.services.kb.reference_detector import detect_and_sync_document_references
from nekro_agent.services.memory.embedding_service import embed_kb_batch, get_kb_embedding_dimension
from nekro_agent.services.system_broadcast import KbIndexProgressEvent, publish_kb_index_progress
from nekro_agent.services.workspace.manager import WorkspaceService

logger = get_sub_logger("kb.index")

PREVIEW_MAX_CHARS = 360
_INDEX_BATCH_SIZE = 10
_INDEX_CONCURRENCY = 3
_index_semaphore = asyncio.Semaphore(_INDEX_CONCURRENCY)
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


def _write_staged_normalized_text(target: Path, text: str) -> Path:
    """规范化文本先落到同目录临时文件。

    检索按 char_start/char_end 从规范化文本取原文，提前覆盖会让仍在服务的旧 chunk 错位，
    因此索引成功前不能动线上文件。
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(f"{target.name}.staging")
    staged.write_text(text, "utf-8")
    return staged


def _discard_staged_normalized_text(staged: Path) -> None:
    with suppress(OSError):
        staged.unlink()


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
    return await kb_qdrant_manager.ensure_collection(get_kb_embedding_dimension())


async def _embed_chunk_drafts(
    document: DBKBDocument,
    drafts: list[ChunkDraft],
    *,
    started_at: int,
) -> list[list[float]]:
    """在不触碰现有索引的前提下完成全部向量化，任一 chunk 失败即抛出。"""
    await _publish_index_progress(
        document,
        phase="embedding",
        started_at=started_at,
        progress_percent=35,
        total_chunks=len(drafts),
        processed_chunks=0,
    )

    vectors: list[list[float] | None] = []
    for batch_start in range(0, len(drafts), _INDEX_BATCH_SIZE):
        draft_batch = drafts[batch_start : batch_start + _INDEX_BATCH_SIZE]
        embeddings = await embed_kb_batch([draft.content for draft in draft_batch])
        vectors.extend(embeddings[: len(draft_batch)])
        vectors.extend([None] * max(0, len(draft_batch) - len(embeddings)))
        await _publish_index_progress(
            document,
            phase="embedding",
            started_at=started_at,
            progress_percent=35 + int((len(vectors) / max(1, len(drafts))) * 50),
            total_chunks=len(drafts),
            processed_chunks=len(vectors),
        )

    failed_embeddings = sum(1 for vector in vectors if vector is None)
    if failed_embeddings:
        raise RuntimeError(f"知识库向量化失败：共 {failed_embeddings}/{len(drafts)} 个 chunk 未能生成 embedding")
    return [vector for vector in vectors if vector is not None]


async def _swap_document_index(
    document: DBKBDocument,
    drafts: list[ChunkDraft],
    vectors: list[list[float]],
) -> int:
    """原子切换文档索引：新数据全部就绪后才替换旧的 chunk 行与向量点。

    DB 事务包住「删旧行 + 建新行 + 写入 Qdrant」，Qdrant 写入失败会连同 DB 一起回滚，
    旧索引保持原样可检索；只有事务提交成功后才清理旧向量点。
    """
    stale_chunk_ids = await list_document_chunk_ids(document.id)
    created_count = 0

    async with in_transaction() as conn:
        await DBKBChunk.filter(document_id=document.id).using_db(conn).delete()
        if drafts:
            await DBKBChunk.bulk_create(
                [
                    DBKBChunk(
                        workspace_id=document.workspace_id,
                        document_id=document.id,
                        chunk_index=index,
                        heading_path=draft.heading_path,
                        char_start=draft.char_start,
                        char_end=draft.char_end,
                        token_count=_estimate_tokens(draft.content),
                    )
                    for index, draft in enumerate(drafts)
                ],
                batch_size=_INDEX_BATCH_SIZE,
                using_db=conn,
            )
            created_chunks = (
                await DBKBChunk.filter(document_id=document.id, workspace_id=document.workspace_id)
                .using_db(conn)
                .order_by("chunk_index")
                .all()
            )
            for chunk in created_chunks:
                chunk.embedding_ref = str(chunk.id)
            await DBKBChunk.bulk_update(
                created_chunks,
                fields=["embedding_ref", "update_time"],
                batch_size=_INDEX_BATCH_SIZE,
                using_db=conn,
            )
            await kb_qdrant_manager.batch_upsert(
                [
                    (
                        chunk.id,
                        vector,
                        chunk.to_qdrant_payload(document=document, content_preview=_preview_text(draft.content)),
                    )
                    for chunk, draft, vector in zip(created_chunks, drafts, vectors, strict=True)
                ]
            )
            created_count = len(created_chunks)

    try:
        await delete_document_vector_points(stale_chunk_ids)
    except Exception as e:
        logger.warning(f"清理知识库旧向量点失败（不影响新索引可用性）: document_id={document.id}, error={e}")

    return created_count


async def index_document(document: DBKBDocument) -> int:
    started_at = int(time.time() * 1000)
    WorkspaceService.ensure_kb_dirs(document.workspace_id)
    document.extract_status = "extracting"
    document.sync_status = "pending"
    document.last_error = None
    await document.save(update_fields=["extract_status", "sync_status", "last_error", "update_time"])
    await _publish_index_progress(document, phase="extracting", started_at=started_at, progress_percent=5)

    source_file = WorkspaceService.resolve_kb_source_path(document.workspace_id, document.source_path)
    extracted = await asyncio.to_thread(extract_source_file, source_file, document.file_name)
    normalized_text = extracted.text.strip()
    normalized_rel_path = document.normalized_text_path or f"{document.id}.md"
    normalized_file = WorkspaceService.resolve_kb_normalized_path(document.workspace_id, normalized_rel_path)
    staged_file = await asyncio.to_thread(_write_staged_normalized_text, normalized_file, normalized_text)

    document.extract_status = "ready"
    document.sync_status = "indexing"
    await document.save(update_fields=["extract_status", "sync_status", "update_time"])
    await _publish_index_progress(document, phase="chunking", started_at=started_at, progress_percent=20)

    committed = False
    try:
        drafts = split_text_into_chunks(normalized_text)
        # staging 阶段：向量全部就绪前不删除任何既有 chunk / 向量点，也不覆盖线上规范化文本
        vectors = await _embed_chunk_drafts(document, drafts, started_at=started_at) if drafts else []

        if drafts:
            await _publish_index_progress(
                document,
                phase="upserting",
                started_at=started_at,
                progress_percent=90,
                total_chunks=len(drafts),
                processed_chunks=len(drafts),
            )
        chunk_count = await _swap_document_index(document, drafts, vectors)
        staged_file.replace(normalized_file)
        committed = True
    finally:
        if not committed:
            _discard_staged_normalized_text(staged_file)

    document.normalized_text_path = normalized_rel_path
    document.normalized_text_hash = _hash_text(normalized_text)
    document.chunk_count = chunk_count
    document.sync_status = "ready"
    document.last_indexed_at = datetime.now(timezone.utc)
    document.last_error = None
    await document.save(
        update_fields=[
            "normalized_text_path",
            "normalized_text_hash",
            "chunk_count",
            "sync_status",
            "last_indexed_at",
            "last_error",
            "update_time",
        ]
    )
    await _publish_index_progress(
        document,
        phase="ready",
        started_at=started_at,
        progress_percent=100,
        total_chunks=chunk_count,
        processed_chunks=chunk_count,
        expires_in_ms=4000,
    )
    await detect_and_sync_document_references(document.workspace_id, document.id)
    return chunk_count


async def rebuild_document(document: DBKBDocument) -> int:
    try:
        return await index_document(document)
    except asyncio.CancelledError:
        document.extract_status = "pending"
        document.sync_status = "pending"
        document.last_error = "任务被取消"
        await document.save(update_fields=["extract_status", "sync_status", "last_error", "update_time"])
        raise
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
        async with _index_semaphore:
            while True:
                _pending_rebuilds.discard(document_id)
                document = await DBKBDocument.get_or_none(id=document_id)
                if document is None:
                    return
                try:
                    await rebuild_document(document)
                except Exception:
                    pass  # rebuild_document 内部已记录日志
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
    """将文档提交到后台索引队列。返回 True 表示新建了任务，False 表示已有任务在跑（追加到 pending）。"""
    existing = _index_tasks.get(document.id)
    if existing is not None and not existing.done():
        _pending_rebuilds.add(document.id)
        return False

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
    new_tasks = 0
    merged = 0
    for document in documents:
        if await schedule_rebuild_document(document):
            new_tasks += 1
        else:
            merged += 1
    return new_tasks + merged, 0


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
