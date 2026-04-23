from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any

from tortoise.backends.base.client import BaseDBAsyncClient

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_kb_asset import DBKBAsset
from nekro_agent.models.db_kb_asset_chunk import DBKBAssetChunk
from nekro_agent.services.kb.chunker import split_text_into_chunks
from nekro_agent.services.kb.extractors import extract_source_file
from nekro_agent.services.kb.library_qdrant_manager import kb_library_qdrant_manager
from nekro_agent.services.kb.library_service import (
    ensure_kb_library_dirs,
    resolve_kb_library_normalized_path,
    resolve_kb_library_source_path,
)
from nekro_agent.services.kb.reference_detector import detect_and_sync_asset_references
from nekro_agent.services.memory.embedding_service import embed_batch, get_memory_embedding_dimension
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
    return await kb_library_qdrant_manager.ensure_collection(get_memory_embedding_dimension())


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
    normalized_file.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(normalized_file.write_text, normalized_text, "utf-8")

    asset.normalized_text_path = normalized_rel_path
    asset.normalized_text_hash = _hash_text(normalized_text)
    asset.extract_status = "ready"
    asset.sync_status = "indexing"
    await asset.save(
        update_fields=[
            "normalized_text_path",
            "normalized_text_hash",
            "extract_status",
            "sync_status",
            "update_time",
        ]
    )
    await _publish_index_progress(asset, phase="chunking", started_at=started_at, progress_percent=20)

    existing_chunks = await DBKBAssetChunk.filter(asset_id=asset.id).all()
    if existing_chunks:
        await kb_library_qdrant_manager.delete_chunk_points([chunk.id for chunk in existing_chunks])
        await DBKBAssetChunk.filter(asset_id=asset.id).delete()

    drafts = split_text_into_chunks(normalized_text)
    if not drafts:
        asset.chunk_count = 0
        asset.sync_status = "ready"
        asset.last_indexed_at = datetime.now(timezone.utc)
        asset.last_error = None
        await asset.save(update_fields=["chunk_count", "sync_status", "last_indexed_at", "last_error", "update_time"])
        await _publish_index_progress(asset, phase="ready", started_at=started_at, progress_percent=100, expires_in_ms=4000)
        await detect_and_sync_asset_references(asset.id)
        return 0

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
    )
    created_chunks = await DBKBAssetChunk.filter(asset_id=asset.id).order_by("chunk_index").all()
    await _publish_index_progress(
        asset,
        phase="embedding",
        started_at=started_at,
        progress_percent=35,
        total_chunks=len(created_chunks),
        processed_chunks=0,
    )

    points: list[tuple[int, list[float], dict[str, object]]] = []
    processed_chunks = 0
    for batch_start in range(0, len(created_chunks), INDEX_BATCH_SIZE):
        db_batch = created_chunks[batch_start : batch_start + INDEX_BATCH_SIZE]
        draft_batch = drafts[batch_start : batch_start + INDEX_BATCH_SIZE]
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
                        asset=asset,
                        content_preview=_preview_text(draft.content),
                    ),
                )
            )
            processed_chunks += 1
        await _publish_index_progress(
            asset,
            phase="embedding",
            started_at=started_at,
            progress_percent=35 + int((processed_chunks / max(1, len(created_chunks))) * 50),
            total_chunks=len(created_chunks),
            processed_chunks=processed_chunks,
        )

    await _publish_index_progress(
        asset,
        phase="upserting",
        started_at=started_at,
        progress_percent=90,
        total_chunks=len(created_chunks),
        processed_chunks=processed_chunks,
    )
    await kb_library_qdrant_manager.batch_upsert(points)
    asset.chunk_count = len(created_chunks)
    asset.sync_status = "ready"
    asset.last_indexed_at = datetime.now(timezone.utc)
    asset.last_error = None
    await asset.save(update_fields=["chunk_count", "sync_status", "last_indexed_at", "last_error", "update_time"])
    await _publish_index_progress(
        asset,
        phase="ready",
        started_at=started_at,
        progress_percent=100,
        total_chunks=len(created_chunks),
        processed_chunks=processed_chunks,
        expires_in_ms=4000,
    )
    await detect_and_sync_asset_references(asset.id)
    return len(created_chunks)


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
                except Exception as e:
                    logger.warning(f"后台全局知识库索引任务失败: asset_id={asset_id}, error={e}")
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
