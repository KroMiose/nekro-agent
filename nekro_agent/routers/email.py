import json
from email.header import decode_header
from email.utils import getaddresses, parseaddr
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_email import DBEmail
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import NotFoundError
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role


class EmailItem(BaseModel):
    """邮件列表项"""

    id: int
    account_username: str
    subject: str
    sender: str
    date: Optional[str] = None
    body_preview: str = Field(description="邮件正文预览（前200字符）")
    has_attachments: bool
    create_time: str


class EmailDetail(BaseModel):
    """邮件详情"""

    id: int
    account_username: str
    email_uid: str
    message_id: str
    subject: str
    sender: str
    recipients: str
    date: Optional[str] = None
    body_text: str
    has_attachments: bool
    attachment_names: str
    attachments: List["EmailAttachmentItem"] = Field(default_factory=list)
    in_reply_to: str
    references: str
    create_time: str


class EmailAttachmentItem(BaseModel):
    """邮件附件项"""

    name: str
    url: str
    extension: str
    preview_type: str


class EmailRawContent(BaseModel):
    """邮件原始内容"""

    html_content: str = ""
    text_content: str = ""


class PaginationMeta(BaseModel):
    """分页元数据"""

    offset: int
    limit: int
    total: int
    has_more: bool


class EmailListResponse(BaseModel):
    """邮件列表响应"""

    items: List[EmailItem]
    pagination: PaginationMeta


router = APIRouter(prefix="/emails", tags=["Emails"])


def _decode_mime_words(value: str) -> str:
    if not value:
        return ""

    decoded_parts: list[str] = []
    for part, encoding in decode_header(value):
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(encoding or "utf-8", errors="ignore"))
            except LookupError:
                decoded_parts.append(part.decode("utf-8", errors="ignore"))
        else:
            decoded_parts.append(part)
    return "".join(decoded_parts).strip()


def _format_email_address(raw_value: str) -> str:
    if not raw_value:
        return ""

    name, addr = parseaddr(raw_value)
    decoded_name = _decode_mime_words(name).strip().strip('"')
    normalized_addr = addr.strip()

    if not normalized_addr:
        return decoded_name or raw_value.strip()

    local_part = normalized_addr.split("@", 1)[0].strip().lower()
    normalized_name = decoded_name.lower()

    if not decoded_name or normalized_name in {normalized_addr.lower(), local_part}:
        return normalized_addr
    return f"{decoded_name} <{normalized_addr}>"


def _normalize_recipients(raw_recipients: str) -> str:
    if not raw_recipients:
        return "[]"

    try:
        loaded = json.loads(raw_recipients)
        raw_items = [str(item) for item in loaded] if isinstance(loaded, list) else [str(loaded)]
    except json.JSONDecodeError:
        raw_items = [raw_recipients]

    normalized: list[str] = []
    for item in raw_items:
        parsed_items = getaddresses([item])
        if parsed_items:
            for name, addr in parsed_items:
                formatted = _format_email_address(f"{name} <{addr}>")
                if formatted:
                    normalized.append(formatted)
            continue

        formatted = _format_email_address(item)
        if formatted:
            normalized.append(formatted)

    return json.dumps(normalized, ensure_ascii=False)


def _guess_preview_type(extension: str) -> str:
    normalized = extension.lower()
    if normalized in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}:
        return "image"
    if normalized in {".md", ".markdown"}:
        return "markdown"
    if normalized in {".txt", ".log", ".csv", ".json", ".yaml", ".yml"}:
        return "text"
    if normalized in {".pdf"}:
        return "pdf"
    return "download"


def _build_attachment_items(account_username: str, email_uid: str, raw_attachment_names: str) -> List[EmailAttachmentItem]:
    attachment_names = parse_json_names(raw_attachment_names)
    if not attachment_names:
        return []

    base_dir = Path(OsEnv.DATA_DIR) / "uploads" / "email_attachment" / account_username / email_uid
    items: list[EmailAttachmentItem] = []
    for name in attachment_names:
        safe_name = Path(name).name
        file_path = base_dir / safe_name
        if not file_path.exists() or not file_path.is_file():
            continue

        extension = file_path.suffix.lower()
        preview_type = _guess_preview_type(extension)
        url = f"/api/emails/{account_username}/{email_uid}/attachments/{safe_name}"
        items.append(
            EmailAttachmentItem(
                name=safe_name,
                url=url,
                extension=extension,
                preview_type=preview_type,
            )
        )
    return items


def parse_json_names(raw_value: str) -> List[str]:
    if not raw_value:
        return []
    try:
        loaded = json.loads(raw_value)
        if isinstance(loaded, list):
            return [str(item) for item in loaded if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in raw_value.split(",") if item.strip()]


@router.get("", summary="获取邮件列表")
@require_role(Role.User)
async def get_emails(
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(25, ge=1, le=100, description="每页数量"),
    account: Optional[str] = Query(None, description="筛选账户"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> EmailListResponse:
    """获取邮件列表，支持分页和账户筛选"""
    query = DBEmail.all()

    if account:
        query = query.filter(account_username=account)

    total = await query.count()
    emails = await query.offset(offset).limit(limit).order_by("-create_time")

    items = [
        EmailItem(
            id=email.id,
            account_username=email.account_username,
            subject=email.subject,
            sender=_format_email_address(email.sender),
            date=email.date.isoformat() if email.date else None,
            body_preview=email.body_text[:200] if email.body_text else "",
            has_attachments=email.has_attachments,
            create_time=email.create_time.isoformat(),
        )
        for email in emails
    ]

    return EmailListResponse(
        items=items,
        pagination=PaginationMeta(
            offset=offset,
            limit=limit,
            total=total,
            has_more=offset + limit < total,
        ),
    )


@router.get("/{email_id}", summary="获取邮件详情")
@require_role(Role.User)
async def get_email_detail(
    email_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> EmailDetail:
    """获取指定邮件的详细信息"""
    email = await DBEmail.get_or_none(id=email_id)

    if not email:
        raise NotFoundError(resource="邮件")

    return EmailDetail(
        id=email.id,
        account_username=email.account_username,
        email_uid=email.email_uid,
        message_id=email.message_id,
        subject=email.subject,
        sender=_format_email_address(email.sender),
        recipients=_normalize_recipients(email.recipients),
        date=email.date.isoformat() if email.date else None,
        body_text=email.body_text,
        has_attachments=email.has_attachments,
        attachment_names=email.attachment_names,
        attachments=_build_attachment_items(email.account_username, email.email_uid, email.attachment_names),
        in_reply_to=email.in_reply_to,
        references=email.references,
        create_time=email.create_time.isoformat(),
    )


@router.get("/{email_id}/raw-content", summary="获取邮件网页正文")
@require_role(Role.User)
async def get_email_raw_content(
    email_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> EmailRawContent:
    email = await DBEmail.get_or_none(id=email_id)
    if not email:
        raise NotFoundError(resource="邮件")

    from nekro_agent.adapters.email.routers import get_email_adapter

    adapter = get_email_adapter()
    raw_content = await adapter.get_raw_email_content(email.account_username, email.email_uid)
    return EmailRawContent(
        html_content=str(raw_content.get("html_content") or ""),
        text_content=str(raw_content.get("text_content") or ""),
    )


@router.get("/{account_username}/{email_uid}/attachments/{filename}", summary="获取邮件附件")
@require_role(Role.User)
async def get_email_attachment(
    account_username: str,
    email_uid: str,
    filename: str,
    _current_user: DBUser = Depends(get_current_active_user),
):
    safe_account = Path(account_username).name
    safe_uid = Path(email_uid).name
    safe_filename = Path(filename).name
    filepath = Path(OsEnv.DATA_DIR) / "uploads" / "email_attachment" / safe_account / safe_uid / safe_filename

    if not filepath.exists() or not filepath.is_file():
        raise NotFoundError(resource="附件")

    suffix = filepath.suffix.lower().lstrip(".")
    media_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "svg": "image/svg+xml",
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "json": "application/json",
        "pdf": "application/pdf",
    }
    media_type = media_map.get(suffix, "application/octet-stream")
    headers = {"Cache-Control": "private, max-age=3600"}
    if media_type == "application/octet-stream":
        headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
    return FileResponse(filepath, media_type=media_type, headers=headers, filename=safe_filename)
