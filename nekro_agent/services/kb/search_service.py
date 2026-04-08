from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from nekro_agent.models.db_kb_chunk import DBKBChunk
from nekro_agent.models.db_kb_document import DBKBDocument
from nekro_agent.schemas.kb import (
    KBSearchDocument,
    KBSearchItem,
    KBSearchResponse,
    KBSearchSnippet,
)
from nekro_agent.services.kb.qdrant_manager import kb_qdrant_manager
from nekro_agent.services.memory.embedding_service import embed_text
from nekro_agent.services.workspace.manager import WorkspaceService


@dataclass
class _ScoredHit:
    chunk: DBKBChunk
    document: DBKBDocument
    score: float


@dataclass
class _DocumentBucket:
    document: DBKBDocument
    hits: list[_ScoredHit] = field(default_factory=list)


def _tokenize_query(query: str) -> list[str]:
    lowered = query.lower().strip()
    tokens = re.findall(r"[a-z0-9_./-]+|[\u4e00-\u9fff]{2,}", lowered)
    seen: set[str] = set()
    result: list[str] = []
    for token in tokens:
        normalized = token.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _keyword_match_score(*, tokens: list[str], chunk: DBKBChunk, document: DBKBDocument) -> float:
    if not tokens:
        return 0.0

    score = 0.0
    haystacks = {
        "title": document.title.lower(),
        "path": document.source_path.lower(),
        "heading": chunk.heading_path.lower(),
        "preview": chunk.content_preview.lower(),
        "category": document.category.lower(),
        "tags": " ".join(str(tag).lower() for tag in (document.tags if isinstance(document.tags, list) else [])),
    }

    for token in tokens:
        if token in haystacks["title"]:
            score += 0.18
        if token in haystacks["path"]:
            score += 0.08
        if token in haystacks["heading"]:
            score += 0.08
        if token in haystacks["preview"]:
            score += 0.05
        if token in haystacks["category"]:
            score += 0.03
        if token in haystacks["tags"]:
            score += 0.03

    return min(score, 0.45)


def _apply_metadata_bonus(
    *,
    query: str,
    tokens: list[str],
    chunk: DBKBChunk,
    document: DBKBDocument,
    base_score: float,
) -> float:
    lowered_query = query.lower()
    score = base_score
    if lowered_query and lowered_query in document.title.lower():
        score += 0.1
    if lowered_query and lowered_query in document.source_path.lower():
        score += 0.06
    score += _keyword_match_score(tokens=tokens, chunk=chunk, document=document)
    return score


def _build_item(hit: _ScoredHit) -> KBSearchItem:
    document = hit.document
    chunk = hit.chunk
    return KBSearchItem(
        document_id=document.id,
        chunk_id=chunk.id,
        title=document.title,
        file_name=document.file_name,
        format=document.format,  # type: ignore[arg-type]
        source_path=document.source_path,
        source_workspace_path=WorkspaceService.get_kb_source_workspace_path(document.source_path),
        normalized_text_path=document.normalized_text_path,
        normalized_workspace_path=(
            WorkspaceService.get_kb_normalized_workspace_path(document.normalized_text_path)
            if document.normalized_text_path else None
        ),
        heading_path=chunk.heading_path,
        category=document.category,
        tags=document.tags if isinstance(document.tags, list) else [],
        content_preview=chunk.content_preview,
        score=round(hit.score, 4),
    )


def _build_document(bucket: _DocumentBucket, max_chunks_per_document: int) -> KBSearchDocument:
    document = bucket.document
    hits = sorted(bucket.hits, key=lambda item: item.score, reverse=True)[:max_chunks_per_document]
    headings: list[str] = []
    snippets: list[KBSearchSnippet] = []
    for hit in hits:
        if hit.chunk.heading_path and hit.chunk.heading_path not in headings:
            headings.append(hit.chunk.heading_path)
        snippets.append(
            KBSearchSnippet(
                chunk_id=hit.chunk.id,
                heading_path=hit.chunk.heading_path,
                content_preview=hit.chunk.content_preview,
                score=round(hit.score, 4),
            )
        )

    excerpt_parts: list[str] = []
    for snippet in snippets[:2]:
        if snippet.heading_path:
            excerpt_parts.append(f"[{snippet.heading_path}] {snippet.content_preview}")
        else:
            excerpt_parts.append(snippet.content_preview)

    return KBSearchDocument(
        document_id=document.id,
        title=document.title,
        file_name=document.file_name,
        format=document.format,  # type: ignore[arg-type]
        source_path=document.source_path,
        source_workspace_path=WorkspaceService.get_kb_source_workspace_path(document.source_path),
        normalized_text_path=document.normalized_text_path,
        normalized_workspace_path=(
            WorkspaceService.get_kb_normalized_workspace_path(document.normalized_text_path)
            if document.normalized_text_path else None
        ),
        category=document.category,
        tags=document.tags if isinstance(document.tags, list) else [],
        document_score=round(max((hit.score for hit in hits), default=0.0), 4),
        matched_chunk_count=len(bucket.hits),
        headings=headings,
        best_match_excerpt="\n".join(excerpt_parts),
        snippets=snippets,
    )


async def search_workspace_kb(
    *,
    workspace_id: int,
    query: str,
    limit: int = 5,
    max_chunks_per_document: int = 2,
    category: str = "",
    tags: list[str] | None = None,
) -> KBSearchResponse:
    tokens = _tokenize_query(query)
    query_vector = await embed_text(query)
    raw_results = await kb_qdrant_manager.search(
        query_vector=query_vector,
        workspace_id=workspace_id,
        limit=max(limit * max_chunks_per_document * 5, limit),
        category=category,
        tags=tags,
        score_threshold=0.48 if tokens else 0.42,
    )

    chunk_ids = [int(item["id"]) for item in raw_results]
    chunks = await DBKBChunk.filter(id__in=chunk_ids, workspace_id=workspace_id).all()
    chunk_map = {chunk.id: chunk for chunk in chunks}
    document_ids = sorted({chunk.document_id for chunk in chunks})
    documents = await DBKBDocument.filter(id__in=document_ids, workspace_id=workspace_id, is_enabled=True).all()
    document_map = {document.id: document for document in documents}

    scored_hits: list[_ScoredHit] = []
    for result in raw_results:
        chunk_id = int(result["id"])
        chunk = chunk_map.get(chunk_id)
        if chunk is None:
            continue
        document = document_map.get(chunk.document_id)
        if document is None:
            continue
        if category.strip() and document.category != category.strip():
            continue
        if tags:
            document_tags = set(document.tags if isinstance(document.tags, list) else [])
            if not set(tags).issubset(document_tags):
                continue

        score = _apply_metadata_bonus(
            query=query,
            tokens=tokens,
            chunk=chunk,
            document=document,
            base_score=float(result["score"]),
        )
        scored_hits.append(_ScoredHit(chunk=chunk, document=document, score=score))

    scored_hits.sort(key=lambda item: item.score, reverse=True)

    buckets: dict[int, _DocumentBucket] = {}
    for hit in scored_hits:
        bucket = buckets.get(hit.document.id)
        if bucket is None:
            buckets[hit.document.id] = _DocumentBucket(document=hit.document, hits=[hit])
        else:
            bucket.hits.append(hit)

    sorted_buckets = sorted(
        buckets.values(),
        key=lambda bucket: max((hit.score for hit in bucket.hits), default=0.0),
        reverse=True,
    )

    document_hits = [_build_document(bucket, max_chunks_per_document=max_chunks_per_document) for bucket in sorted_buckets[:limit]]
    allowed_document_ids = {item.document_id for item in document_hits}

    per_document_counter: defaultdict[int, int] = defaultdict(int)
    flat_items: list[KBSearchItem] = []
    for hit in scored_hits:
        if hit.document.id not in allowed_document_ids:
            continue
        if per_document_counter[hit.document.id] >= max_chunks_per_document:
            continue
        flat_items.append(_build_item(hit))
        per_document_counter[hit.document.id] += 1
        if len(flat_items) >= limit * max_chunks_per_document:
            break

    suggested_document_ids = [item.document_id for item in document_hits[: min(3, len(document_hits))]]
    next_action_hint = (
        "优先阅读 suggested_document_ids 中前 1 到 2 篇文档的全文，不要对相同问题反复搜索；"
        "如果当前结果明显不相关，再改写 query 重新搜索。"
        if document_hits
        else "当前未命中文档，可尝试缩短 query、改用明确关键词，或换一个更具体的文档主题再搜索。"
    )

    return KBSearchResponse(
        workspace_id=workspace_id,
        query=query,
        total=len(flat_items),
        items=flat_items,
        document_total=len(document_hits),
        documents=document_hits,
        suggested_document_ids=suggested_document_ids,
        next_action_hint=next_action_hint,
    )
