from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

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
    in_reply_to: str
    references: str
    create_time: str


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
            sender=email.sender,
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
        sender=email.sender,
        recipients=email.recipients,
        date=email.date.isoformat() if email.date else None,
        body_text=email.body_text,
        has_attachments=email.has_attachments,
        attachment_names=email.attachment_names,
        in_reply_to=email.in_reply_to,
        references=email.references,
        create_time=email.create_time.isoformat(),
    )
