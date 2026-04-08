from __future__ import annotations

from typing import List

from nekro_agent.api.plugin import SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_kb_chunk import DBKBChunk
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.schemas.kb import (
    KBChunkContextResponse,
    KBDocumentDetailResponse,
    KBFullTextResponse,
    KBSourceFileResponse,
)
from nekro_agent.services.kb.document_service import document_to_list_item, get_document, read_normalized_content, read_source_content
from nekro_agent.services.kb.search_service import search_workspace_kb
from nekro_agent.services.workspace.manager import WorkspaceService

from .plugin import kb_tools_config, plugin

logger = get_sub_logger("kb_tools")
_HIT_START = "\n<<<HIT-START>>>\n"
_HIT_END = "\n<<<HIT-END>>>\n"


async def _require_bound_workspace(_ctx: AgentCtx) -> DBWorkspace:
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        raise ValueError("当前频道未绑定工作区，无法使用知识库工具。")
    return workspace


def _resolve_chunk_span(normalized_content: str, chunk: DBKBChunk) -> tuple[int, int]:
    start = max(0, min(len(normalized_content), int(chunk.char_start)))
    end = max(start, min(len(normalized_content), int(chunk.char_end)))
    if start < end:
        return start, end

    if chunk.content:
        found_at = normalized_content.find(chunk.content)
        if found_at != -1:
            return found_at, found_at + len(chunk.content)

    return start, min(len(normalized_content), start + len(chunk.content))


def _build_chunk_context_payload(
    *,
    workspace_id: int,
    document_id: int,
    title: str,
    source_path: str,
    normalized_text_path: str | None,
    chunk: DBKBChunk,
    normalized_content: str,
    around_chars: int,
) -> KBChunkContextResponse:
    chunk_start, chunk_end = _resolve_chunk_span(normalized_content, chunk)
    excerpt_start = max(0, chunk_start - around_chars)
    excerpt_end = min(len(normalized_content), chunk_end + around_chars)
    excerpt = normalized_content[excerpt_start:excerpt_end]
    match_text = normalized_content[chunk_start:chunk_end] or chunk.content
    relative_start = max(0, chunk_start - excerpt_start)
    relative_end = max(relative_start, min(len(excerpt), chunk_end - excerpt_start))
    annotated_excerpt = (
        excerpt[:relative_start]
        + _HIT_START
        + excerpt[relative_start:relative_end]
        + _HIT_END
        + excerpt[relative_end:]
    )

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
        excerpt_char_start=excerpt_start,
        excerpt_char_end=excerpt_end,
        before_truncated=excerpt_start > 0,
        after_truncated=excerpt_end < len(normalized_content),
        match_text=match_text,
        annotated_excerpt=annotated_excerpt,
    )


@plugin.mount_prompt_inject_method("kb_tools_prompt")
async def kb_tools_prompt(_ctx: AgentCtx) -> str:
    try:
        workspace = await _ctx.get_bound_workspace()
        if workspace is None:
            return ""
        return (
            "[Knowledge Base Tools]\n"
            "Use KB tools only for static knowledge that has already been indexed into the workspace knowledge base, such as manuals, rules, FAQ, imported design docs, imported product docs, and imported reference materials.\n"
            "- Do NOT use KB tools for repository source code, implementation details in the live codebase, debugging, refactors, local file inspection outside the indexed KB, git history, or tasks that require editing files. Those belong to CC Workspace.\n"
            "- If the user is asking how Nekro-Agent itself is implemented, how a plugin works in the repo, or asks you to inspect/change code, prefer CC Workspace first.\n"
            "- After one KB search, prefer reading the matched local context around a hit chunk instead of jumping straight to the beginning of the full text.\n"
            "- Use `read_workspace_kb_chunk_context_tool(chunk_id=...)` first when search returns useful chunk_ids; only read full text if local context is still insufficient.\n"
            "- Only search again if the current results are clearly irrelevant.\n"
            "- When you cite a KB answer, keep the source_path for traceability."
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
        and a next_action_hint. Prefer reading full text from suggested_document_ids after one search.
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
    return result.model_dump_json(indent=2)


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
    payload = KBDocumentDetailResponse(
        document=document_to_list_item(document),
        source_content=read_source_content(document) if document.format in {"markdown", "text", "html", "json", "yaml", "csv"} else None,
        normalized_content=read_normalized_content(document) or None,
    )
    return payload.model_dump_json(indent=2)


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
    resolved_max_chars = max_chars if max_chars > 0 else int(kb_tools_config.DEFAULT_FULLTEXT_MAX_CHARS)
    content = read_normalized_content(document)
    truncated = len(content) > resolved_max_chars
    if truncated:
        content = content[:resolved_max_chars]
    payload = KBFullTextResponse(
        document_id=document.id,
        title=document.title,
        source_path=document.source_path,
        source_workspace_path=WorkspaceService.get_kb_source_workspace_path(document.source_path),
        normalized_text_path=document.normalized_text_path,
        normalized_workspace_path=(
            WorkspaceService.get_kb_normalized_workspace_path(document.normalized_text_path)
            if document.normalized_text_path else None
        ),
        content=content,
        truncated=truncated,
    )
    return payload.model_dump_json(indent=2)


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "读取知识库命中附近上下文",
    description="按 chunk_id 读取命中位置附近的局部上下文，并用标记圈出命中段，适合搜索命中后继续阅读附近内容。",
)
async def read_workspace_kb_chunk_context_tool(
    _ctx: AgentCtx,
    chunk_id: int,
    around_chars: int = 280,
) -> str:
    """Read local context around a matched KB chunk.

    Args:
        chunk_id (int): Target chunk ID returned by KB search.
        around_chars (int): Number of characters to include before and after the matched chunk.

    Returns:
        str: JSON string containing chunk offsets, compact local context, and an annotated excerpt
        where the hit chunk is wrapped by <<<HIT-START>>> / <<<HIT-END>>> markers.
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

    resolved_around_chars = max(80, min(int(around_chars), 1200))
    payload = _build_chunk_context_payload(
        workspace_id=workspace.id,
        document_id=document.id,
        title=document.title,
        source_path=document.source_path,
        normalized_text_path=document.normalized_text_path,
        chunk=chunk,
        normalized_content=normalized_content,
        around_chars=resolved_around_chars,
    )
    return payload.model_dump_json(indent=2)


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
    return payload.model_dump_json(indent=2)


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
