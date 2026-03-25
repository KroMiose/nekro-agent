"""记忆关系模型

表达实体与实体之间的关系，如：
- 用户 → 喜欢 → 概念
- 项目 → 包含 → 产物
- 事件 → 涉及 → 人物
"""

from typing import Any

from tortoise import fields
from tortoise.models import Model


class DBMemRelation(Model):
    """记忆关系模型

    表达实体与实体之间的结构连接。
    采用三元组形式：subject -> predicate -> object
    """

    id = fields.IntField(pk=True, generated=True, description="主键 ID")
    workspace_id = fields.IntField(index=True, description="工作区 ID（隔离边界）")

    # === 三元组结构 ===
    subject_entity_id = fields.IntField(index=True, description="主体实体 ID")
    predicate = fields.CharField(max_length=64, index=True, description="关系谓词")
    object_entity_id = fields.IntField(index=True, description="客体实体 ID")

    # === 来源关联 ===
    paragraph_id = fields.IntField(
        null=True,
        index=True,
        description="来源段落 ID（关系从哪段叙述提取）",
    )
    memory_source = fields.CharField(
        max_length=8,
        description="记忆来源（na/cc）",
    )
    cognitive_type = fields.CharField(
        max_length=16,
        description="认知类型（episodic/semantic）",
    )

    # === 生命周期管理 ===
    base_weight = fields.FloatField(default=1.0, description="基础权重")
    last_reinforced_at = fields.DatetimeField(
        null=True,
        description="最后一次强化时间",
    )
    half_life_seconds = fields.IntField(
        default=86400,  # 默认 1 天
        description="半衰期（秒）",
    )
    is_inactive = fields.BooleanField(default=False, index=True, description="是否已失活")

    # === 时间戳 ===
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "mem_relation"
        indexes = [
            ("workspace_id", "subject_entity_id"),
            ("workspace_id", "object_entity_id"),
            ("workspace_id", "predicate"),
            ("subject_entity_id", "predicate", "object_entity_id"),  # 三元组唯一性
        ]

    def __str__(self) -> str:
        return f"Relation({self.subject_entity_id}-[{self.predicate}]->{self.object_entity_id})"

    def compute_effective_weight(self, now_timestamp: float) -> float:
        """计算当前有效权重（读时衰减）"""
        import math

        if self.last_reinforced_at:
            last_ts = self.last_reinforced_at.timestamp()
        else:
            last_ts = self.create_time.timestamp()

        delta_seconds = max(0, now_timestamp - last_ts)
        decay_factor = math.pow(2, -delta_seconds / self.half_life_seconds)
        return self.base_weight * decay_factor

    async def reinforce(self, boost: float = 0.2) -> None:
        """强化关系"""
        from datetime import datetime

        self.base_weight = min(self.base_weight + boost, 2.0)
        self.last_reinforced_at = datetime.now()
        await self.save(update_fields=["base_weight", "last_reinforced_at", "update_time"])

    @classmethod
    async def find_or_create(
        cls,
        workspace_id: int,
        subject_entity_id: int,
        predicate: str,
        object_entity_id: int,
        paragraph_id: int | None = None,
        memory_source: str = "na",
        cognitive_type: str = "episodic",
    ) -> tuple["DBMemRelation", bool]:
        """查找或创建关系

        Returns:
            (relation, created): 关系对象和是否新创建
        """
        predicate_normalized = predicate.strip().lower()

        existing = await cls.filter(
            workspace_id=workspace_id,
            subject_entity_id=subject_entity_id,
            predicate=predicate_normalized,
            object_entity_id=object_entity_id,
            is_inactive=False,
        ).first()

        if existing:
            await existing.reinforce(0.1)
            return existing, False

        relation = await cls.create(
            workspace_id=workspace_id,
            subject_entity_id=subject_entity_id,
            predicate=predicate_normalized,
            object_entity_id=object_entity_id,
            paragraph_id=paragraph_id,
            memory_source=memory_source,
            cognitive_type=cognitive_type,
        )
        return relation, True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "subject_entity_id": self.subject_entity_id,
            "predicate": self.predicate,
            "object_entity_id": self.object_entity_id,
            "paragraph_id": self.paragraph_id,
            "memory_source": self.memory_source,
            "cognitive_type": self.cognitive_type,
            "base_weight": self.base_weight,
            "is_inactive": self.is_inactive,
        }
