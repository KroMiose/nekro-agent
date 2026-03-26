from fastapi import APIRouter, Query

from nekro_agent.models.db_email import DBEmail

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("")
async def get_emails(
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(25, ge=1, le=100, description="每页数量"),
):
    """获取邮件列表"""
    emails = await DBEmail.all().offset(offset).limit(limit).order_by("-create_time")
    return [
        {
            "id": email.id,
            "account_username": email.account_username,
            "subject": email.subject,
            "sender": email.sender,
            "date": email.date.isoformat() if email.date else None,
            "body_text": email.body_text[:200],  # 只返回前200字符
            "has_attachments": email.has_attachments,
            "create_time": email.create_time.isoformat(),
        }
        for email in emails
    ]
