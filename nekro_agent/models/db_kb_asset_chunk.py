from typing import Any

from tortoise import fields
from tortoise.models import Model


class DBKBAssetChunk(Model):
    """全局知识库资产索引切块。"""

    id = fields.IntField(pk=True, generated=True, description="资产 Chunk ID")
    asset_id = fields.IntField(index=True, description="所属资产 ID")
    chunk_index = fields.IntField(description="资产内顺序")
    heading_path = fields.CharField(max_length=512, default="", description="标题层级路径")
    char_start = fields.IntField(default=0, description="字符起始偏移")
    char_end = fields.IntField(default=0, description="字符结束偏移")
    token_count = fields.IntField(default=0, description="估算 token 数")
    embedding_ref = fields.CharField(max_length=64, null=True, index=True, description="Qdrant 向量 ID")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "kb_asset_chunk"
        unique_together = [("asset_id", "chunk_index")]
        indexes = [
            ("asset_id", "chunk_index"),
        ]

    def to_qdrant_payload(self, *, asset: "Any", content_preview: str) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "chunk_index": self.chunk_index,
            "heading_path": self.heading_path,
            "content_preview": content_preview,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "token_count": self.token_count,
            "category": asset.category,
            "tags": asset.tags if isinstance(asset.tags, list) else [],
            "is_enabled": asset.is_enabled,
        }
