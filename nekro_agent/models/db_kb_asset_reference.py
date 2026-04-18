from tortoise import fields
from tortoise.models import Model


class DBKBAssetReference(Model):
    """全局知识库资产间引用关系。"""

    id = fields.IntField(pk=True, generated=True, description="引用记录 ID")
    source_asset_id = fields.IntField(index=True, description="发起引用的资产 ID")
    target_asset_id = fields.IntField(index=True, description="被引用的资产 ID")
    description = fields.CharField(max_length=500, default="", description="引用说明，描述被引用资产补充了哪些内容")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "kb_asset_reference"
        unique_together = [("source_asset_id", "target_asset_id")]
        indexes = [
            ("source_asset_id",),
            ("target_asset_id",),
        ]
