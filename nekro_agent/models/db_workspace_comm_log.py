from tortoise import fields
from tortoise.models import Model


class DBWorkspaceCommLog(Model):
    """NA↔CC 通讯日志"""

    id = fields.IntField(pk=True, generated=True)
    workspace_id = fields.IntField(index=True, description="关联工作区 ID")
    direction = fields.CharField(
        max_length=16,
        description="NA_TO_CC | CC_TO_NA | USER_TO_CC | SYSTEM",
    )
    source_chat_key = fields.CharField(max_length=128, default="", description="来源频道 chat_key，用户手动发送时为 __user__")
    content = fields.TextField(description="消息内容")
    is_streaming = fields.BooleanField(default=False, description="是否为流式聚合结果")
    task_id = fields.CharField(max_length=128, null=True, description="关联任务 ID")
    create_time = fields.DatetimeField(auto_now_add=True, index=True, description="创建时间")

    class Meta:
        table = "workspace_comm_log"
        ordering = ["create_time"]
