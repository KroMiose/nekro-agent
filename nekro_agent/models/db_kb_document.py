from tortoise import fields
from tortoise.models import Model


class DBKBDocument(Model):
    """知识库文档元数据。"""

    id = fields.IntField(pk=True, generated=True, description="文档 ID")
    workspace_id = fields.IntField(index=True, description="工作区 ID")
    source_path = fields.CharField(max_length=512, description="相对 kb/files 根目录的源文件路径")
    normalized_text_path = fields.CharField(max_length=256, null=True, description="相对 kb/.normalized 根目录的规范化全文路径")
    file_name = fields.CharField(max_length=256, description="原始文件名")
    file_ext = fields.CharField(max_length=32, description="文件扩展名")
    mime_type = fields.CharField(max_length=128, description="文件 MIME 类型")
    title = fields.CharField(max_length=255, description="文档标题")
    category = fields.CharField(max_length=64, default="", description="文档分类")
    tags = fields.JSONField(default=list, description="标签列表")
    summary = fields.TextField(default="", description="摘要")
    source_type = fields.CharField(max_length=32, default="manual", description="来源类型")
    format = fields.CharField(max_length=32, description="文档格式")
    is_enabled = fields.BooleanField(default=True, index=True, description="是否参与检索")
    extract_status = fields.CharField(max_length=32, default="pending", description="抽取状态")
    sync_status = fields.CharField(max_length=32, default="pending", description="索引状态")
    content_hash = fields.CharField(max_length=64, default="", description="原始文件内容哈希")
    normalized_text_hash = fields.CharField(max_length=64, default="", description="规范化全文哈希")
    chunk_count = fields.IntField(default=0, description="chunk 数量")
    file_size = fields.BigIntField(default=0, description="文件大小")
    last_indexed_at = fields.DatetimeField(null=True, description="最近索引时间")
    last_error = fields.TextField(null=True, description="最近错误")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "kb_document"
        unique_together = [("workspace_id", "source_path")]
        indexes = [
            ("workspace_id", "is_enabled"),
            ("workspace_id", "category"),
            ("workspace_id", "format"),
            ("workspace_id", "sync_status"),
        ]
