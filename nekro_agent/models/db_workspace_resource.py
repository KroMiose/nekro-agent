from tortoise import fields
from tortoise.models import Model


class DBWorkspaceResource(Model):
    """工作区资源定义模型。"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    resource_key = fields.CharField(max_length=128, unique=True, index=True, description="稳定资源键")
    name = fields.CharField(max_length=128, index=True, description="资源名称")
    template_key = fields.CharField(max_length=64, null=True, description="模板键")
    resource_note = fields.TextField(default="", description="资源备注")
    resource_tags_json = fields.JSONField(default=list, description="资源标签列表")
    resource_prompt = fields.TextField(default="", description="资源提示")
    schema_json = fields.JSONField(default=list, description="字段结构定义")
    public_payload = fields.JSONField(default=dict, description="非敏感字段值")
    secret_payload_encrypted = fields.TextField(default="", description="加密后的敏感字段值")
    enabled = fields.BooleanField(default=True, description="是否启用")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "workspace_resource"
