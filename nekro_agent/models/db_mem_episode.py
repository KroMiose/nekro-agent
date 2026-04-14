"""记忆 Episode 模型

将一组时间连续、主题相关的段落聚合为可复用事件单元。
"""

from enum import Enum
from typing import Any

from tortoise import fields
from tortoise.models import Model


class EpisodePhase(str, Enum):
    """Episode 内部阶段枚举。"""

    OPENING = "opening"
    DEVELOPMENT = "development"
    CLIMAX = "climax"
    RESOLUTION = "resolution"


class DBMemEpisode(Model):
    """Episode 聚合记忆模型。"""

    id = fields.IntField(pk=True, generated=True, description="主键 ID")
    workspace_id = fields.IntField(index=True, description="工作区 ID")
    origin_chat_key = fields.CharField(
        max_length=128,
        null=True,
        index=True,
        description="Episode 来源聊天频道",
    )
    title = fields.CharField(max_length=256, description="Episode 标题")
    narrative_summary = fields.TextField(description="Episode 叙事摘要")
    time_start = fields.DatetimeField(null=True, index=True, description="Episode 起始时间")
    time_end = fields.DatetimeField(null=True, index=True, description="Episode 结束时间")
    participant_entity_ids = fields.JSONField(default=list, description="参与实体 ID 列表")
    paragraph_ids = fields.JSONField(default=list, description="包含的段落 ID 列表")
    phase_mapping = fields.JSONField(default=dict, description="阶段到段落 ID 的映射")
    base_weight = fields.FloatField(default=1.0, description="Episode 基础权重")
    is_inactive = fields.BooleanField(default=False, index=True, description="是否已失活")
    embedding_ref = fields.CharField(max_length=64, null=True, index=True, description="预留向量引用")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "mem_episode"
        indexes = [
            ("workspace_id", "origin_chat_key"),
            ("workspace_id", "time_start"),
            ("workspace_id", "time_end"),
            ("workspace_id", "is_inactive"),
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "origin_chat_key": self.origin_chat_key,
            "title": self.title,
            "narrative_summary": self.narrative_summary,
            "time_start": self.time_start.isoformat() if self.time_start else None,
            "time_end": self.time_end.isoformat() if self.time_end else None,
            "participant_entity_ids": self.participant_entity_ids,
            "paragraph_ids": self.paragraph_ids,
            "phase_mapping": self.phase_mapping,
            "base_weight": self.base_weight,
            "is_inactive": self.is_inactive,
            "create_time": self.create_time.isoformat(),
            "update_time": self.update_time.isoformat(),
        }
