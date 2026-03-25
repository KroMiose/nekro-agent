"""记忆媒体资源模型

缓存多模态资源的文本化描述，支持内容哈希去重。
记录引用链，追踪同一资源在不同对话中的出现。
"""

from enum import Enum
from typing import Any

from tortoise import fields
from tortoise.models import Model


class MediaType(str, Enum):
    """媒体类型"""

    IMAGE = "image"  # 图片
    AUDIO = "audio"  # 音频
    VIDEO = "video"  # 视频
    STICKER = "sticker"  # 表情包


class DBMemMediaResource(Model):
    """记忆媒体资源模型

    缓存多模态资源的文本化描述，实现：
    1. 内容哈希去重，避免重复处理
    2. 引用链追踪，形成记忆"线索"
    3. 与 mem_paragraph 关联
    """

    id = fields.IntField(pk=True, generated=True, description="主键 ID")
    workspace_id = fields.IntField(index=True, description="工作区 ID")

    # === 核心字段 ===
    content_hash = fields.CharField(
        max_length=64,
        index=True,
        unique=True,
        description="资源内容的 MD5/SHA256 哈希（全局唯一）",
    )
    media_type = fields.CharEnumField(
        MediaType,
        max_length=16,
        description="媒体类型",
    )
    description = fields.TextField(
        null=True,
        description="AI 生成的文本描述",
    )
    tags = fields.JSONField(
        default=list,
        description="标签列表（JSON 数组）",
    )
    embedding_ref = fields.CharField(
        max_length=64,
        null=True,
        index=True,
        description="可选的向量索引引用",
    )

    # === 元数据 ===
    original_filename = fields.CharField(
        max_length=256,
        null=True,
        description="原始文件名",
    )
    file_size = fields.IntField(null=True, description="文件大小（字节）")
    dimensions = fields.JSONField(
        null=True,
        description="图片/视频尺寸（如 {width: 800, height: 600}）",
    )
    duration = fields.FloatField(null=True, description="音视频时长（秒）")
    mime_type = fields.CharField(max_length=64, null=True, description="MIME 类型")

    # === 引用追踪 ===
    reference_count = fields.IntField(default=1, description="被引用次数")
    first_seen_at = fields.DatetimeField(auto_now_add=True, description="首次出现时间")
    last_seen_at = fields.DatetimeField(auto_now=True, description="最后出现时间")
    reference_log = fields.JSONField(
        default=list,
        description="引用记录（JSON 数组，限制最近 N 条）",
    )

    # === 时间戳 ===
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "mem_media_resource"
        indexes = [
            ("workspace_id", "media_type"),
            ("workspace_id", "reference_count"),
        ]

    def __str__(self) -> str:
        desc_preview = (self.description or "")[:30]
        return f"Media({self.media_type.value}:{self.content_hash[:8]}... {desc_preview})"

    def add_reference(
        self,
        chat_key: str,
        message_id: str,
        context_hint: str | None = None,
        max_log_size: int = 20,
    ) -> None:
        """添加引用记录

        Args:
            chat_key: 聊天频道标识
            message_id: 消息 ID
            context_hint: 上下文提示
            max_log_size: 最大日志数量
        """
        import time

        self.reference_count += 1

        # 构建新引用记录
        new_ref = {
            "chat_key": chat_key,
            "message_id": message_id,
            "timestamp": int(time.time()),
        }
        if context_hint:
            new_ref["context_hint"] = context_hint

        # 更新引用日志（保留最近 N 条）
        log: list[dict[str, Any]] = self.reference_log if isinstance(self.reference_log, list) else []
        log.append(new_ref)
        if len(log) > max_log_size:
            log = log[-max_log_size:]
        self.reference_log = log

    @classmethod
    async def find_by_hash(cls, content_hash: str) -> "DBMemMediaResource | None":
        """通过内容哈希查找资源"""
        return await cls.filter(content_hash=content_hash).first()

    @classmethod
    async def find_or_create(
        cls,
        workspace_id: int,
        content_hash: str,
        media_type: MediaType,
        chat_key: str,
        message_id: str,
        **kwargs: Any,
    ) -> tuple["DBMemMediaResource", bool]:
        """查找或创建媒体资源

        Returns:
            (resource, created): 资源对象和是否新创建
        """
        existing = await cls.find_by_hash(content_hash)

        if existing:
            existing.add_reference(chat_key, message_id)
            await existing.save(
                update_fields=["reference_count", "reference_log", "last_seen_at", "update_time"],
            )
            return existing, False

        # 创建新资源
        resource = await cls.create(
            workspace_id=workspace_id,
            content_hash=content_hash,
            media_type=media_type,
            reference_log=[
                {
                    "chat_key": chat_key,
                    "message_id": message_id,
                    "timestamp": int(__import__("time").time()),
                }
            ],
            **kwargs,
        )
        return resource, True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "content_hash": self.content_hash,
            "media_type": self.media_type.value,
            "description": self.description,
            "tags": self.tags,
            "file_size": self.file_size,
            "dimensions": self.dimensions,
            "reference_count": self.reference_count,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }

    def get_reference_summary(self) -> str:
        """获取引用摘要（用于记忆线索）"""
        log: list[dict[str, Any]] = self.reference_log if isinstance(self.reference_log, list) else []
        if not log:
            return "首次出现"

        if len(log) == 1:
            return "仅出现一次"

        # 统计不同频道
        chat_keys = set(ref.get("chat_key", "") for ref in log)
        return f"出现 {self.reference_count} 次，跨 {len(chat_keys)} 个对话"
