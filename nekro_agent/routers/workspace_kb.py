from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from tortoise.exceptions import IntegrityError

from nekro_agent.models.db_kb_document import DBKBDocument
from nekro_agent.models.db_user import DBUser
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.schemas.errors import ConflictError, NotFoundError, ValidationError
from nekro_agent.schemas.kb import (
    KBActionResponse,
    KBCreateTextDocumentBody,
    KBDocumentDetailResponse,
    KBDocumentListResponse,
    KBFullTextResponse,
    KBReindexResponse,
    KBSearchRequest,
    KBSearchResponse,
    KBSourceFileResponse,
    KBTreeNode,
    KBTreeResponse,
    KBUpdateDocumentBody,
)
from nekro_agent.services.kb.document_service import (
    create_file_document,
    create_text_document,
    document_to_list_item,
    get_document,
    list_documents,
    normalize_tags,
    read_normalized_content,
    read_source_content,
    update_document_metadata,
)
from nekro_agent.services.kb.index_service import (
    delete_document_files,
    delete_document_index,
    ensure_kb_collection,
    rebuild_workspace_documents,
    schedule_rebuild_document,
)
from nekro_agent.services.kb.search_service import search_workspace_kb
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.services.workspace.manager import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspace Knowledge Base"])

ALLOWED_KB_EXTENSIONS = {".md", ".txt", ".html", ".htm", ".json", ".yaml", ".yml", ".csv", ".pdf", ".docx"}


async def _get_workspace_or_404(workspace_id: int) -> DBWorkspace:
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    return workspace


async def _get_document_or_404(workspace_id: int, document_id: int) -> DBKBDocument:
    document = await get_document(workspace_id, document_id)
    if document is None:
        raise NotFoundError(resource=f"知识库文档 {document_id}")
    return document


def _parse_tags_text(raw_tags: str) -> list[str]:
    if not raw_tags.strip():
        return []
    return normalize_tags([item for item in raw_tags.split(",")])


def _build_tree_nodes(paths: list[tuple[int, str]]) -> list[KBTreeNode]:
    root: dict[str, dict] = {}

    for document_id, raw_path in paths:
        parts = [part for part in raw_path.split("/") if part]
        current = root
        rel_parts: list[str] = []
        for index, part in enumerate(parts):
            rel_parts.append(part)
            is_last = index == len(parts) - 1
            current.setdefault(
                part,
                {
                    "name": part,
                    "path": "/".join(rel_parts),
                    "type": "file" if is_last else "dir",
                    "document_id": document_id if is_last else None,
                    "children": {},
                },
            )
            current = current[part]["children"]

    def _convert(tree: dict[str, dict]) -> list[KBTreeNode]:
        nodes: list[KBTreeNode] = []
        for key in sorted(tree.keys()):
            value = tree[key]
            children = _convert(value["children"]) if value["children"] else None
            nodes.append(
                KBTreeNode(
                    name=value["name"],
                    path=value["path"],
                    type=value["type"],
                    document_id=value["document_id"],
                    children=children,
                )
            )
        return nodes

    return _convert(root)


@router.get("/{workspace_id}/kb/documents", summary="获取工作区知识库文档列表", response_model=KBDocumentListResponse)
@require_role(Role.Admin)
async def list_workspace_kb_documents(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBDocumentListResponse:
    await _get_workspace_or_404(workspace_id)
    documents = await list_documents(workspace_id)
    items = [document_to_list_item(document) for document in documents]
    return KBDocumentListResponse(total=len(items), items=items)


@router.get("/{workspace_id}/kb/tree", summary="获取工作区知识库目录树", response_model=KBTreeResponse)
@require_role(Role.Admin)
async def get_workspace_kb_tree(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBTreeResponse:
    await _get_workspace_or_404(workspace_id)
    documents = await list_documents(workspace_id)
    return KBTreeResponse(nodes=_build_tree_nodes([(document.id, document.source_path) for document in documents]))


@router.get(
    "/{workspace_id}/kb/documents/{document_id}", summary="获取知识库文档详情", response_model=KBDocumentDetailResponse
)
@require_role(Role.Admin)
async def get_workspace_kb_document(
    workspace_id: int,
    document_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBDocumentDetailResponse:
    document = await _get_document_or_404(workspace_id, document_id)
    source_content = (
        read_source_content(document)
        if document.format in {"markdown", "text", "html", "json", "yaml", "csv"}
        else None
    )
    normalized_content = read_normalized_content(document) or None
    return KBDocumentDetailResponse(
        document=document_to_list_item(document),
        source_content=source_content,
        normalized_content=normalized_content,
    )


@router.post("/{workspace_id}/kb/documents", summary="创建文本类知识库文档", response_model=KBDocumentDetailResponse)
@require_role(Role.Admin)
async def create_workspace_kb_document(
    workspace_id: int,
    body: KBCreateTextDocumentBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBDocumentDetailResponse:
    await _get_workspace_or_404(workspace_id)
    if body.format not in {"markdown", "text"}:
        raise ValidationError(reason="仅支持创建 markdown 或 text 类型的文本知识")
    await ensure_kb_collection()
    try:
        document = await create_text_document(
            workspace_id=workspace_id,
            title=body.title,
            content=body.content,
            source_path=body.source_path,
            file_name=body.file_name,
            format=body.format,
            category=body.category,
            tags=body.tags,
            summary=body.summary,
            is_enabled=body.is_enabled,
        )
    except IntegrityError as e:
        raise ConflictError(resource=f"知识库路径 '{body.source_path or body.file_name}'") from e
    except ValueError as e:
        raise ValidationError(reason=str(e)) from e

    refreshed = await _get_document_or_404(workspace_id, document.id)
    await schedule_rebuild_document(refreshed)
    return KBDocumentDetailResponse(
        document=document_to_list_item(refreshed),
        source_content=read_source_content(refreshed),
        normalized_content=read_normalized_content(refreshed) or None,
    )


@router.post("/{workspace_id}/kb/files", summary="上传多格式知识库文件", response_model=KBDocumentDetailResponse)
@require_role(Role.Admin)
async def upload_workspace_kb_file(
    workspace_id: int,
    file: UploadFile = File(...),
    title: str = Form(default=""),
    source_path: str = Form(default=""),
    category: str = Form(default=""),
    tags: str = Form(default=""),
    summary: str = Form(default=""),
    is_enabled: bool = Form(default=True),
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBDocumentDetailResponse:
    await _get_workspace_or_404(workspace_id)
    file_name = file.filename or ""
    if Path(file_name).suffix.lower() not in ALLOWED_KB_EXTENSIONS:
        raise ValidationError(reason=f"暂不支持的知识库文件类型: {file_name or 'unknown'}")
    await ensure_kb_collection()
    try:
        document = await create_file_document(
            workspace_id=workspace_id,
            upload_file=file,
            source_path=source_path,
            title=title,
            category=category,
            tags=_parse_tags_text(tags),
            summary=summary,
            is_enabled=is_enabled,
        )
    except IntegrityError as e:
        raise ConflictError(resource=f"知识库路径 '{source_path or file_name}'") from e
    except ValueError as e:
        raise ValidationError(reason=str(e)) from e

    refreshed = await _get_document_or_404(workspace_id, document.id)
    await schedule_rebuild_document(refreshed)
    return KBDocumentDetailResponse(
        document=document_to_list_item(refreshed),
        source_content=read_source_content(refreshed)
        if refreshed.format in {"markdown", "text", "html", "json", "yaml", "csv"}
        else None,
        normalized_content=read_normalized_content(refreshed) or None,
    )


@router.put(
    "/{workspace_id}/kb/documents/{document_id}", summary="更新知识库文档", response_model=KBDocumentDetailResponse
)
@require_role(Role.Admin)
async def update_workspace_kb_document(
    workspace_id: int,
    document_id: int,
    body: KBUpdateDocumentBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBDocumentDetailResponse:
    document = await _get_document_or_404(workspace_id, document_id)
    try:
        updated = await update_document_metadata(
            document,
            title=body.title,
            category=body.category,
            tags=body.tags,
            summary=body.summary,
            is_enabled=body.is_enabled,
            source_path=body.source_path,
            content=body.content,
        )
    except IntegrityError as e:
        raise ConflictError(resource=f"知识库路径 '{body.source_path}'") from e
    except ValueError as e:
        raise ValidationError(reason=str(e)) from e

    if body.content is not None or body.source_path is not None:
        await schedule_rebuild_document(updated)
    elif body.is_enabled is not None:
        await schedule_rebuild_document(updated)

    refreshed = await _get_document_or_404(workspace_id, document_id)
    return KBDocumentDetailResponse(
        document=document_to_list_item(refreshed),
        source_content=read_source_content(refreshed)
        if refreshed.format in {"markdown", "text", "html", "json", "yaml", "csv"}
        else None,
        normalized_content=read_normalized_content(refreshed) or None,
    )


@router.delete("/{workspace_id}/kb/documents/{document_id}", summary="删除知识库文档", response_model=KBActionResponse)
@require_role(Role.Admin)
async def delete_workspace_kb_document(
    workspace_id: int,
    document_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBActionResponse:
    document = await _get_document_or_404(workspace_id, document_id)
    await delete_document_index(document)
    await delete_document_files(document)
    await document.delete()
    return KBActionResponse(ok=True)


@router.get("/{workspace_id}/kb/documents/{document_id}/raw", summary="下载知识库原始文件")
@require_role(Role.Admin)
async def get_workspace_kb_raw_file(
    workspace_id: int,
    document_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
):
    document = await _get_document_or_404(workspace_id, document_id)
    source_file = WorkspaceService.resolve_kb_source_path(workspace_id, document.source_path)
    if not source_file.exists():
        raise NotFoundError(resource=f"知识库源文件 {document.source_path}")
    return FileResponse(source_file, media_type=document.mime_type, filename=document.file_name)


@router.get(
    "/{workspace_id}/kb/documents/{document_id}/fulltext",
    summary="获取知识库规范化全文",
    response_model=KBFullTextResponse,
)
@require_role(Role.Admin)
async def get_workspace_kb_fulltext(
    workspace_id: int,
    document_id: int,
    max_chars: int = Query(default=20000, ge=200, le=200000),
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBFullTextResponse:
    document = await _get_document_or_404(workspace_id, document_id)
    content = read_normalized_content(document)
    truncated = len(content) > max_chars
    if truncated:
        content = content[:max_chars]
    return KBFullTextResponse(
        document_id=document.id,
        title=document.title,
        source_path=document.source_path,
        source_workspace_path=WorkspaceService.get_kb_source_workspace_path(document.source_path),
        normalized_text_path=document.normalized_text_path,
        normalized_workspace_path=(
            WorkspaceService.get_kb_normalized_workspace_path(document.normalized_text_path)
            if document.normalized_text_path
            else None
        ),
        content=content,
        truncated=truncated,
    )


@router.post(
    "/{workspace_id}/kb/documents/{document_id}/reindex",
    summary="重建单个知识库文档索引",
    response_model=KBReindexResponse,
)
@require_role(Role.Admin)
async def reindex_workspace_kb_document(
    workspace_id: int,
    document_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBReindexResponse:
    await ensure_kb_collection()
    document = await _get_document_or_404(workspace_id, document_id)
    await schedule_rebuild_document(document)
    return KBReindexResponse(ok=True, total=1, success=0, failed=0)


@router.post("/{workspace_id}/kb/reindex", summary="重建工作区知识库索引", response_model=KBReindexResponse)
@require_role(Role.Admin)
async def reindex_workspace_kb(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBReindexResponse:
    await _get_workspace_or_404(workspace_id)
    await ensure_kb_collection()
    success, failed = await rebuild_workspace_documents(workspace_id)
    return KBReindexResponse(ok=failed == 0, total=success + failed, success=success, failed=failed)


@router.post("/{workspace_id}/kb/search", summary="搜索工作区知识库", response_model=KBSearchResponse)
@require_role(Role.Admin)
async def search_workspace_kb_route(
    workspace_id: int,
    body: KBSearchRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBSearchResponse:
    await _get_workspace_or_404(workspace_id)
    return await search_workspace_kb(
        workspace_id=workspace_id,
        query=body.query,
        limit=body.limit,
        max_chunks_per_document=body.max_chunks_per_document,
        category=body.category,
        tags=body.tags,
    )


@router.get(
    "/{workspace_id}/kb/documents/{document_id}/source-file",
    summary="获取源文件路径信息",
    response_model=KBSourceFileResponse,
)
@require_role(Role.Admin)
async def get_workspace_kb_source_file_info(
    workspace_id: int,
    document_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBSourceFileResponse:
    document = await _get_document_or_404(workspace_id, document_id)
    return KBSourceFileResponse(
        document_id=document.id,
        title=document.title,
        source_path=document.source_path,
        source_workspace_path=WorkspaceService.get_kb_source_workspace_path(document.source_path),
        sandbox_file_path=None,
    )
