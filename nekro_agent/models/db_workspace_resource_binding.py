from tortoise import fields
from tortoise.models import Model


class DBWorkspaceResourceBinding(Model):
    """工作区与资源绑定关系。"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    workspace_id = fields.IntField(index=True, description="工作区 ID")
    resource_id = fields.IntField(index=True, description="资源 ID")
    enabled = fields.BooleanField(default=True, description="是否启用")
    sort_order = fields.IntField(default=0, description="排序")
    note = fields.CharField(max_length=256, default="", description="备注")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "workspace_resource_binding"
        unique_together = (("workspace_id", "resource_id"),)
        indexes = [
            ("workspace_id", "sort_order"),
            ("workspace_id", "enabled"),
        ]
