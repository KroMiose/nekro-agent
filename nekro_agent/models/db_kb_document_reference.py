from tortoise import fields
from tortoise.models import Model


class DBKBDocumentReference(Model):
    """工作区知识库文档间引用关系。"""

    id = fields.IntField(pk=True, generated=True, description="引用记录 ID")
    workspace_id = fields.IntField(index=True, description="所属工作区 ID（source 和 target 必须同属此工作区）")
    source_document_id = fields.IntField(index=True, description="发起引用的文档 ID")
    target_document_id = fields.IntField(index=True, description="被引用的文档 ID")
    description = fields.CharField(max_length=500, default="", description="引用说明，描述被引用文档补充了哪些内容")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "kb_document_reference"
        unique_together = [("source_document_id", "target_document_id")]
        indexes = [
            ("workspace_id", "source_document_id"),
            ("workspace_id", "target_document_id"),
        ]
