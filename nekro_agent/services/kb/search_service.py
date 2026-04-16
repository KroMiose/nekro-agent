from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal

from nekro_agent.models.db_kb_asset import DBKBAsset
from nekro_agent.models.db_kb_asset_binding import DBKBAssetBinding
from nekro_agent.models.db_kb_asset_chunk import DBKBAssetChunk
from nekro_agent.models.db_kb_chunk import DBKBChunk
from nekro_agent.models.db_kb_document import DBKBDocument
from nekro_agent.schemas.kb import (
    KBSearchDocument,
    KBSearchItem,
    KBSearchResponse,
    KBSearchSnippet,
)
from nekro_agent.services.kb.document_service import read_normalized_content
from nekro_agent.services.kb.library_qdrant_manager import kb_library_qdrant_manager
from nekro_agent.services.kb.library_service import read_asset_normalized_content
from nekro_agent.services.kb.qdrant_manager import kb_qdrant_manager
from nekro_agent.services.memory.embedding_service import embed_text
from nekro_agent.services.workspace.manager import WorkspaceService

PREVIEW_MAX_CHARS = 360
KEYWORD_DOC_CANDIDATE_FACTOR = 6
KEYWORD_HIT_FACTOR = 4
KEYWORD_CHUNK_SCORE_THRESHOLD = 0.22
KEYWORD_DOCUMENT_FALLBACK_THRESHOLD = 0.4
FUSED_SCORE_CAP = 1.8


_SourceKind = Literal["document", "asset"]


@dataclass
class _ScoredHit:
    source_kind: _SourceKind
    chunk: DBKBChunk | DBKBAssetChunk
    source: DBKBDocument | DBKBAsset
    heading_path: str
    content_preview: str
    score: float


@dataclass
class _DocumentBucket:
    source_kind: _SourceKind
    source: DBKBDocument | DBKBAsset
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


def _preview_text(text: str, max_chars: int = PREVIEW_MAX_CHARS) -> str:
    normalized = " ".join(text.strip().split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 1]}…"


def _payload_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key, "")
    return value.strip() if isinstance(value, str) else ""


def _source_tags(source: DBKBDocument | DBKBAsset) -> list[str]:
    return [str(tag) for tag in source.tags] if isinstance(source.tags, list) else []


def _source_matches_filters(source: DBKBDocument | DBKBAsset, *, category: str, tags: list[str] | None) -> bool:
    if category.strip() and source.category != category.strip():
        return False
    if tags:
        source_tags = set(_source_tags(source))
        if not set(tag.strip() for tag in tags if tag.strip()).issubset(source_tags):
            return False
    return True


def _read_normalized_cached(document: DBKBDocument, normalized_cache: dict[int, str]) -> str:
    normalized_content = normalized_cache.get(document.id)
    if normalized_content is None:
        normalized_content = read_normalized_content(document)
        normalized_cache[document.id] = normalized_content
    return normalized_content


def _extract_chunk_text(
    *,
    document: DBKBDocument,
    chunk: DBKBChunk,
    normalized_cache: dict[int, str],
) -> str:
    normalized_content = _read_normalized_cached(document, normalized_cache)
    if not normalized_content:
        return ""
    start = max(0, min(len(normalized_content), int(chunk.char_start)))
    end = max(start, min(len(normalized_content), int(chunk.char_end)))
    return normalized_content[start:end].strip()


def _extract_preview_from_document(
    *,
    document: DBKBDocument,
    chunk: DBKBChunk,
    normalized_cache: dict[int, str],
) -> str:
    excerpt = _extract_chunk_text(document=document, chunk=chunk, normalized_cache=normalized_cache)
    if excerpt:
        return _preview_text(excerpt)

    normalized_content = _read_normalized_cached(document, normalized_cache)
    if not normalized_content:
        return ""

    start = max(0, min(len(normalized_content), int(chunk.char_start)))
    end = max(start, min(len(normalized_content), int(chunk.char_end)))
    fallback_start = max(0, start - PREVIEW_MAX_CHARS // 2)
    fallback_end = min(len(normalized_content), max(end, start + PREVIEW_MAX_CHARS // 2))
    return _preview_text(normalized_content[fallback_start:fallback_end])


def _keyword_match_score(
    *,
    tokens: list[str],
    heading_path: str,
    content_preview: str,
    source: DBKBDocument | DBKBAsset,
) -> float:
    if not tokens:
        return 0.0

    score = 0.0
    haystacks = {
        "title": source.title.lower(),
        "path": source.source_path.lower(),
        "heading": heading_path.lower(),
        "preview": content_preview.lower(),
        "category": source.category.lower(),
        "summary": source.summary.lower(),
        "tags": " ".join(tag.lower() for tag in _source_tags(source)),
    }

    for token in tokens:
        if token in haystacks["title"]:
            score += 0.18
        if token in haystacks["path"]:
            score += 0.08
        if token in haystacks["heading"]:
            score += 0.08
        if token in haystacks["preview"]:
            score += 0.06
        if token in haystacks["summary"]:
            score += 0.04
        if token in haystacks["category"]:
            score += 0.03
        if token in haystacks["tags"]:
            score += 0.03

    return min(score, 0.5)


def _keyword_document_score(*, query: str, tokens: list[str], source: DBKBDocument | DBKBAsset) -> float:
    lowered_query = query.lower().strip()
    title = source.title.lower()
    path = source.source_path.lower()
    summary = source.summary.lower()
    category = source.category.lower()
    tags = " ".join(tag.lower() for tag in _source_tags(source))

    score = 0.0
    if lowered_query:
        if lowered_query in title:
            score += 0.55
        if lowered_query in path:
            score += 0.3
        if lowered_query in summary:
            score += 0.18
        if lowered_query in category:
            score += 0.1
        if lowered_query in tags:
            score += 0.1

    matched_tokens = 0
    for token in tokens:
        token_matched = False
        if token in title:
            score += 0.14
            token_matched = True
        if token in path:
            score += 0.08
            token_matched = True
        if token in summary:
            score += 0.05
            token_matched = True
        if token in category:
            score += 0.03
            token_matched = True
        if token in tags:
            score += 0.04
            token_matched = True
        if token_matched:
            matched_tokens += 1

    if tokens:
        score += (matched_tokens / len(tokens)) * 0.18
    return min(score, 1.2)


def _keyword_chunk_score(
    *,
    query: str,
    tokens: list[str],
    heading_path: str,
    chunk_text: str,
    source: DBKBDocument | DBKBAsset,
) -> float:
    lowered_query = query.lower().strip()
    chunk_lower = chunk_text.lower()
    heading_lower = heading_path.lower()
    score = 0.0

    if lowered_query:
        if lowered_query in chunk_lower:
            score += 0.55
        if lowered_query in heading_lower:
            score += 0.18

    matched_tokens = 0
    for token in tokens:
        token_matched = False
        if token in chunk_lower:
            score += 0.08
            token_matched = True
        if token in heading_lower:
            score += 0.06
            token_matched = True
        if token_matched:
            matched_tokens += 1

    if tokens:
        score += (matched_tokens / len(tokens)) * 0.16
    score += min(_keyword_document_score(query=query, tokens=tokens, source=source) * 0.25, 0.25)
    return min(score, 1.35)


def _apply_metadata_bonus(
    *,
    query: str,
    tokens: list[str],
    heading_path: str,
    content_preview: str,
    source: DBKBDocument | DBKBAsset,
    base_score: float,
) -> float:
    lowered_query = query.lower()
    score = base_score
    if lowered_query and lowered_query in source.title.lower():
        score += 0.1
    if lowered_query and lowered_query in source.source_path.lower():
        score += 0.06
    score += _keyword_match_score(
        tokens=tokens,
        heading_path=heading_path,
        content_preview=content_preview,
        source=source,
    )
    return score


def _merge_hits(vector_hits: list[_ScoredHit], keyword_hits: list[_ScoredHit]) -> list[_ScoredHit]:
    merged: dict[tuple[_SourceKind, int], _ScoredHit] = {}

    def _merge_one(hit: _ScoredHit) -> None:
        key = (hit.source_kind, hit.chunk.id)
        existing = merged.get(key)
        if existing is None:
            merged[key] = hit
            return

        combined_score = max(existing.score, hit.score) + min(existing.score, hit.score) * 0.2
        merged[key] = _ScoredHit(
            source_kind=existing.source_kind,
            chunk=existing.chunk,
            source=existing.source,
            heading_path=existing.heading_path or hit.heading_path,
            content_preview=existing.content_preview if len(existing.content_preview) >= len(hit.content_preview) else hit.content_preview,
            score=min(combined_score, FUSED_SCORE_CAP),
        )

    for hit in vector_hits:
        _merge_one(hit)
    for hit in keyword_hits:
        _merge_one(hit)
    return list(merged.values())


async def _collect_keyword_hits(
    *,
    documents: list[DBKBDocument],
    workspace_id: int,
    query: str,
    tokens: list[str],
    limit: int,
    max_chunks_per_document: int,
    normalized_cache: dict[int, str],
) -> list[_ScoredHit]:
    if not query.strip():
        return []

    scored_documents = [
        (document, _keyword_document_score(query=query, tokens=tokens, source=document))
        for document in documents
    ]
    scored_documents = [(document, score) for document, score in scored_documents if score > 0]
    if not scored_documents:
        return []

    scored_documents.sort(key=lambda item: item[1], reverse=True)
    candidate_limit = max(limit * KEYWORD_DOC_CANDIDATE_FACTOR, 12)
    candidate_documents = scored_documents[:candidate_limit]
    candidate_doc_ids = [document.id for document, _score in candidate_documents]
    chunks = (
        await DBKBChunk.filter(workspace_id=workspace_id, document_id__in=candidate_doc_ids)
        .order_by("document_id", "chunk_index")
        .all()
    )
    chunk_groups: defaultdict[int, list[DBKBChunk]] = defaultdict(list)
    for chunk in chunks:
        chunk_groups[chunk.document_id].append(chunk)

    hits: list[_ScoredHit] = []
    chunk_limit = max(limit * max_chunks_per_document * KEYWORD_HIT_FACTOR, 12)
    for document, document_score in candidate_documents:
        document_chunks = chunk_groups.get(document.id, [])
        if not document_chunks:
            continue

        document_hits: list[_ScoredHit] = []
        for chunk in document_chunks:
            chunk_text = _extract_chunk_text(document=document, chunk=chunk, normalized_cache=normalized_cache)
            if not chunk_text:
                continue

            chunk_score = _keyword_chunk_score(
                query=query,
                tokens=tokens,
                heading_path=chunk.heading_path,
                chunk_text=chunk_text,
                source=document,
            )
            if chunk_score < KEYWORD_CHUNK_SCORE_THRESHOLD:
                continue

            document_hits.append(
                _ScoredHit(
                    source_kind="document",
                    chunk=chunk,
                    source=document,
                    heading_path=chunk.heading_path,
                    content_preview=_preview_text(chunk_text),
                    score=min(chunk_score, FUSED_SCORE_CAP),
                )
            )

        if not document_hits and document_score >= KEYWORD_DOCUMENT_FALLBACK_THRESHOLD:
            fallback_chunk = document_chunks[0]
            document_hits.append(
                _ScoredHit(
                    source_kind="document",
                    chunk=fallback_chunk,
                    source=document,
                    heading_path=fallback_chunk.heading_path,
                    content_preview=_extract_preview_from_document(
                        document=document,
                        chunk=fallback_chunk,
                        normalized_cache=normalized_cache,
                    ),
                    score=min(document_score * 0.85, FUSED_SCORE_CAP),
                )
            )

        hits.extend(sorted(document_hits, key=lambda item: item.score, reverse=True)[: max_chunks_per_document * 2])

    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[:chunk_limit]


def _read_asset_normalized_cached(asset: DBKBAsset, normalized_cache: dict[int, str]) -> str:
    normalized_content = normalized_cache.get(asset.id)
    if normalized_content is None:
        normalized_content = read_asset_normalized_content(asset)
        normalized_cache[asset.id] = normalized_content
    return normalized_content


def _extract_chunk_text_from_asset(
    *,
    asset: DBKBAsset,
    chunk: DBKBAssetChunk,
    normalized_cache: dict[int, str],
) -> str:
    normalized_content = _read_asset_normalized_cached(asset, normalized_cache)
    if not normalized_content:
        return ""
    start = max(0, min(len(normalized_content), int(chunk.char_start)))
    end = max(start, min(len(normalized_content), int(chunk.char_end)))
    return normalized_content[start:end].strip()


def _extract_preview_from_asset(
    *,
    asset: DBKBAsset,
    chunk: DBKBAssetChunk,
    normalized_cache: dict[int, str],
) -> str:
    excerpt = _extract_chunk_text_from_asset(asset=asset, chunk=chunk, normalized_cache=normalized_cache)
    if excerpt:
        return _preview_text(excerpt)

    normalized_content = _read_asset_normalized_cached(asset, normalized_cache)
    if not normalized_content:
        return ""

    start = max(0, min(len(normalized_content), int(chunk.char_start)))
    end = max(start, min(len(normalized_content), int(chunk.char_end)))
    fallback_start = max(0, start - PREVIEW_MAX_CHARS // 2)
    fallback_end = min(len(normalized_content), max(end, start + PREVIEW_MAX_CHARS // 2))
    return _preview_text(normalized_content[fallback_start:fallback_end])


async def _collect_keyword_asset_hits(
    *,
    assets: list[DBKBAsset],
    query: str,
    tokens: list[str],
    limit: int,
    max_chunks_per_document: int,
    normalized_cache: dict[int, str],
) -> list[_ScoredHit]:
    if not query.strip():
        return []

    scored_assets = [
        (asset, _keyword_document_score(query=query, tokens=tokens, source=asset))
        for asset in assets
    ]
    scored_assets = [(asset, score) for asset, score in scored_assets if score > 0]
    if not scored_assets:
        return []

    scored_assets.sort(key=lambda item: item[1], reverse=True)
    candidate_limit = max(limit * KEYWORD_DOC_CANDIDATE_FACTOR, 12)
    candidate_assets = scored_assets[:candidate_limit]
    candidate_asset_ids = [asset.id for asset, _score in candidate_assets]
    chunks = (
        await DBKBAssetChunk.filter(asset_id__in=candidate_asset_ids)
        .order_by("asset_id", "chunk_index")
        .all()
    )
    chunk_groups: defaultdict[int, list[DBKBAssetChunk]] = defaultdict(list)
    for chunk in chunks:
        chunk_groups[chunk.asset_id].append(chunk)

    hits: list[_ScoredHit] = []
    chunk_limit = max(limit * max_chunks_per_document * KEYWORD_HIT_FACTOR, 12)
    for asset, asset_score in candidate_assets:
        asset_chunks = chunk_groups.get(asset.id, [])
        if not asset_chunks:
            continue

        asset_hits: list[_ScoredHit] = []
        for chunk in asset_chunks:
            chunk_text = _extract_chunk_text_from_asset(asset=asset, chunk=chunk, normalized_cache=normalized_cache)
            if not chunk_text:
                continue

            chunk_score = _keyword_chunk_score(
                query=query,
                tokens=tokens,
                heading_path=chunk.heading_path,
                chunk_text=chunk_text,
                source=asset,
            )
            if chunk_score < KEYWORD_CHUNK_SCORE_THRESHOLD:
                continue

            asset_hits.append(
                _ScoredHit(
                    source_kind="asset",
                    chunk=chunk,
                    source=asset,
                    heading_path=chunk.heading_path,
                    content_preview=_preview_text(chunk_text),
                    score=min(chunk_score, FUSED_SCORE_CAP),
                )
            )

        if not asset_hits and asset_score >= KEYWORD_DOCUMENT_FALLBACK_THRESHOLD:
            fallback_chunk = asset_chunks[0]
            asset_hits.append(
                _ScoredHit(
                    source_kind="asset",
                    chunk=fallback_chunk,
                    source=asset,
                    heading_path=fallback_chunk.heading_path,
                    content_preview=_extract_preview_from_asset(
                        asset=asset,
                        chunk=fallback_chunk,
                        normalized_cache=normalized_cache,
                    ),
                    score=min(asset_score * 0.85, FUSED_SCORE_CAP),
                )
            )

        hits.extend(sorted(asset_hits, key=lambda item: item.score, reverse=True)[: max_chunks_per_document * 2])

    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[:chunk_limit]


def _build_item(hit: _ScoredHit) -> KBSearchItem:
    source = hit.source
    source_workspace_path = (
        WorkspaceService.get_kb_source_workspace_path(source.source_path) if hit.source_kind == "document" else ""
    )
    normalized_workspace_path = (
        WorkspaceService.get_kb_normalized_workspace_path(source.normalized_text_path)
        if hit.source_kind == "document" and source.normalized_text_path
        else None
    )
    return KBSearchItem(
        document_id=source.id,
        source_kind=hit.source_kind,
        chunk_id=hit.chunk.id,
        title=source.title,
        file_name=source.file_name,
        format=source.format,  # type: ignore[arg-type]
        source_path=source.source_path,
        source_workspace_path=source_workspace_path,
        normalized_text_path=source.normalized_text_path,
        normalized_workspace_path=normalized_workspace_path,
        heading_path=hit.heading_path,
        category=source.category,
        tags=_source_tags(source),
        content_preview=hit.content_preview,
        score=round(hit.score, 4),
    )


def _build_document(bucket: _DocumentBucket, max_chunks_per_document: int) -> KBSearchDocument:
    source = bucket.source
    hits = sorted(bucket.hits, key=lambda item: item.score, reverse=True)[:max_chunks_per_document]
    headings: list[str] = []
    snippets: list[KBSearchSnippet] = []
    for hit in hits:
        if hit.heading_path and hit.heading_path not in headings:
            headings.append(hit.heading_path)
        snippets.append(
            KBSearchSnippet(
                chunk_id=hit.chunk.id,
                heading_path=hit.heading_path,
                content_preview=hit.content_preview,
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
        document_id=source.id,
        source_kind=bucket.source_kind,
        title=source.title,
        file_name=source.file_name,
        format=source.format,  # type: ignore[arg-type]
        source_path=source.source_path,
        source_workspace_path=(
            WorkspaceService.get_kb_source_workspace_path(source.source_path)
            if bucket.source_kind == "document"
            else ""
        ),
        normalized_text_path=source.normalized_text_path,
        normalized_workspace_path=(
            WorkspaceService.get_kb_normalized_workspace_path(source.normalized_text_path)
            if bucket.source_kind == "document" and source.normalized_text_path
            else None
        ),
        category=source.category,
        tags=_source_tags(source),
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
    documents = await DBKBDocument.filter(workspace_id=workspace_id, is_enabled=True).all()
    documents = [
        document
        for document in documents
        if _source_matches_filters(document, category=category, tags=tags)
    ]
    bound_asset_ids = sorted(
        {
            int(asset_id)
            for asset_id in await DBKBAssetBinding.filter(workspace_id=workspace_id).values_list("asset_id", flat=True)
        }
    )
    assets: list[DBKBAsset] = []
    if bound_asset_ids:
        assets = await DBKBAsset.filter(id__in=bound_asset_ids, is_enabled=True).all()
        assets = [
            asset
            for asset in assets
            if _source_matches_filters(asset, category=category, tags=tags)
        ]

    if not documents and not assets:
        return KBSearchResponse(
            workspace_id=workspace_id,
            query=query,
            total=0,
            items=[],
            document_total=0,
            documents=[],
            suggested_document_ids=[],
            next_action_hint="当前未命中文档，可尝试缩短 query、改用明确关键词，或换一个更具体的文档主题再搜索。",
        )

    query_vector = await embed_text(query)
    vector_hits: list[_ScoredHit] = []
    keyword_hits: list[_ScoredHit] = []

    if documents:
        document_map = {document.id: document for document in documents}
        grouped_results = await kb_qdrant_manager.search_grouped(
            query_vector=query_vector,
            workspace_id=workspace_id,
            limit=max(limit * 3, limit),
            group_size=max(max_chunks_per_document * 3, 4),
            category=category,
            tags=tags,
            score_threshold=0.48 if tokens else 0.42,
        )

        raw_results = [hit for group in grouped_results for hit in group["hits"]]
        chunk_ids = [int(item["id"]) for item in raw_results]
        chunks = await DBKBChunk.filter(id__in=chunk_ids, workspace_id=workspace_id).all()
        chunk_map = {chunk.id: chunk for chunk in chunks}
        normalized_cache: dict[int, str] = {}

        for result in raw_results:
            chunk_id = int(result["id"])
            chunk = chunk_map.get(chunk_id)
            if chunk is None:
                continue

            payload = result["payload"] if isinstance(result["payload"], dict) else {}
            payload_document_id = payload.get("document_id")
            document_id = int(payload_document_id) if isinstance(payload_document_id, int) else chunk.document_id
            document = document_map.get(document_id)
            if document is None:
                continue

            heading_path = _payload_text(payload, "heading_path") or chunk.heading_path
            content_preview = _payload_text(payload, "content_preview") or _extract_preview_from_document(
                document=document,
                chunk=chunk,
                normalized_cache=normalized_cache,
            )
            score = _apply_metadata_bonus(
                query=query,
                tokens=tokens,
                heading_path=heading_path,
                content_preview=content_preview,
                source=document,
                base_score=float(result["score"]),
            )
            vector_hits.append(
                _ScoredHit(
                    source_kind="document",
                    chunk=chunk,
                    source=document,
                    heading_path=heading_path,
                    content_preview=content_preview,
                    score=min(score, FUSED_SCORE_CAP),
                )
            )

        keyword_hits.extend(
            await _collect_keyword_hits(
                documents=documents,
                workspace_id=workspace_id,
                query=query,
                tokens=tokens,
                limit=limit,
                max_chunks_per_document=max_chunks_per_document,
                normalized_cache=normalized_cache,
            )
        )

    if assets:
        asset_ids = [asset.id for asset in assets]
        asset_map = {asset.id: asset for asset in assets}
        grouped_asset_results = await kb_library_qdrant_manager.search_grouped(
            query_vector=query_vector,
            asset_ids=asset_ids,
            limit=max(limit * 3, limit),
            group_size=max(max_chunks_per_document * 3, 4),
            category=category,
            tags=tags,
            score_threshold=0.48 if tokens else 0.42,
        )

        raw_asset_results = [hit for group in grouped_asset_results for hit in group["hits"]]
        asset_chunk_ids = [int(item["id"]) for item in raw_asset_results]
        asset_chunks = await DBKBAssetChunk.filter(id__in=asset_chunk_ids).all()
        asset_chunk_map = {chunk.id: chunk for chunk in asset_chunks}
        asset_normalized_cache: dict[int, str] = {}

        for result in raw_asset_results:
            chunk_id = int(result["id"])
            chunk = asset_chunk_map.get(chunk_id)
            if chunk is None:
                continue

            payload = result["payload"] if isinstance(result["payload"], dict) else {}
            payload_asset_id = payload.get("asset_id")
            asset_id = int(payload_asset_id) if isinstance(payload_asset_id, int) else chunk.asset_id
            asset = asset_map.get(asset_id)
            if asset is None:
                continue

            heading_path = _payload_text(payload, "heading_path") or chunk.heading_path
            content_preview = _payload_text(payload, "content_preview") or _extract_preview_from_asset(
                asset=asset,
                chunk=chunk,
                normalized_cache=asset_normalized_cache,
            )
            score = _apply_metadata_bonus(
                query=query,
                tokens=tokens,
                heading_path=heading_path,
                content_preview=content_preview,
                source=asset,
                base_score=float(result["score"]),
            )
            vector_hits.append(
                _ScoredHit(
                    source_kind="asset",
                    chunk=chunk,
                    source=asset,
                    heading_path=heading_path,
                    content_preview=content_preview,
                    score=min(score, FUSED_SCORE_CAP),
                )
            )

        keyword_hits.extend(
            await _collect_keyword_asset_hits(
                assets=assets,
                query=query,
                tokens=tokens,
                limit=limit,
                max_chunks_per_document=max_chunks_per_document,
                normalized_cache=asset_normalized_cache,
            )
        )

    scored_hits = _merge_hits(vector_hits, keyword_hits)
    scored_hits.sort(key=lambda item: item.score, reverse=True)

    buckets: dict[tuple[_SourceKind, int], _DocumentBucket] = {}
    for hit in scored_hits:
        bucket_key = (hit.source_kind, hit.source.id)
        bucket = buckets.get(bucket_key)
        if bucket is None:
            buckets[bucket_key] = _DocumentBucket(source_kind=hit.source_kind, source=hit.source, hits=[hit])
        else:
            bucket.hits.append(hit)

    sorted_buckets = sorted(
        buckets.values(),
        key=lambda bucket: max((hit.score for hit in bucket.hits), default=0.0),
        reverse=True,
    )

    document_hits = [
        _build_document(bucket, max_chunks_per_document=max_chunks_per_document)
        for bucket in sorted_buckets[:limit]
    ]
    allowed_entry_keys = {(item.source_kind, item.document_id) for item in document_hits}

    per_document_counter: defaultdict[tuple[_SourceKind, int], int] = defaultdict(int)
    flat_items: list[KBSearchItem] = []
    for hit in scored_hits:
        entry_key = (hit.source_kind, hit.source.id)
        if entry_key not in allowed_entry_keys:
            continue
        if per_document_counter[entry_key] >= max_chunks_per_document:
            continue
        flat_items.append(_build_item(hit))
        per_document_counter[entry_key] += 1
        if len(flat_items) >= limit * max_chunks_per_document:
            break

    suggested_document_ids = [
        item.document_id
        for item in document_hits
        if item.source_kind == "document"
    ][: min(3, len(document_hits))]
    has_asset_hits = any(item.source_kind == "asset" for item in document_hits)
    next_action_hint = (
        (
            "优先阅读命中的条目详情与局部预览；"
            "若命中 source_kind=document，可继续用 chunk 上下文工具读取附近内容；"
            "若命中 source_kind=asset，请直接查看该全局知识条目的详情或全文；"
            "如果当前结果明显不相关，再改写 query 重新搜索。"
            if has_asset_hits
            else (
                "优先对命中的 chunk_id 调用 read_workspace_kb_chunk_context_tool 读取命中附近上下文；"
                "如果第一段局部上下文仍不足，可继续使用返回的 next_window_start 或 prev_window_start 翻页；"
                "只有局部上下文仍不足时，再阅读 suggested_document_ids 中前 1 到 2 篇文档的全文；"
                "如果当前结果明显不相关，再改写 query 重新搜索。"
            )
        )
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
