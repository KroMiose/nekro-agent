from __future__ import annotations

import hashlib
import mimetypes
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from fastapi import UploadFile

from nekro_agent.models.db_kb_document import DBKBDocument
from nekro_agent.models.db_kb_document_reference import DBKBDocumentReference
from nekro_agent.schemas.kb import KBDocumentListItem, KBDocumentReferences, KBReferenceItem
from nekro_agent.services.workspace.manager import WorkspaceService

TEXT_FORMATS = {"markdown", "text", "html", "json", "yaml", "csv"}


def normalize_tags(tags: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_tag in tags:
        tag = str(raw_tag).strip()
        if not tag or tag in seen:
            continue
        normalized.append(tag)
        seen.add(tag)
    return normalized


def safe_source_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/").lstrip("/")
    normalized = re.sub(r"/{2,}", "/", normalized)
    if not normalized:
        raise ValueError("知识库路径不能为空")
    if any(part in {"..", "."} for part in normalized.split("/")):
        raise ValueError(f"非法知识库路径: {path}")
    return normalized


def build_default_file_name(title: str, file_ext: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "-", title).strip().strip(".")
    if not cleaned:
        cleaned = f"kb-{int(datetime.now().timestamp())}"
    return f"{cleaned}{file_ext}"


def detect_format_and_mime(file_name: str) -> tuple[str, str, str]:
    suffix = Path(file_name).suffix.lower()
    format_map = {
        ".md": "markdown",
        ".txt": "text",
        ".html": "html",
        ".htm": "html",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".csv": "csv",
        ".xlsx": "xlsx",
        ".pdf": "pdf",
        ".docx": "docx",
    }
    detected_format = format_map.get(suffix, "text")
    mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    return detected_format, suffix or ".txt", mime_type


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_bytes_exclusive(target: Path, content: bytes, *, logical_path: str) -> None:
    try:
        with target.open("xb") as file:
            file.write(content)
    except FileExistsError as e:
        raise FileExistsError(logical_path) from e


def document_to_list_item(document: DBKBDocument) -> KBDocumentListItem:
    return KBDocumentListItem(
        id=document.id,
        workspace_id=document.workspace_id,
        title=document.title,
        category=document.category,
        tags=document.tags if isinstance(document.tags, list) else [],
        summary=document.summary,
        file_name=document.file_name,
        file_ext=document.file_ext,
        mime_type=document.mime_type,
        format=document.format,  # type: ignore[arg-type]
        source_path=document.source_path,
        source_workspace_path=WorkspaceService.get_kb_source_workspace_path(document.source_path),
        normalized_text_path=document.normalized_text_path,
        normalized_workspace_path=(
            WorkspaceService.get_kb_normalized_workspace_path(document.normalized_text_path)
            if document.normalized_text_path else None
        ),
        is_enabled=document.is_enabled,
        extract_status=document.extract_status,  # type: ignore[arg-type]
        sync_status=document.sync_status,  # type: ignore[arg-type]
        chunk_count=document.chunk_count,
        file_size=int(document.file_size),
        last_error=document.last_error,
        last_indexed_at=document.last_indexed_at.isoformat() if document.last_indexed_at else None,
        update_time=document.update_time.isoformat(),
        create_time=document.create_time.isoformat(),
    )


async def list_documents(workspace_id: int) -> list[DBKBDocument]:
    return await DBKBDocument.filter(workspace_id=workspace_id).order_by("source_path").all()


async def get_document(workspace_id: int, document_id: int) -> DBKBDocument | None:
    return await DBKBDocument.get_or_none(id=document_id, workspace_id=workspace_id)


def read_source_content(document: DBKBDocument) -> str:
    source_path = WorkspaceService.resolve_kb_source_path(document.workspace_id, document.source_path)
    if not source_path.exists():
        return ""
    return source_path.read_text(encoding="utf-8", errors="replace")


def read_normalized_content(document: DBKBDocument) -> str:
    if not document.normalized_text_path:
        return ""
    normalized_path = WorkspaceService.resolve_kb_normalized_path(document.workspace_id, document.normalized_text_path)
    if not normalized_path.exists():
        return ""
    return normalized_path.read_text(encoding="utf-8", errors="replace")


async def create_text_document(
    *,
    workspace_id: int,
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
) -> DBKBDocument:
    WorkspaceService.ensure_kb_dirs(workspace_id)
    final_file_name = file_name or build_default_file_name(title, ".md" if format == "markdown" else ".txt")
    final_source_path = safe_source_path(source_path or final_file_name)
    target = WorkspaceService.resolve_kb_source_path(workspace_id, final_source_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = content.encode("utf-8")
    write_bytes_exclusive(target, encoded, logical_path=final_source_path)
    detected_format, suffix, mime_type = detect_format_and_mime(Path(final_source_path).name)
    try:
        return await DBKBDocument.create(
            workspace_id=workspace_id,
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
            content_hash=compute_sha256(encoded),
            normalized_text_hash="",
            chunk_count=0,
            file_size=len(encoded),
        )
    except Exception:
        if target.exists():
            target.unlink()
        raise


async def create_file_document(
    *,
    workspace_id: int,
    upload_file: UploadFile,
    source_path: str,
    title: str,
    category: str,
    tags: list[str],
    summary: str,
    is_enabled: bool,
    source_type: str = "upload",
) -> DBKBDocument:
    WorkspaceService.ensure_kb_dirs(workspace_id)
    original_name = upload_file.filename or f"kb-upload-{int(datetime.now().timestamp())}.txt"
    final_source_path = safe_source_path(source_path or original_name)
    target = WorkspaceService.resolve_kb_source_path(workspace_id, final_source_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = await upload_file.read()
    write_bytes_exclusive(target, content, logical_path=final_source_path)
    detected_format, suffix, mime_type = detect_format_and_mime(Path(final_source_path).name)
    try:
        return await DBKBDocument.create(
            workspace_id=workspace_id,
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
            content_hash=compute_sha256(content),
            normalized_text_hash="",
            chunk_count=0,
            file_size=len(content),
        )
    except Exception:
        if target.exists():
            target.unlink()
        raise


async def update_document_metadata(
    document: DBKBDocument,
    *,
    title: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    is_enabled: bool | None = None,
    source_path: str | None = None,
    content: str | None = None,
) -> DBKBDocument:
    update_fields: list[str] = []
    old_source_path = document.source_path
    old_file_name = document.file_name
    old_file_ext = document.file_ext
    old_mime_type = document.mime_type
    old_content_hash = document.content_hash
    old_file_size = document.file_size
    old_extract_status = document.extract_status
    old_sync_status = document.sync_status
    current_path = WorkspaceService.resolve_kb_source_path(document.workspace_id, document.source_path)
    target_path = current_path
    original_bytes: bytes | None = None
    remove_target_on_failure = False
    moved_paths: tuple[Path, Path] | None = None

    if title is not None:
        document.title = title.strip()
        update_fields.append("title")
    if category is not None:
        document.category = category.strip()
        update_fields.append("category")
    if tags is not None:
        document.tags = normalize_tags(tags)
        update_fields.append("tags")
    if summary is not None:
        document.summary = summary.strip()
        update_fields.append("summary")
    if is_enabled is not None:
        document.is_enabled = is_enabled
        update_fields.append("is_enabled")
    try:
        if source_path is not None and source_path.strip():
            new_rel_path = safe_source_path(source_path)
            if new_rel_path != document.source_path:
                conflict_exists = await DBKBDocument.filter(
                    workspace_id=document.workspace_id,
                    source_path=new_rel_path,
                ).exclude(id=document.id).exists()
                if conflict_exists:
                    raise FileExistsError(new_rel_path)

                new_path = WorkspaceService.resolve_kb_source_path(document.workspace_id, new_rel_path)
                new_path.parent.mkdir(parents=True, exist_ok=True)
                if new_path.exists():
                    raise FileExistsError(new_rel_path)
                if current_path.exists():
                    current_path.rename(new_path)
                    moved_paths = (current_path, new_path)
                target_path = new_path
                document.source_path = new_rel_path
                document.file_name = new_path.name
                _, suffix, mime_type = detect_format_and_mime(document.file_name)
                document.file_ext = suffix
                document.mime_type = mime_type
                update_fields.extend(["source_path", "file_name", "file_ext", "mime_type"])

        if content is not None:
            if document.format not in TEXT_FORMATS:
                raise ValueError("仅文本类知识文档允许直接更新正文内容")
            encoded = content.encode("utf-8")
            if target_path.exists():
                original_bytes = target_path.read_bytes()
            else:
                remove_target_on_failure = True
            target_path.write_bytes(encoded)
            document.content_hash = compute_sha256(encoded)
            document.file_size = len(encoded)
            document.extract_status = "pending"
            document.sync_status = "pending"
            update_fields.extend(["content_hash", "file_size", "extract_status", "sync_status"])

        if update_fields:
            await document.save(update_fields=[*sorted(set(update_fields)), "update_time"])
    except Exception:
        document.source_path = old_source_path
        document.file_name = old_file_name
        document.file_ext = old_file_ext
        document.mime_type = old_mime_type
        document.content_hash = old_content_hash
        document.file_size = old_file_size
        document.extract_status = old_extract_status
        document.sync_status = old_sync_status

        if content is not None:
            if original_bytes is not None:
                target_path.write_bytes(original_bytes)
            elif remove_target_on_failure and target_path.exists():
                target_path.unlink()
        if moved_paths is not None:
            old_path, new_path = moved_paths
            if new_path.exists() and not old_path.exists():
                new_path.rename(old_path)
        raise
    return document


# ---------------------------------------------------------------------------
# 文档引用关系管理
# ---------------------------------------------------------------------------


def _doc_to_reference_item(ref: DBKBDocumentReference, doc: DBKBDocument, is_source: bool) -> KBReferenceItem:
    return KBReferenceItem(
        ref_id=ref.id,
        document_id=doc.id,
        title=doc.title,
        category=doc.category,
        format=doc.format,  # type: ignore[arg-type]
        summary=doc.summary,
        description=ref.description,
        is_auto=ref.is_auto,
    )


async def get_document_references(workspace_id: int, document_id: int) -> KBDocumentReferences:
    refs_to = await DBKBDocumentReference.filter(
        workspace_id=workspace_id, source_document_id=document_id
    ).all()
    refs_by = await DBKBDocumentReference.filter(
        workspace_id=workspace_id, target_document_id=document_id
    ).all()

    target_ids = [r.target_document_id for r in refs_to]
    source_ids = [r.source_document_id for r in refs_by]
    all_ids = list(set(target_ids + source_ids))

    docs = await DBKBDocument.filter(id__in=all_ids, workspace_id=workspace_id).all()
    doc_map = {doc.id: doc for doc in docs}

    references_to = [
        _doc_to_reference_item(ref, doc, is_source=True)
        for ref in refs_to
        if (doc := doc_map.get(ref.target_document_id)) is not None
    ]
    referenced_by = [
        _doc_to_reference_item(ref, doc, is_source=False)
        for ref in refs_by
        if (doc := doc_map.get(ref.source_document_id)) is not None
    ]
    return KBDocumentReferences(references_to=references_to, referenced_by=referenced_by)


async def add_document_reference(
    workspace_id: int,
    source_document_id: int,
    target_document_id: int,
    description: str,
) -> DBKBDocumentReference:
    if source_document_id == target_document_id:
        raise ValueError("不能引用自身")
    ref, _ = await DBKBDocumentReference.get_or_create(
        source_document_id=source_document_id,
        target_document_id=target_document_id,
        defaults={"workspace_id": workspace_id, "description": description},
    )
    if ref.description != description or ref.workspace_id != workspace_id:
        ref.description = description
        ref.workspace_id = workspace_id
        await ref.save(update_fields=["description", "workspace_id", "update_time"])
    return ref


async def remove_document_reference(
    workspace_id: int,
    source_document_id: int,
    target_document_id: int,
) -> bool:
    deleted = await DBKBDocumentReference.filter(
        workspace_id=workspace_id,
        source_document_id=source_document_id,
        target_document_id=target_document_id,
    ).delete()
    return deleted > 0


async def get_referenced_document_ids(workspace_id: int, document_ids: list[int]) -> dict[int, list[int]]:
    """批量查询多个文档引用了哪些文档，用于搜索时联动展开。"""
    if not document_ids:
        return {}
    refs = await DBKBDocumentReference.filter(
        workspace_id=workspace_id, source_document_id__in=document_ids
    ).all()
    result: dict[int, list[int]] = {doc_id: [] for doc_id in document_ids}
    for ref in refs:
        result[ref.source_document_id].append(ref.target_document_id)
    return result
