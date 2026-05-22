from tortoise import fields
from tortoise.models import Model


class DBKBAssetBinding(Model):
    """工作区与全局知识库资产绑定关系。"""

    id = fields.IntField(pk=True, generated=True, description="绑定 ID")
    workspace_id = fields.IntField(index=True, description="工作区 ID")
    asset_id = fields.IntField(index=True, description="全局资产 ID")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "kb_asset_binding"
        unique_together = [("workspace_id", "asset_id")]
        indexes = [
            ("workspace_id", "asset_id"),
        ]
