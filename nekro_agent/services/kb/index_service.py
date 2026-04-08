from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_kb_chunk import DBKBChunk
from nekro_agent.models.db_kb_document import DBKBDocument
from nekro_agent.services.kb.chunker import split_text_into_chunks
from nekro_agent.services.kb.extractors import extract_source_file
from nekro_agent.services.kb.qdrant_manager import kb_qdrant_manager
from nekro_agent.services.memory.embedding_service import embed_batch, get_memory_embedding_dimension
from nekro_agent.services.workspace.manager import WorkspaceService

logger = get_sub_logger("kb.index")

PREVIEW_MAX_CHARS = 360


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _preview_text(text: str, max_chars: int = PREVIEW_MAX_CHARS) -> str:
    normalized = " ".join(text.strip().split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 1]}…"


async def ensure_kb_collection() -> bool:
    return await kb_qdrant_manager.ensure_collection(get_memory_embedding_dimension())


async def index_document(document: DBKBDocument) -> int:
    WorkspaceService.ensure_kb_dirs(document.workspace_id)
    document.extract_status = "extracting"
    document.sync_status = "pending"
    document.last_error = None
    await document.save(update_fields=["extract_status", "sync_status", "last_error", "update_time"])

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
        return 0

    created_chunks: list[DBKBChunk] = []
    for index, draft in enumerate(drafts):
        created_chunks.append(
            await DBKBChunk.create(
                workspace_id=document.workspace_id,
                document_id=document.id,
                chunk_index=index,
                heading_path=draft.heading_path,
                content=draft.content,
                content_preview=_preview_text(draft.content),
                char_start=draft.char_start,
                char_end=draft.char_end,
                token_count=_estimate_tokens(draft.content),
            )
        )

    embeddings = await embed_batch([chunk.content for chunk in created_chunks])
    points: list[tuple[int, list[float], dict[str, object]]] = []
    for chunk, embedding in zip(created_chunks, embeddings, strict=False):
        if embedding is None:
            continue
        chunk.embedding_ref = str(chunk.id)
        await chunk.save(update_fields=["embedding_ref", "update_time"])
        points.append((chunk.id, embedding, chunk.to_qdrant_payload(document=document)))

    await kb_qdrant_manager.batch_upsert(points)
    document.chunk_count = len(created_chunks)
    document.sync_status = "ready"
    document.last_indexed_at = datetime.now(timezone.utc)
    document.last_error = None
    await document.save(update_fields=["chunk_count", "sync_status", "last_indexed_at", "last_error", "update_time"])
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
        raise


async def rebuild_workspace_documents(workspace_id: int) -> tuple[int, int]:
    documents = await DBKBDocument.filter(workspace_id=workspace_id).all()
    success = 0
    failed = 0
    for document in documents:
        try:
            await rebuild_document(document)
            success += 1
        except Exception:
            failed += 1
    return success, failed


async def delete_document_files(document: DBKBDocument) -> None:
    source_file = WorkspaceService.resolve_kb_source_path(document.workspace_id, document.source_path)
    if source_file.exists():
        source_file.unlink()
    if document.normalized_text_path:
        normalized_file = WorkspaceService.resolve_kb_normalized_path(document.workspace_id, document.normalized_text_path)
        if normalized_file.exists():
            normalized_file.unlink()


async def delete_document_index(document: DBKBDocument) -> None:
    chunks = await DBKBChunk.filter(document_id=document.id).all()
    if chunks:
        await kb_qdrant_manager.delete_chunk_points([chunk.id for chunk in chunks])
        await DBKBChunk.filter(document_id=document.id).delete()
