from tortoise import fields
from tortoise.models import Model


class DBEmail(Model):
    """邮件模型，用于存储已处理的邮件信息"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    account_username = fields.CharField(max_length=256, index=True, description="所属邮箱账户")
    email_uid = fields.CharField(max_length=128, description="IMAP UID")
    message_id = fields.CharField(max_length=512, default="", description="Message-ID 头")
    subject = fields.CharField(max_length=1024, default="", description="邮件主题")
    sender = fields.CharField(max_length=512, default="", description="发件人")
    recipients = fields.TextField(default="", description="收件人(JSON)")
    date = fields.DatetimeField(null=True, description="邮件日期")
    body_text = fields.TextField(default="", description="纯文本正文(截断)")
    has_attachments = fields.BooleanField(default=False, description="是否有附件")
    attachment_names = fields.TextField(default="", description="附件文件名列表(JSON)")
    in_reply_to = fields.CharField(max_length=512, default="", description="In-Reply-To 头")
    references = fields.TextField(default="", description="References 头")
    fetched_at = fields.DatetimeField(auto_now_add=True, description="获取时间")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "email"
        unique_together = (("account_username", "email_uid"),)
