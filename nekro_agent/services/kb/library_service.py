from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_kb_asset import DBKBAsset
from nekro_agent.models.db_kb_asset_binding import DBKBAssetBinding
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.schemas.kb import (
    KBAssetBoundWorkspace,
    KBAssetListItem,
)
from nekro_agent.services.kb.document_service import (
    build_default_file_name,
    compute_sha256,
    detect_format_and_mime,
    normalize_tags,
    safe_source_path,
)

_KB_LIBRARY_ROOT = Path(OsEnv.DATA_DIR) / "kb_library"
_KB_LIBRARY_FILES_ROOT = _KB_LIBRARY_ROOT / "files"
_KB_LIBRARY_NORMALIZED_ROOT = _KB_LIBRARY_ROOT / ".normalized"

TEXT_LIBRARY_FORMATS = {"markdown", "text", "html", "json", "yaml", "csv", "xlsx"}


def ensure_kb_library_dirs() -> None:
    _KB_LIBRARY_FILES_ROOT.mkdir(parents=True, exist_ok=True)
    _KB_LIBRARY_NORMALIZED_ROOT.mkdir(parents=True, exist_ok=True)


def resolve_kb_library_source_path(rel_path: str) -> Path:
    try:
        target = (_KB_LIBRARY_FILES_ROOT / rel_path).resolve()
        target.relative_to(_KB_LIBRARY_FILES_ROOT.resolve())
    except ValueError as e:
        raise ValueError(f"非法 KB 全局源文件路径: {rel_path}") from e
    return target


def resolve_kb_library_normalized_path(rel_path: str) -> Path:
    try:
        target = (_KB_LIBRARY_NORMALIZED_ROOT / rel_path).resolve()
        target.relative_to(_KB_LIBRARY_NORMALIZED_ROOT.resolve())
    except ValueError as e:
        raise ValueError(f"非法 KB 全局规范化全文路径: {rel_path}") from e
    return target


async def list_assets() -> list[DBKBAsset]:
    return await DBKBAsset.all().order_by("source_path")


async def get_asset(asset_id: int) -> DBKBAsset | None:
    return await DBKBAsset.get_or_none(id=asset_id)


async def list_asset_bindings(asset_id: int) -> list[DBKBAssetBinding]:
    return await DBKBAssetBinding.filter(asset_id=asset_id).order_by("workspace_id").all()


async def list_asset_bound_workspaces(asset_id: int) -> list[KBAssetBoundWorkspace]:
    bindings = await list_asset_bindings(asset_id)
    if not bindings:
        return []
    workspace_ids = [binding.workspace_id for binding in bindings]
    workspaces = await DBWorkspace.filter(id__in=workspace_ids).order_by("id").all()
    workspace_map = {workspace.id: workspace for workspace in workspaces}
    return [
        KBAssetBoundWorkspace(
            workspace_id=binding.workspace_id,
            workspace_name=workspace_map[binding.workspace_id].name,
            workspace_status=workspace_map[binding.workspace_id].status,
        )
        for binding in bindings
        if binding.workspace_id in workspace_map
    ]


async def asset_to_list_item(asset: DBKBAsset) -> KBAssetListItem:
    bound_workspaces = await list_asset_bound_workspaces(asset.id)
    return KBAssetListItem(
        id=asset.id,
        title=asset.title,
        category=asset.category,
        tags=asset.tags if isinstance(asset.tags, list) else [],
        summary=asset.summary,
        file_name=asset.file_name,
        file_ext=asset.file_ext,
        mime_type=asset.mime_type,
        format=asset.format,  # type: ignore[arg-type]
        source_path=asset.source_path,
        is_enabled=asset.is_enabled,
        extract_status=asset.extract_status,  # type: ignore[arg-type]
        sync_status=asset.sync_status,  # type: ignore[arg-type]
        chunk_count=asset.chunk_count,
        file_size=int(asset.file_size),
        last_error=asset.last_error,
        last_indexed_at=asset.last_indexed_at.isoformat() if asset.last_indexed_at else None,
        binding_count=len(bound_workspaces),
        bound_workspaces=bound_workspaces,
        update_time=asset.update_time.isoformat(),
        create_time=asset.create_time.isoformat(),
    )


def read_asset_source_content(asset: DBKBAsset) -> str:
    source_path = resolve_kb_library_source_path(asset.source_path)
    if not source_path.exists():
        return ""
    return source_path.read_text(encoding="utf-8", errors="replace")


def read_asset_normalized_content(asset: DBKBAsset) -> str:
    if not asset.normalized_text_path:
        return ""
    normalized_path = resolve_kb_library_normalized_path(asset.normalized_text_path)
    if not normalized_path.exists():
        return ""
    return normalized_path.read_text(encoding="utf-8", errors="replace")


async def create_asset_from_upload(
    *,
    upload_file: UploadFile,
    source_path: str,
    title: str,
    category: str,
    tags: list[str],
    summary: str,
    is_enabled: bool,
    source_type: str = "upload",
) -> tuple[DBKBAsset, bool]:
    ensure_kb_library_dirs()
    original_name = upload_file.filename or "kb-asset-upload.txt"
    final_source_path = safe_source_path(source_path or original_name)
    content = await upload_file.read()
    content_hash = compute_sha256(content)
    existing = await DBKBAsset.get_or_none(content_hash=content_hash)
    if existing is not None:
        return existing, True

    target = resolve_kb_library_source_path(final_source_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError(f"知识库资产路径已存在: {final_source_path}")
    target.write_bytes(content)
    detected_format, suffix, mime_type = detect_format_and_mime(Path(final_source_path).name)
    asset = await DBKBAsset.create(
        source_path=final_source_path,
        normalized_text_path="",
        file_name=Path(final_source_path).name,
        file_ext=suffix,
        mime_type=mime_type,
        title=(title or Path(final_source_path).stem).strip(),
        category=category.strip(),
        tags=normalize_tags(tags),
        summary=summary.strip(),
        source_type=source_type,
        format=detected_format,
        is_enabled=is_enabled,
        extract_status="pending",
        sync_status="pending",
        content_hash=content_hash,
        normalized_text_hash="",
        chunk_count=0,
        file_size=len(content),
    )
    return asset, False


async def create_text_asset(
    *,
    title: str,
    content: str,
    source_path: str,
    file_name: str,
    format: str,
    category: str,
    tags: list[str],
    summary: str,
    is_enabled: bool,
    source_type: str = "manual",
) -> tuple[DBKBAsset, bool]:
    ensure_kb_library_dirs()
    final_file_name = file_name or build_default_file_name(title, ".md" if format == "markdown" else ".txt")
    final_source_path = safe_source_path(source_path or final_file_name)
    encoded = content.encode("utf-8")
    content_hash = compute_sha256(encoded)
    existing = await DBKBAsset.get_or_none(content_hash=content_hash)
    if existing is not None:
        return existing, True

    target = resolve_kb_library_source_path(final_source_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError(f"知识库资产路径已存在: {final_source_path}")
    target.write_bytes(encoded)
    detected_format, suffix, mime_type = detect_format_and_mime(Path(final_source_path).name)
    asset = await DBKBAsset.create(
        source_path=final_source_path,
        normalized_text_path="",
        file_name=Path(final_source_path).name,
        file_ext=suffix,
        mime_type=mime_type,
        title=title.strip(),
        category=category.strip(),
        tags=normalize_tags(tags),
        summary=summary.strip(),
        source_type=source_type,
        format=detected_format,
        is_enabled=is_enabled,
        extract_status="pending",
        sync_status="pending",
        content_hash=content_hash,
        normalized_text_hash="",
        chunk_count=0,
        file_size=len(encoded),
    )
    return asset, False


async def update_asset_metadata(
    asset: DBKBAsset,
    *,
    title: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    is_enabled: bool | None = None,
) -> DBKBAsset:
    update_fields: list[str] = []
    if title is not None:
        asset.title = title.strip()
        update_fields.append("title")
    if category is not None:
        asset.category = category.strip()
        update_fields.append("category")
    if tags is not None:
        asset.tags = normalize_tags(tags)
        update_fields.append("tags")
    if summary is not None:
        asset.summary = summary.strip()
        update_fields.append("summary")
    if is_enabled is not None:
        asset.is_enabled = is_enabled
        update_fields.append("is_enabled")
    if update_fields:
        await asset.save(update_fields=[*sorted(set(update_fields)), "update_time"])
    return asset


async def update_asset_bindings(asset_id: int, workspace_ids: list[int]) -> list[KBAssetBoundWorkspace]:
    normalized_ids = sorted({int(workspace_id) for workspace_id in workspace_ids})
    existing_bindings = await DBKBAssetBinding.filter(asset_id=asset_id).all()
    existing_ids = {binding.workspace_id for binding in existing_bindings}
    target_ids = set(normalized_ids)

    delete_ids = existing_ids - target_ids
    create_ids = target_ids - existing_ids

    if delete_ids:
        await DBKBAssetBinding.filter(asset_id=asset_id, workspace_id__in=list(delete_ids)).delete()
    for workspace_id in sorted(create_ids):
        await DBKBAssetBinding.create(asset_id=asset_id, workspace_id=workspace_id)

    return await list_asset_bound_workspaces(asset_id)


async def bind_asset_workspace(asset_id: int, workspace_id: int) -> list[KBAssetBoundWorkspace]:
    await DBKBAssetBinding.get_or_create(asset_id=asset_id, workspace_id=workspace_id)
    return await list_asset_bound_workspaces(asset_id)


async def unbind_asset_workspace(asset_id: int, workspace_id: int) -> list[KBAssetBoundWorkspace]:
    await DBKBAssetBinding.filter(asset_id=asset_id, workspace_id=workspace_id).delete()
    return await list_asset_bound_workspaces(asset_id)
