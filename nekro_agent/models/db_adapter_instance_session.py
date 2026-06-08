from tortoise import fields
from tortoise.models import Model


class DBAdapterInstanceSession(Model):
    """适配器实例会话模型，用于存储运行态凭据与同步状态。"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    instance_id = fields.IntField(index=True, description="适配器实例 ID")
    session_state = fields.CharField(max_length=64, default="", description="会话子状态")
    credentials_json = fields.TextField(default="", description="凭据数据(JSON)")
    sync_state_json = fields.TextField(default="", description="同步状态(JSON)")
    expires_at = fields.DatetimeField(null=True, description="过期时间")
    renewed_at = fields.DatetimeField(null=True, description="最近续期时间")
    last_cursor = fields.CharField(max_length=512, default="", description="最近同步游标")
    last_message_remote_id = fields.CharField(max_length=256, default="", description="最近远端消息 ID")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "adapter_instance_session"
