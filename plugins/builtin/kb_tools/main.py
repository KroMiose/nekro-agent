from __future__ import annotations

from collections import Counter
import json
from typing import Any, List

from nekro_agent.api.plugin import SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_kb_chunk import DBKBChunk
from nekro_agent.models.db_kb_document import DBKBDocument
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.schemas.kb import (
    KBChunkContextResponse,
    KBSourceFileResponse,
)
from nekro_agent.services.kb.document_service import (
    get_document,
    list_documents,
    read_normalized_content,
    read_source_content,
)
from nekro_agent.services.kb.search_service import search_workspace_kb
from nekro_agent.services.workspace.manager import WorkspaceService

from .plugin import kb_tools_config, plugin

logger = get_sub_logger("kb_tools")
_HIT_START = "\n<<<HIT-START>>>\n"
_HIT_END = "\n<<<HIT-END>>>\n"
_TOOL_TEXT_PREVIEW_MAX_CHARS = 1200
_TOOL_FULLTEXT_HARD_CAP = 32000
_TOOL_SEARCH_SNIPPET_MAX_CHARS = 180


async def _require_bound_workspace(_ctx: AgentCtx) -> DBWorkspace:
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        raise ValueError("当前频道未绑定工作区，无法使用知识库工具。")
    return workspace


def _document_prompt_status(document: DBKBDocument) -> str:
    if document.extract_status == "failed" or document.sync_status == "failed":
        return "failed"
    if document.extract_status != "ready":
        return document.extract_status
    return document.sync_status


def _trim_prompt_text(value: str, limit: int) -> str:
    """压缩空白后截断，保留最后一个完整词，超出时附省略号。"""
    compact = " ".join(value.strip().split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: max(0, limit - 1)]}…"


def _trim_tool_text(value: str, limit: int) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    trimmed = value[:limit]
    last_newline = trimmed.rfind("\n")
    if last_newline > limit // 2:
        trimmed = trimmed[:last_newline]
    return trimmed.rstrip(), True


def _dump_tool_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _format_document_catalog_line(document: DBKBDocument) -> str:
    parts = [
        f"[{document.id}] {_trim_prompt_text(document.title, 60)}",
        f"path={document.source_path}",
        f"format={document.format}",
        f"status={_document_prompt_status(document)}",
    ]
    if document.category:
        parts.append(f"category={_trim_prompt_text(document.category, 24)}")
    if isinstance(document.tags, list) and document.tags:
        parts.append(f"tags={','.join(_trim_prompt_text(str(tag), 16) for tag in document.tags[:4])}")
    if document.chunk_count > 0:
        parts.append(f"chunks={document.chunk_count}")
    if not document.is_enabled:
        parts.append("disabled=true")
    return "- " + " | ".join(parts)


async def _build_kb_catalog_prompt(workspace_id: int) -> str:
    documents = await list_documents(workspace_id)
    if not documents:
        return "KB catalog: empty."

    status_counter = Counter(_document_prompt_status(document) for document in documents)
    ready_documents = [document for document in documents if document.is_enabled and _document_prompt_status(document) == "ready"]
    prompt_limit = max(1, int(kb_tools_config.PROMPT_CATALOG_LIMIT))
    shown_documents = ready_documents[:prompt_limit]
    extra_ready = max(0, len(ready_documents) - len(shown_documents))

    lines = [
        (
            "KB catalog summary: "
            f"total={len(documents)}, searchable_ready={len(ready_documents)}, "
            f"pending={status_counter.get('pending', 0)}, "
            f"extracting={status_counter.get('extracting', 0)}, "
            f"indexing={status_counter.get('indexing', 0)}, "
            f"failed={status_counter.get('failed', 0)}."
        ),
    ]

    if shown_documents:
        lines.append("Searchable KB documents (metadata only, no content):")
        lines.extend(_format_document_catalog_line(document) for document in shown_documents)
        if extra_ready > 0:
            lines.append(f"- ... {extra_ready} more ready documents not shown in prompt.")
    else:
        lines.append("No ready searchable KB documents currently. If needed, check indexing status first.")

    lines.append(
        "If the user request overlaps titles, paths, categories, or tags above, search KB first instead of waiting for an explicit KB mention."
    )
    return "\n".join(lines)


def _build_document_status_payload(document: DBKBDocument) -> dict[str, Any]:
    return {
        "document_id": document.id,
        "title": document.title,
        "source_path": document.source_path,
        "format": document.format,
        "category": document.category,
        "tags": document.tags if isinstance(document.tags, list) else [],
        "summary": document.summary,
        "status": _document_prompt_status(document),
        "chunk_count": document.chunk_count,
        "file_size": int(document.file_size),
        "is_enabled": document.is_enabled,
        "last_indexed_at": document.last_indexed_at.isoformat() if document.last_indexed_at else None,
    }


def _resolve_chunk_span(normalized_content: str, chunk: DBKBChunk) -> tuple[int, int]:
    start = max(0, min(len(normalized_content), int(chunk.char_start)))
    end = max(start, min(len(normalized_content), int(chunk.char_end)))
    if start < end:
        return start, end
    return start, min(len(normalized_content), start + 1)


def _build_chunk_context_payload(
    *,
    workspace_id: int,
    document_id: int,
    title: str,
    source_path: str,
    normalized_text_path: str | None,
    chunk: DBKBChunk,
    normalized_content: str,
    window_chars: int,
    window_start: int | None = None,
) -> KBChunkContextResponse:
    chunk_start, chunk_end = _resolve_chunk_span(normalized_content, chunk)
    if window_start is None:
        excerpt_start = max(0, chunk_start - window_chars)
        excerpt_end = min(len(normalized_content), chunk_end + window_chars)
    else:
        excerpt_start = max(0, min(len(normalized_content), int(window_start)))
        excerpt_end = min(len(normalized_content), excerpt_start + window_chars)
    excerpt = normalized_content[excerpt_start:excerpt_end]
    match_text = normalized_content[chunk_start:chunk_end]
    relative_start = max(0, chunk_start - excerpt_start)
    relative_end = max(relative_start, min(len(excerpt), chunk_end - excerpt_start))
    includes_hit = relative_start < relative_end
    annotated_excerpt = (
        excerpt[:relative_start]
        + _HIT_START
        + excerpt[relative_start:relative_end]
        + _HIT_END
        + excerpt[relative_end:]
        if includes_hit else excerpt
    )
    prev_window_start = max(0, excerpt_start - window_chars) if excerpt_start > 0 else None
    next_window_start = excerpt_end if excerpt_end < len(normalized_content) else None

    return KBChunkContextResponse(
        document_id=document_id,
        chunk_id=chunk.id,
        title=title,
        source_path=source_path,
        source_workspace_path=WorkspaceService.get_kb_source_workspace_path(source_path),
        normalized_text_path=normalized_text_path,
        normalized_workspace_path=(
            WorkspaceService.get_kb_normalized_workspace_path(normalized_text_path)
            if normalized_text_path else None
        ),
        heading_path=chunk.heading_path,
        chunk_char_start=chunk_start,
        chunk_char_end=chunk_end,
        window_start=excerpt_start,
        window_size=window_chars,
        excerpt_char_start=excerpt_start,
        excerpt_char_end=excerpt_end,
        before_truncated=excerpt_start > 0,
        after_truncated=excerpt_end < len(normalized_content),
        includes_hit=includes_hit,
        prev_window_start=prev_window_start,
        next_window_start=next_window_start,
        match_text=match_text,
        annotated_excerpt=annotated_excerpt,
    )


@plugin.mount_prompt_inject_method("kb_tools_prompt")
async def kb_tools_prompt(_ctx: AgentCtx) -> str:
    try:
        workspace = await _ctx.get_bound_workspace()
        if workspace is None:
            return ""
        catalog_prompt = await _build_kb_catalog_prompt(workspace.id)
        return (
            "[Knowledge Base]\n"
            "Use KB for indexed static docs only: manuals, rules, FAQ, imported design/product/reference docs.\n"
            "Do not use KB for live repo code, implementation inspection, debugging, refactors, or git history; use CC Workspace for those.\n"
            "If the user request overlaps titles, paths, categories, or tags below, search KB proactively.\n"
            "Workflow: search first, then read hit-local chunk context, and only read fulltext if local context is still insufficient.\n"
            "When answering from KB, keep source_path for traceability.\n"
            f"{catalog_prompt}"
        )
    except Exception:
        logger.exception("构建知识库工具提示词失败")
        return ""


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "搜索工作区知识库",
    description="在当前绑定工作区中搜索知识库，返回文档 ID、文件路径、规范化全文路径和命中摘要，适合处理 FAQ、规则、手册、设计文档检索。",
)
async def search_workspace_kb_tool(
    _ctx: AgentCtx,
    query: str,
    limit: int = 0,
    max_chunks_per_document: int = 3,
    category: str = "",
) -> str:
    """Search the current workspace knowledge base.

    Args:
        query (str): Search query describing the document topic to find.
        limit (int): Maximum number of results to return. Use `0` for the plugin default.
        max_chunks_per_document (int): Maximum number of matched chunks from the same document.
        category (str): Optional category filter.

    Returns:
        str: JSON string containing grouped document hits, snippets, suggested document IDs,
        and a next_action_hint. Prefer reading hit-local context before full text.
    """
    workspace = await _require_bound_workspace(_ctx)
    resolved_limit = limit if limit > 0 else int(kb_tools_config.DEFAULT_SEARCH_LIMIT)
    result = await search_workspace_kb(
        workspace_id=workspace.id,
        query=query,
        limit=resolved_limit,
        max_chunks_per_document=max_chunks_per_document,
        category=category,
    )
    payload = {
        "query": result.query,
        "document_total": result.document_total,
        "suggested_document_ids": result.suggested_document_ids,
        "next_action_hint": (
            "先读命中 chunk 的局部上下文；不够再翻页；仍不足再读全文；结果不相关再换 query。"
        ),
        "documents": [
            {
                "document_id": item.document_id,
                "title": item.title,
                "source_path": item.source_path,
                "format": item.format,
                "document_score": item.document_score,
                "matched_chunk_count": item.matched_chunk_count,
                "category": item.category or None,
                "tags": item.tags[:3],
                "top_hit": (
                    {
                        "chunk_id": item.snippets[0].chunk_id,
                        "heading_path": item.snippets[0].heading_path,
                        "content_preview": _trim_prompt_text(item.snippets[0].content_preview, _TOOL_SEARCH_SNIPPET_MAX_CHARS),
                        "score": item.snippets[0].score,
                    }
                    if item.snippets
                    else None
                ),
            }
            for item in result.documents
        ],
    }
    return _dump_tool_payload(payload)


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "查看知识库文档详情",
    description="按文档 ID 查看知识库文档的元数据、文件路径、原文内容和规范化全文预览。",
)
async def get_workspace_kb_document_tool(
    _ctx: AgentCtx,
    document_id: int,
) -> str:
    """Get knowledge base document metadata and content preview by document ID.

    Args:
        document_id (int): Target KB document ID returned by KB search.

    Returns:
        str: JSON string containing document metadata, file paths, and content preview.
    """
    workspace = await _require_bound_workspace(_ctx)
    document = await get_document(workspace.id, document_id)
    if document is None:
        raise ValueError(f"未找到知识库文档 {document_id}")
    source_content = read_source_content(document) if document.format in {"markdown", "text", "html", "json", "yaml", "csv"} else ""
    normalized_content = read_normalized_content(document)
    source_preview, source_truncated = _trim_tool_text(source_content, _TOOL_TEXT_PREVIEW_MAX_CHARS)
    normalized_preview, normalized_truncated = _trim_tool_text(normalized_content, _TOOL_TEXT_PREVIEW_MAX_CHARS)
    payload = {
        "document": _build_document_status_payload(document),
        "source_preview": source_preview,
        "source_preview_truncated": source_truncated,
        "source_total_chars": len(source_content),
        "normalized_preview": normalized_preview,
        "normalized_preview_truncated": normalized_truncated,
        "normalized_total_chars": len(normalized_content),
        "next_action_hint": (
            "Use read_workspace_kb_chunk_context_tool first for hit-local reading; "
            "use read_workspace_kb_fulltext_tool only when a larger normalized text window is necessary."
        ),
    }
    return _dump_tool_payload(payload)


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "读取知识库全文",
    description="读取知识库文档的规范化全文，适合在搜索命中后继续阅读完整内容。",
)
async def read_workspace_kb_fulltext_tool(
    _ctx: AgentCtx,
    document_id: int,
    max_chars: int = 0,
) -> str:
    """Read the normalized full text of a KB document.

    Args:
        document_id (int): Target KB document ID.
        max_chars (int): Maximum number of characters to return. Use `0` for the plugin default.

    Returns:
        str: JSON string containing normalized full text and stable file paths.
    """
    workspace = await _require_bound_workspace(_ctx)
    document = await get_document(workspace.id, document_id)
    if document is None:
        raise ValueError(f"未找到知识库文档 {document_id}")
    config_max = int(kb_tools_config.DEFAULT_FULLTEXT_MAX_CHARS)
    resolved_max_chars = min(max_chars if max_chars > 0 else config_max, _TOOL_FULLTEXT_HARD_CAP)
    content = read_normalized_content(document)
    content_preview, truncated = _trim_tool_text(content, resolved_max_chars)
    payload = {
        "document_id": document.id,
        "title": document.title,
        "source_path": document.source_path,
        "content": content_preview,
        "returned_chars": len(content_preview),
        "total_chars": len(content),
        "truncated": truncated,
        "next_action_hint": (
            "If this window is still too large or incomplete, narrow the target by searching again "
            "or read hit-local context with read_workspace_kb_chunk_context_tool."
        ),
    }
    return _dump_tool_payload(payload)


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "读取知识库命中附近上下文",
    description="按 chunk_id 读取命中位置附近的局部上下文，并用标记圈出命中段，适合搜索命中后继续阅读附近内容。",
)
async def read_workspace_kb_chunk_context_tool(
    _ctx: AgentCtx,
    chunk_id: int,
    window_chars: int = 280,
    window_start: int = -1,
) -> str:
    """Read local context around a matched KB chunk.

    Args:
        chunk_id (int): Target chunk ID returned by KB search.
        window_chars (int): Size of the returned context window.
        window_start (int): Optional absolute start offset for paging. Use `-1` to auto-center around the hit.

    Returns:
        str: JSON string containing chunk offsets, compact local context, paging cursors,
        and an annotated excerpt where the hit chunk is wrapped by <<<HIT-START>>> / <<<HIT-END>>> markers
        when the current window overlaps the hit.
    """
    workspace = await _require_bound_workspace(_ctx)
    chunk = await DBKBChunk.get_or_none(id=chunk_id, workspace_id=workspace.id)
    if chunk is None:
        raise ValueError(f"未找到知识库 chunk {chunk_id}")

    document = await get_document(workspace.id, chunk.document_id)
    if document is None:
        raise ValueError(f"未找到知识库文档 {chunk.document_id}")

    normalized_content = read_normalized_content(document)
    if not normalized_content.strip():
        raise ValueError(f"知识库文档 {document.id} 尚无可读取的规范化全文")

    resolved_window_chars = max(80, min(int(window_chars), 1200))
    resolved_window_start = None if int(window_start) < 0 else int(window_start)
    payload = _build_chunk_context_payload(
        workspace_id=workspace.id,
        document_id=document.id,
        title=document.title,
        source_path=document.source_path,
        normalized_text_path=document.normalized_text_path,
        chunk=chunk,
        normalized_content=normalized_content,
        window_chars=resolved_window_chars,
        window_start=resolved_window_start,
    )
    return _dump_tool_payload(payload.model_dump())


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    "获取知识库源文件",
    description="将知识库源文件转成 AI 可继续发送或处理的沙盒文件路径，同时返回稳定逻辑路径。",
)
async def get_workspace_kb_source_file_tool(
    _ctx: AgentCtx,
    document_id: int,
) -> str:
    """Forward a KB source file into the agent-accessible sandbox path.

    Args:
        document_id (int): Target KB document ID.

    Returns:
        str: JSON string containing logical source path and agent-accessible sandbox file path.
    """
    workspace = await _require_bound_workspace(_ctx)
    document = await get_document(workspace.id, document_id)
    if document is None:
        raise ValueError(f"未找到知识库文档 {document_id}")

    source_file = WorkspaceService.resolve_kb_source_path(workspace.id, document.source_path)
    if not source_file.exists():
        raise ValueError(f"知识库源文件不存在: {document.source_path}")

    sandbox_file_path = await _ctx.fs.mixed_forward_file(source_file, file_name=document.file_name)
    payload = KBSourceFileResponse(
        document_id=document.id,
        title=document.title,
        source_path=document.source_path,
        source_workspace_path=WorkspaceService.get_kb_source_workspace_path(document.source_path),
        sandbox_file_path=sandbox_file_path,
    )
    return _dump_tool_payload(payload.model_dump())


@plugin.mount_collect_methods()
async def collect_kb_methods(ctx: AgentCtx) -> List:
    workspace = await ctx.get_bound_workspace()
    if workspace is None:
        return []
    return [
        search_workspace_kb_tool,
        get_workspace_kb_document_tool,
        read_workspace_kb_chunk_context_tool,
        read_workspace_kb_fulltext_tool,
        get_workspace_kb_source_file_tool,
    ]
