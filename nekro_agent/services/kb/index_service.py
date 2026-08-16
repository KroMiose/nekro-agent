from __future__ import annotations

import asyncio
import hashlib
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from nekro_agent.core.config import config
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
_INDEX_CONCURRENCY_DEFAULT = 3
_index_tasks: dict[int, Any] = {}
_pending_rebuilds: set[int] = set()

try:
    _INDEX_CONCURRENCY = max(1, int(config.KB_INDEX_CONCURRENCY))
except (TypeError, ValueError):
    # 配置值非法时回退默认并发，避免索引任务因错误配置而崩溃
    _INDEX_CONCURRENCY = _INDEX_CONCURRENCY_DEFAULT
_index_semaphore = asyncio.Semaphore(_INDEX_CONCURRENCY)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _preview_text(text: str, max_chars: int = PREVIEW_MAX_CHARS) -> str:
    normalized = " ".join(text.strip().split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 1]}…"


def _normalized_rel_path_for(document_id: int, text_hash: str) -> str:
    """规范化文本按内容寻址命名，让新旧两版可以并存到切换完成为止。"""
    return f"{document_id}-{text_hash[:32]}.md"


def _write_normalized_text(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, "utf-8")


def _discard_normalized_text(target: Path) -> None:
    with suppress(OSError):
        target.unlink()


@dataclass(frozen=True)
class _IndexStateSnapshot:
    """重建开始前的索引状态，用于失败时把仍然完好的旧索引恢复成可检索。"""

    extract_status: str
    sync_status: str
    chunk_count: int
    last_indexed_at: datetime | None
    normalized_text_path: str
    normalized_text_hash: str

    @property
    def searchable(self) -> bool:
        """与 search_service._source_is_search_ready 的状态条件保持一致。"""
        return self.extract_status == "ready" and self.sync_status == "ready"


_RESTORE_UPDATE_FIELDS = [
    "extract_status",
    "sync_status",
    "chunk_count",
    "last_indexed_at",
    "normalized_text_path",
    "normalized_text_hash",
    "last_error",
    "update_time",
]


def _snapshot_document_state(document: DBKBDocument) -> _IndexStateSnapshot:
    return _IndexStateSnapshot(
        extract_status=document.extract_status,
        sync_status=document.sync_status,
        chunk_count=document.chunk_count,
        last_indexed_at=document.last_indexed_at,
        normalized_text_path=document.normalized_text_path or "",
        normalized_text_hash=document.normalized_text_hash,
    )


async def _restore_document_state(
    document: DBKBDocument,
    snapshot: _IndexStateSnapshot,
    *,
    last_error: str,
) -> None:
    """回退到重建前状态：旧 chunk / 向量点 / 规范化文本都还在，索引必须保持可检索。"""
    document.extract_status = snapshot.extract_status
    document.sync_status = snapshot.sync_status
    document.chunk_count = snapshot.chunk_count
    document.last_indexed_at = snapshot.last_indexed_at
    document.normalized_text_path = snapshot.normalized_text_path
    document.normalized_text_hash = snapshot.normalized_text_hash
    document.last_error = last_error
    await document.save(update_fields=_RESTORE_UPDATE_FIELDS)


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


def _staged_qdrant_payload(chunk: DBKBChunk, *, document: DBKBDocument, content_preview: str) -> dict[str, object]:
    """staging 点先写成不可检索：is_enabled=False 不满足检索过滤条件，DB 提交后再激活。"""
    payload = chunk.to_qdrant_payload(document=document, content_preview=content_preview)
    payload["is_enabled"] = False
    return payload


async def _swap_document_index(
    document: DBKBDocument,
    drafts: list[ChunkDraft],
    vectors: list[list[float]],
    *,
    snapshot: _IndexStateSnapshot,
    normalized_rel_path: str,
    normalized_text_hash: str,
) -> int:
    """两阶段切换文档索引，DB 提交是唯一的切换点。

    Qdrant 写入不受 Postgres 事务保护，所以新向量点先以 is_enabled=False 写入：它们不满足
    检索过滤条件，旧点仍是唯一可检索的一份。激活放在事务内、紧邻提交的最后一步——激活失败会
    连同 DB 一起回滚，旧 chunk 行、旧向量点、旧规范化文本全部原样保留，旧索引继续可检索；
    回滚时刚写入的新点由 finally 尽力清除。
    提交之后只剩纯清理动作（删旧点、删旧文本），失败仅留残留，不影响新索引可用性。
    """
    stale_chunk_ids = await list_document_chunk_ids(document.id)
    staged_point_ids: list[int] = []
    created_count = 0
    switched = False

    try:
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
                            _staged_qdrant_payload(
                                chunk,
                                document=document,
                                content_preview=_preview_text(draft.content),
                            ),
                        )
                        for chunk, draft, vector in zip(created_chunks, drafts, vectors, strict=True)
                    ]
                )
                staged_point_ids = [chunk.id for chunk in created_chunks]
                created_count = len(created_chunks)

            # 元数据与 chunk 行在同一事务内 flip，避免出现「新 chunk + 旧文本指针」的中间态
            document.normalized_text_path = normalized_rel_path
            document.normalized_text_hash = normalized_text_hash
            document.chunk_count = created_count
            document.extract_status = "ready"
            document.sync_status = "ready"
            document.last_indexed_at = datetime.now(timezone.utc)
            document.last_error = None
            await document.save(
                update_fields=[
                    "normalized_text_path",
                    "normalized_text_hash",
                    "chunk_count",
                    "extract_status",
                    "sync_status",
                    "last_indexed_at",
                    "last_error",
                    "update_time",
                ],
                using_db=conn,
            )

            # 提交前最后一步激活新点：失败即整体回滚，旧 chunk / 旧向量点 / 旧文本原封不动
            if staged_point_ids:
                await kb_qdrant_manager.set_payload(
                    chunk_ids=staged_point_ids,
                    payload={"is_enabled": document.is_enabled},
                )
        switched = True
    finally:
        if not switched and staged_point_ids:
            try:
                await delete_document_vector_points(staged_point_ids)
            except Exception as e:
                logger.warning(f"清理知识库 staging 向量点失败: document_id={document.id}, error={e}")

    try:
        await delete_document_vector_points(stale_chunk_ids)
    except Exception as e:
        logger.warning(f"清理知识库旧向量点失败（不影响新索引可用性）: document_id={document.id}, error={e}")
    if snapshot.normalized_text_path and snapshot.normalized_text_path != normalized_rel_path:
        with suppress(ValueError):
            _discard_normalized_text(
                WorkspaceService.resolve_kb_normalized_path(document.workspace_id, snapshot.normalized_text_path)
            )

    return created_count


async def index_document(document: DBKBDocument) -> int:
    started_at = int(time.time() * 1000)
    WorkspaceService.ensure_kb_dirs(document.workspace_id)
    snapshot = _snapshot_document_state(document)

    # 已有可检索索引时不下调状态：重建期间旧索引对搜索保持可见，进度另经 SSE 推送
    document.last_error = None
    if snapshot.searchable:
        await document.save(update_fields=["last_error", "update_time"])
    else:
        document.extract_status = "extracting"
        document.sync_status = "pending"
        await document.save(update_fields=["extract_status", "sync_status", "last_error", "update_time"])
    await _publish_index_progress(document, phase="extracting", started_at=started_at, progress_percent=5)

    source_file = WorkspaceService.resolve_kb_source_path(document.workspace_id, document.source_path)
    extracted = await asyncio.to_thread(extract_source_file, source_file, document.file_name)
    normalized_text = extracted.text.strip()
    normalized_text_hash = _hash_text(normalized_text)
    staged_rel_path = _normalized_rel_path_for(document.id, normalized_text_hash)
    staged_file = WorkspaceService.resolve_kb_normalized_path(document.workspace_id, staged_rel_path)
    reuses_live_text = staged_rel_path == snapshot.normalized_text_path

    if not snapshot.searchable:
        document.extract_status = "ready"
        document.sync_status = "indexing"
        await document.save(update_fields=["extract_status", "sync_status", "update_time"])
    await _publish_index_progress(document, phase="chunking", started_at=started_at, progress_percent=20)

    committed = False
    try:
        # staging 阶段：新文本写到独立路径，旧 chunk / 向量点 / 旧文本一律不动
        if not reuses_live_text or not staged_file.exists():
            await asyncio.to_thread(_write_normalized_text, staged_file, normalized_text)

        drafts = split_text_into_chunks(normalized_text)
        if drafts:
            vectors = await _embed_chunk_drafts(document, drafts, started_at=started_at)
            await _publish_index_progress(
                document,
                phase="upserting",
                started_at=started_at,
                progress_percent=90,
                total_chunks=len(drafts),
                processed_chunks=len(drafts),
            )
        else:
            # 空文本也必须显式完成切换：清空旧 chunk/向量点，并把 chunk_count 落到 0。
            vectors = []
        chunk_count = await _swap_document_index(
            document,
            drafts,
            vectors,
            snapshot=snapshot,
            normalized_rel_path=staged_rel_path,
            normalized_text_hash=normalized_text_hash,
        )
        committed = True
    finally:
        if not committed and not reuses_live_text:
            _discard_normalized_text(staged_file)

    # 切换已提交：此后不得再有可失败步骤，否则 rebuild_document 会误把元数据回滚到已删除的旧文本
    return chunk_count


async def rebuild_document(document: DBKBDocument) -> int:
    snapshot = _snapshot_document_state(document)
    try:
        chunk_count = await index_document(document)
    except asyncio.CancelledError:
        if snapshot.searchable:
            await _restore_document_state(document, snapshot, last_error="任务被取消")
        else:
            document.extract_status = "pending"
            document.sync_status = "pending"
            document.last_error = "任务被取消"
            await document.save(update_fields=["extract_status", "sync_status", "last_error", "update_time"])
        raise
    except Exception as e:
        logger.warning(f"知识库文档索引失败: workspace={document.workspace_id}, document_id={document.id}, error={e}")
        if snapshot.searchable:
            logger.info(f"知识库文档重建失败，回退到上一次成功的索引并保持可检索: document_id={document.id}")
            await _restore_document_state(document, snapshot, last_error=str(e))
        else:
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

    # 索引已生效，以下均为尽力而为的收尾，失败不得回滚状态
    try:
        await _publish_index_progress(
            document,
            phase="ready",
            started_at=int(time.time() * 1000),
            progress_percent=100,
            total_chunks=chunk_count,
            processed_chunks=chunk_count,
            expires_in_ms=4000,
        )
        await detect_and_sync_document_references(document.workspace_id, document.id)
    except Exception as e:
        logger.warning(f"知识库索引收尾处理失败（索引已生效）: document_id={document.id}, error={e}")
    return chunk_count


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
