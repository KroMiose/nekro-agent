from __future__ import annotations

import asyncio
import hashlib
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.transactions import in_transaction

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_kb_asset import DBKBAsset
from nekro_agent.models.db_kb_asset_chunk import DBKBAssetChunk
from nekro_agent.services.kb.chunker import ChunkDraft, split_text_into_chunks
from nekro_agent.services.kb.extractors import extract_source_file
from nekro_agent.services.kb.library_qdrant_manager import kb_library_qdrant_manager
from nekro_agent.services.kb.library_service import (
    ensure_kb_library_dirs,
    resolve_kb_library_normalized_path,
    resolve_kb_library_source_path,
)
from nekro_agent.services.kb.reference_detector import detect_and_sync_asset_references
from nekro_agent.services.memory.embedding_service import embed_kb_batch, get_kb_embedding_dimension
from nekro_agent.services.system_broadcast import KbLibraryIndexProgressEvent, publish_kb_library_index_progress

logger = get_sub_logger("kb.library_index")

PREVIEW_MAX_CHARS = 360
INDEX_BATCH_SIZE = 10
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
    asset: DBKBAsset,
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
    await publish_kb_library_index_progress(
        KbLibraryIndexProgressEvent(
            asset_id=asset.id,
            active=active,
            title=asset.title,
            source_path=asset.source_path,
            phase=phase,  # type: ignore[arg-type]
            started_at=started_at,
            updated_at=int(datetime.now(timezone.utc).timestamp() * 1000),
            progress_percent=max(0, min(100, int(progress_percent))),
            total_chunks=max(0, int(total_chunks)),
            processed_chunks=max(0, int(processed_chunks)),
            expires_in_ms=expires_in_ms,
            error_summary=error_summary[:500],
        )
    )


async def ensure_kb_library_collection() -> bool:
    return await kb_library_qdrant_manager.ensure_collection(get_kb_embedding_dimension())


async def _embed_chunk_drafts(
    asset: DBKBAsset,
    drafts: list[ChunkDraft],
    *,
    started_at: int,
) -> list[list[float]]:
    """在不触碰现有索引的前提下完成全部向量化，任一 chunk 失败即抛出。"""
    await _publish_index_progress(
        asset,
        phase="embedding",
        started_at=started_at,
        progress_percent=35,
        total_chunks=len(drafts),
        processed_chunks=0,
    )

    vectors: list[list[float] | None] = []
    for batch_start in range(0, len(drafts), INDEX_BATCH_SIZE):
        draft_batch = drafts[batch_start : batch_start + INDEX_BATCH_SIZE]
        embeddings = await embed_kb_batch([draft.content for draft in draft_batch])
        vectors.extend(embeddings[: len(draft_batch)])
        vectors.extend([None] * max(0, len(draft_batch) - len(embeddings)))
        await _publish_index_progress(
            asset,
            phase="embedding",
            started_at=started_at,
            progress_percent=35 + int((len(vectors) / max(1, len(drafts))) * 50),
            total_chunks=len(drafts),
            processed_chunks=len(vectors),
        )

    failed_embeddings = sum(1 for vector in vectors if vector is None)
    if failed_embeddings:
        raise RuntimeError(f"全局知识库向量化失败：共 {failed_embeddings}/{len(drafts)} 个 chunk 未能生成 embedding")
    return [vector for vector in vectors if vector is not None]


async def _swap_asset_index(
    asset: DBKBAsset,
    drafts: list[ChunkDraft],
    vectors: list[list[float]],
) -> int:
    """原子切换资产索引：新数据全部就绪后才替换旧的 chunk 行与向量点。

    DB 事务包住「删旧行 + 建新行 + 写入 Qdrant」，Qdrant 写入失败会连同 DB 一起回滚，
    旧索引保持原样可检索；只有事务提交成功后才清理旧向量点。
    """
    stale_chunk_ids = await list_asset_chunk_ids(asset.id)
    created_count = 0

    async with in_transaction() as conn:
        await DBKBAssetChunk.filter(asset_id=asset.id).using_db(conn).delete()
        if drafts:
            await DBKBAssetChunk.bulk_create(
                [
                    DBKBAssetChunk(
                        asset_id=asset.id,
                        chunk_index=index,
                        heading_path=draft.heading_path,
                        char_start=draft.char_start,
                        char_end=draft.char_end,
                        token_count=_estimate_tokens(draft.content),
                    )
                    for index, draft in enumerate(drafts)
                ],
                batch_size=INDEX_BATCH_SIZE,
                using_db=conn,
            )
            created_chunks = (
                await DBKBAssetChunk.filter(asset_id=asset.id).using_db(conn).order_by("chunk_index").all()
            )
            for chunk in created_chunks:
                chunk.embedding_ref = str(chunk.id)
            await DBKBAssetChunk.bulk_update(
                created_chunks,
                fields=["embedding_ref", "update_time"],
                batch_size=INDEX_BATCH_SIZE,
                using_db=conn,
            )
            await kb_library_qdrant_manager.batch_upsert(
                [
                    (
                        chunk.id,
                        vector,
                        chunk.to_qdrant_payload(asset=asset, content_preview=_preview_text(draft.content)),
                    )
                    for chunk, draft, vector in zip(created_chunks, drafts, vectors, strict=True)
                ]
            )
            created_count = len(created_chunks)

    try:
        await delete_asset_vector_points(stale_chunk_ids)
    except Exception as e:
        logger.warning(f"清理全局知识库旧向量点失败（不影响新索引可用性）: asset_id={asset.id}, error={e}")

    return created_count


async def index_asset(asset: DBKBAsset) -> int:
    started_at = int(datetime.now(timezone.utc).timestamp() * 1000)
    ensure_kb_library_dirs()
    asset.extract_status = "extracting"
    asset.sync_status = "pending"
    asset.last_error = None
    await asset.save(update_fields=["extract_status", "sync_status", "last_error", "update_time"])
    await _publish_index_progress(asset, phase="extracting", started_at=started_at, progress_percent=5)

    source_file = resolve_kb_library_source_path(asset.source_path)
    extracted = await asyncio.to_thread(extract_source_file, source_file, asset.file_name)
    normalized_text = extracted.text.strip()
    normalized_rel_path = asset.normalized_text_path or f"{asset.id}.md"
    normalized_file = resolve_kb_library_normalized_path(normalized_rel_path)
    staged_file = await asyncio.to_thread(_write_staged_normalized_text, normalized_file, normalized_text)

    asset.extract_status = "ready"
    asset.sync_status = "indexing"
    await asset.save(update_fields=["extract_status", "sync_status", "update_time"])
    await _publish_index_progress(asset, phase="chunking", started_at=started_at, progress_percent=20)

    committed = False
    try:
        drafts = split_text_into_chunks(normalized_text)
        # staging 阶段：向量全部就绪前不删除任何既有 chunk / 向量点，也不覆盖线上规范化文本
        vectors = await _embed_chunk_drafts(asset, drafts, started_at=started_at) if drafts else []

        if drafts:
            await _publish_index_progress(
                asset,
                phase="upserting",
                started_at=started_at,
                progress_percent=90,
                total_chunks=len(drafts),
                processed_chunks=len(drafts),
            )
        chunk_count = await _swap_asset_index(asset, drafts, vectors)
        staged_file.replace(normalized_file)
        committed = True
    finally:
        if not committed:
            _discard_staged_normalized_text(staged_file)

    asset.normalized_text_path = normalized_rel_path
    asset.normalized_text_hash = _hash_text(normalized_text)
    asset.chunk_count = chunk_count
    asset.sync_status = "ready"
    asset.last_indexed_at = datetime.now(timezone.utc)
    asset.last_error = None
    await asset.save(
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
        asset,
        phase="ready",
        started_at=started_at,
        progress_percent=100,
        total_chunks=chunk_count,
        processed_chunks=chunk_count,
        expires_in_ms=4000,
    )
    await detect_and_sync_asset_references(asset.id)
    return chunk_count


async def rebuild_asset(asset: DBKBAsset) -> int:
    try:
        return await index_asset(asset)
    except asyncio.CancelledError:
        asset.extract_status = "pending"
        asset.sync_status = "pending"
        asset.last_error = "任务被取消"
        await asset.save(update_fields=["extract_status", "sync_status", "last_error", "update_time"])
        raise
    except Exception as e:
        logger.warning(f"全局知识库资产索引失败: asset_id={asset.id}, error={e}")
        asset.extract_status = "failed"
        asset.sync_status = "failed"
        asset.last_error = str(e)
        await asset.save(update_fields=["extract_status", "sync_status", "last_error", "update_time"])
        await _publish_index_progress(
            asset,
            phase="failed",
            started_at=int(datetime.now(timezone.utc).timestamp() * 1000),
            progress_percent=100,
            error_summary=str(e),
            expires_in_ms=8000,
        )
        raise


async def _run_rebuild_asset_task(asset_id: int) -> None:
    task = _index_tasks.get(asset_id)
    try:
        async with _index_semaphore:
            while True:
                _pending_rebuilds.discard(asset_id)
                asset = await DBKBAsset.get_or_none(id=asset_id)
                if asset is None:
                    return
                try:
                    await rebuild_asset(asset)
                except Exception:
                    pass  # rebuild_asset 内部已记录日志
                if asset_id not in _pending_rebuilds:
                    return
                logger.info(f"全局知识库资产收到新的重建请求，继续重跑索引: asset_id={asset_id}")
    except Exception as e:
        logger.warning(f"后台全局知识库索引任务失败: asset_id={asset_id}, error={e}")
    finally:
        _pending_rebuilds.discard(asset_id)
        if _index_tasks.get(asset_id) is task:
            _index_tasks.pop(asset_id, None)


async def schedule_rebuild_asset(asset: DBKBAsset) -> bool:
    existing = _index_tasks.get(asset.id)
    if existing is not None and not existing.done():
        _pending_rebuilds.add(asset.id)
        return True
    await _publish_index_progress(
        asset,
        phase="queued",
        started_at=int(datetime.now(timezone.utc).timestamp() * 1000),
        progress_percent=0,
        expires_in_ms=3000,
    )
    task = asyncio.create_task(_run_rebuild_asset_task(asset.id))
    _index_tasks[asset.id] = task
    return True


async def cancel_rebuild_asset(asset_id: int) -> bool:
    existing = _index_tasks.get(asset_id)
    if existing is None or existing.done():
        return False
    existing.cancel()
    try:
        await existing
    except asyncio.CancelledError:
        pass
    return True


async def delete_asset_files(asset: DBKBAsset) -> None:
    source_file = resolve_kb_library_source_path(asset.source_path)
    if source_file.exists():
        source_file.unlink()
    if asset.normalized_text_path:
        normalized_file = resolve_kb_library_normalized_path(asset.normalized_text_path)
        if normalized_file.exists():
            normalized_file.unlink()


async def delete_asset_index(asset: DBKBAsset) -> None:
    chunks = await DBKBAssetChunk.filter(asset_id=asset.id).all()
    if chunks:
        await kb_library_qdrant_manager.delete_chunk_points([chunk.id for chunk in chunks])
        await DBKBAssetChunk.filter(asset_id=asset.id).delete()


async def list_asset_chunk_ids(asset_id: int) -> list[int]:
    chunk_ids = await DBKBAssetChunk.filter(asset_id=asset_id).values_list("id", flat=True)
    return [int(chunk_id) for chunk_id in chunk_ids]


async def delete_asset_chunk_rows(
    asset_id: int,
    *,
    using_db: BaseDBAsyncClient | None = None,
) -> int:
    queryset = DBKBAssetChunk.filter(asset_id=asset_id)
    if using_db is not None:
        queryset = queryset.using_db(using_db)
    return await queryset.delete()


async def delete_asset_vector_points(chunk_ids: list[int]) -> int:
    if not chunk_ids:
        return 0
    await kb_library_qdrant_manager.delete_chunk_points(chunk_ids)
    return len(chunk_ids)


async def sync_asset_index_metadata(asset: DBKBAsset) -> int:
    chunk_ids = await DBKBAssetChunk.filter(asset_id=asset.id).values_list("id", flat=True)
    if not chunk_ids:
        return 0
    await kb_library_qdrant_manager.set_payload(
        chunk_ids=list(chunk_ids),
        payload={
            "category": asset.category,
            "tags": asset.tags if isinstance(asset.tags, list) else [],
            "is_enabled": asset.is_enabled,
        },
    )
    return len(chunk_ids)
