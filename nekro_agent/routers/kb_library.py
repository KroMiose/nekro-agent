from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from tortoise.exceptions import IntegrityError

from nekro_agent.models.db_kb_asset import DBKBAsset
from nekro_agent.models.db_user import DBUser
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.schemas.errors import ConflictError, NotFoundError, ValidationError
from nekro_agent.schemas.kb import (
    KBActionResponse,
    KBAssetBindingsResponse,
    KBAssetBindingsUpdateBody,
    KBAssetDetailResponse,
    KBAssetListResponse,
    KBAssetUploadResponse,
    KBCreateTextDocumentBody,
    KBFullTextResponse,
)
from nekro_agent.services.kb.library_index_service import (
    delete_asset_files,
    delete_asset_index,
    ensure_kb_library_collection,
    schedule_rebuild_asset,
)
from nekro_agent.services.kb.library_service import (
    TEXT_LIBRARY_FORMATS,
    asset_to_list_item,
    bind_asset_workspace,
    create_asset_from_upload,
    create_text_asset,
    get_asset,
    list_asset_bound_workspaces,
    list_assets,
    read_asset_normalized_content,
    read_asset_source_content,
    resolve_kb_library_source_path,
    unbind_asset_workspace,
    update_asset_bindings,
)
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/kb-library", tags=["Knowledge Base Library"])

ALLOWED_KB_LIBRARY_EXTENSIONS = {
    ".md",
    ".txt",
    ".html",
    ".htm",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".xlsx",
    ".pdf",
    ".docx",
}


async def _get_asset_or_404(asset_id: int) -> DBKBAsset:
    asset = await get_asset(asset_id)
    if asset is None:
        raise NotFoundError(resource=f"全局知识库文件 {asset_id}")
    return asset


async def _ensure_workspace_exists(workspace_id: int) -> None:
    if not await DBWorkspace.filter(id=workspace_id).exists():
        raise ValidationError(reason="存在无效的工作区 ID，无法更新绑定")


@router.get("/assets", summary="获取全局知识库文件列表", response_model=KBAssetListResponse)
@require_role(Role.Admin)
async def list_kb_library_assets(
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBAssetListResponse:
    assets = await list_assets()
    items = [await asset_to_list_item(asset) for asset in assets]
    return KBAssetListResponse(total=len(items), items=items)


@router.get("/assets/{asset_id}", summary="获取全局知识库文件详情", response_model=KBAssetDetailResponse)
@require_role(Role.Admin)
async def get_kb_library_asset(
    asset_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBAssetDetailResponse:
    asset = await _get_asset_or_404(asset_id)
    source_content = read_asset_source_content(asset) if asset.format in TEXT_LIBRARY_FORMATS else None
    normalized_content = read_asset_normalized_content(asset) or None
    return KBAssetDetailResponse(
        asset=await asset_to_list_item(asset),
        source_content=source_content,
        normalized_content=normalized_content,
    )


@router.post("/assets", summary="创建文本类全局知识库文件", response_model=KBAssetUploadResponse)
@require_role(Role.Admin)
async def create_kb_library_asset(
    body: KBCreateTextDocumentBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBAssetUploadResponse:
    if body.format not in {"markdown", "text"}:
        raise ValidationError(reason="仅支持创建 markdown 或 text 类型的文本知识")
    await ensure_kb_library_collection()
    try:
        asset, reused_existing = await create_text_asset(
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
        raise ConflictError(resource=f"全局知识库路径 '{body.source_path or body.file_name}'") from e
    except ValueError as e:
        raise ValidationError(reason=str(e)) from e

    refreshed = await _get_asset_or_404(asset.id)
    if not reused_existing:
        await schedule_rebuild_asset(refreshed)
    return KBAssetUploadResponse(asset=await asset_to_list_item(refreshed), reused_existing=reused_existing)


@router.post("/assets/files", summary="上传全局知识库文件", response_model=KBAssetUploadResponse)
@require_role(Role.Admin)
async def upload_kb_library_asset(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    source_path: str = Form(default=""),
    category: str = Form(default=""),
    tags: str = Form(default=""),
    summary: str = Form(default=""),
    is_enabled: bool = Form(default=True),
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBAssetUploadResponse:
    file_name = file.filename or ""
    if Path(file_name).suffix.lower() not in ALLOWED_KB_LIBRARY_EXTENSIONS:
        raise ValidationError(reason=f"暂不支持的全局知识库文件类型: {file_name or 'unknown'}")
    await ensure_kb_library_collection()
    parsed_tags = [item.strip() for item in tags.split(",") if item.strip()]
    try:
        asset, reused_existing = await create_asset_from_upload(
            upload_file=file,
            source_path=source_path,
            title=title,
            category=category,
            tags=parsed_tags,
            summary=summary,
            is_enabled=is_enabled,
        )
    except IntegrityError as e:
        raise ConflictError(resource=f"全局知识库路径 '{source_path or file_name}'") from e
    except ValueError as e:
        raise ValidationError(reason=str(e)) from e

    refreshed = await _get_asset_or_404(asset.id)
    if not reused_existing:
        await schedule_rebuild_asset(refreshed)
    return KBAssetUploadResponse(asset=await asset_to_list_item(refreshed), reused_existing=reused_existing)


@router.delete("/assets/{asset_id}", summary="删除全局知识库文件", response_model=KBActionResponse)
@require_role(Role.Admin)
async def delete_kb_library_asset(
    asset_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBActionResponse:
    asset = await _get_asset_or_404(asset_id)
    bound_workspaces = await list_asset_bound_workspaces(asset.id)
    if bound_workspaces:
        raise ConflictError(resource=f"全局知识库文件 {asset.id} 仍被 {len(bound_workspaces)} 个工作区绑定")
    await delete_asset_index(asset)
    await delete_asset_files(asset)
    await asset.delete()
    return KBActionResponse(ok=True)


@router.post("/assets/{asset_id}/reindex", summary="重建全局知识库文件索引", response_model=KBActionResponse)
@require_role(Role.Admin)
async def reindex_kb_library_asset(
    asset_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBActionResponse:
    await ensure_kb_library_collection()
    asset = await _get_asset_or_404(asset_id)
    await schedule_rebuild_asset(asset)
    return KBActionResponse(ok=True)


@router.get("/assets/{asset_id}/raw", summary="下载全局知识库原始文件")
@require_role(Role.Admin)
async def get_kb_library_raw_file(
    asset_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
):
    asset = await _get_asset_or_404(asset_id)
    source_file = resolve_kb_library_source_path(asset.source_path)
    if not source_file.exists():
        raise NotFoundError(resource=f"全局知识库源文件 {asset.source_path}")
    return FileResponse(source_file, media_type=asset.mime_type, filename=asset.file_name)


@router.get("/assets/{asset_id}/fulltext", summary="获取全局知识库规范化全文", response_model=KBFullTextResponse)
@require_role(Role.Admin)
async def get_kb_library_fulltext(
    asset_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBFullTextResponse:
    asset = await _get_asset_or_404(asset_id)
    content = read_asset_normalized_content(asset)
    return KBFullTextResponse(
        document_id=asset.id,
        title=asset.title,
        source_path=asset.source_path,
        source_workspace_path="",
        normalized_text_path=asset.normalized_text_path,
        normalized_workspace_path=None,
        content=content,
        truncated=False,
    )


@router.get("/assets/{asset_id}/bindings", summary="获取全局知识库文件绑定", response_model=KBAssetBindingsResponse)
@require_role(Role.Admin)
async def get_kb_library_asset_bindings(
    asset_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBAssetBindingsResponse:
    await _get_asset_or_404(asset_id)
    items = await list_asset_bound_workspaces(asset_id)
    return KBAssetBindingsResponse(asset_id=asset_id, binding_count=len(items), items=items)


@router.put("/assets/{asset_id}/bindings", summary="更新全局知识库文件绑定", response_model=KBAssetBindingsResponse)
@require_role(Role.Admin)
async def update_kb_library_asset_bindings(
    asset_id: int,
    body: KBAssetBindingsUpdateBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBAssetBindingsResponse:
    await _get_asset_or_404(asset_id)
    normalized_ids = sorted({int(workspace_id) for workspace_id in body.workspace_ids})
    if normalized_ids:
        existing_count = await DBWorkspace.filter(id__in=normalized_ids).count()
        if existing_count != len(normalized_ids):
            raise ValidationError(reason="存在无效的工作区 ID，无法更新绑定")
    items = await update_asset_bindings(asset_id, normalized_ids)
    return KBAssetBindingsResponse(asset_id=asset_id, binding_count=len(items), items=items)


@router.put(
    "/assets/{asset_id}/bindings/{workspace_id}",
    summary="为工作区绑定全局知识库文件",
    response_model=KBAssetBindingsResponse,
)
@require_role(Role.Admin)
async def bind_kb_library_asset_workspace(
    asset_id: int,
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBAssetBindingsResponse:
    await _get_asset_or_404(asset_id)
    await _ensure_workspace_exists(workspace_id)
    items = await bind_asset_workspace(asset_id, workspace_id)
    return KBAssetBindingsResponse(asset_id=asset_id, binding_count=len(items), items=items)


@router.delete(
    "/assets/{asset_id}/bindings/{workspace_id}",
    summary="解绑工作区与全局知识库文件",
    response_model=KBAssetBindingsResponse,
)
@require_role(Role.Admin)
async def unbind_kb_library_asset_workspace(
    asset_id: int,
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> KBAssetBindingsResponse:
    await _get_asset_or_404(asset_id)
    await _ensure_workspace_exists(workspace_id)
    items = await unbind_asset_workspace(asset_id, workspace_id)
    return KBAssetBindingsResponse(asset_id=asset_id, binding_count=len(items), items=items)
