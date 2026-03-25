"""记忆段落模型

承载可检索叙述文本，作为向量召回主对象。
连接原始事件流与结构化图谱。
"""

from enum import Enum
from typing import Any

from tortoise import fields
from tortoise.models import Model


class CognitiveType(str, Enum):
    """认知类型枚举"""

    EPISODIC = "episodic"  # 情景记忆：依赖时间语境，快速衰减
    SEMANTIC = "semantic"  # 语义记忆：技术事实型，长期保留


class KnowledgeType(str, Enum):
    """知识类型枚举"""

    CONVERSATION = "conversation"  # 对话内容
    PREFERENCE = "preference"  # 用户偏好
    FACT = "fact"  # 事实信息
    EXPERIENCE = "experience"  # 经验总结
    DECISION = "decision"  # 决策记录
    EMOTION = "emotion"  # 情感状态


class OriginKind(str, Enum):
    """记忆来源类型枚举"""

    MESSAGE = "message"  # 从单条消息提取
    CONSOLIDATION = "consolidation"  # 对话片段沉淀
    TASK = "task"  # CC 任务结论
    MANUAL = "manual"  # 用户/系统手动创建
    PLUGIN = "plugin"  # 第三方插件创建


class EpisodePhase(str, Enum):
    """段落在 Episode 中的阶段。"""

    OPENING = "opening"
    DEVELOPMENT = "development"
    CLIMAX = "climax"
    RESOLUTION = "resolution"


class DBMemParagraph(Model):
    """记忆段落模型

    承载可检索的叙述文本，是记忆系统的核心存储单元。
    """

    id = fields.IntField(pk=True, generated=True, description="主键 ID")
    workspace_id = fields.IntField(index=True, description="工作区 ID（隔离边界）")

    # === 记忆分类 ===
    memory_source = fields.CharField(
        max_length=8,
        index=True,
        description="记忆来源（na/cc）",
    )
    cognitive_type = fields.CharEnumField(
        CognitiveType,
        max_length=16,
        index=True,
        description="认知类型（episodic/semantic）",
    )
    knowledge_type = fields.CharEnumField(
        KnowledgeType,
        max_length=16,
        index=True,
        description="知识类型",
    )

    # === 记忆内容 ===
    content = fields.TextField(description="记忆主体内容（第三人称叙述）")
    summary = fields.CharField(
        max_length=512,
        null=True,
        description="简短摘要（用于快速展示）",
    )
    event_time = fields.DatetimeField(
        null=True,
        index=True,
        description="事件发生时间（对 episodic 特别重要）",
    )
    episode_id = fields.IntField(
        null=True,
        index=True,
        description="所属 Episode ID",
    )
    episode_phase = fields.CharEnumField(
        EpisodePhase,
        max_length=16,
        null=True,
        description="在 Episode 中的阶段",
    )

    # === 生命周期管理 ===
    base_weight = fields.FloatField(default=1.0, description="基础权重")
    last_reinforced_at = fields.DatetimeField(
        null=True,
        description="最后一次强化时间",
    )
    half_life_seconds = fields.IntField(
        default=7200,  # 默认 2 小时（情景记忆）
        description="半衰期（秒）",
    )
    is_inactive = fields.BooleanField(default=False, index=True, description="是否已失活")

    # === 向量索引 ===
    embedding_ref = fields.CharField(
        max_length=64,
        null=True,
        index=True,
        description="Qdrant 向量 ID 引用",
    )

    # === 来源追溯 ===
    origin_kind = fields.CharEnumField(
        OriginKind,
        max_length=16,
        description="来源类型",
    )
    origin_ref = fields.CharField(
        max_length=256,
        null=True,
        description="来源引用（消息ID/任务ID等）",
    )

    # === 原始数据锚定（供追溯与插件扩展）===
    origin_chat_key = fields.CharField(
        max_length=128,
        null=True,
        index=True,
        description="记忆产生的聊天频道标识",
    )
    anchor_msg_id = fields.CharField(
        max_length=64,
        null=True,
        index=True,
        description="锚定的单条原始消息 ID",
    )
    anchor_msg_id_start = fields.CharField(
        max_length=64,
        null=True,
        description="对话片段起始消息 ID",
    )
    anchor_msg_id_end = fields.CharField(
        max_length=64,
        null=True,
        description="对话片段结束消息 ID",
    )
    anchor_timestamp_start = fields.IntField(
        null=True,
        description="对话片段起始时间戳",
    )
    anchor_timestamp_end = fields.IntField(
        null=True,
        description="对话片段结束时间戳",
    )

    # === 手动干涉字段 ===
    is_protected = fields.BooleanField(
        default=False,
        description="受保护，永不自动清理",
    )
    is_frozen = fields.BooleanField(
        default=False,
        description="冻结状态，暂停衰减",
    )
    manual_weight_delta = fields.FloatField(
        default=0.0,
        description="手动调整的权重增量",
    )
    last_manual_action = fields.CharField(
        max_length=32,
        null=True,
        description="最后一次手动操作类型",
    )
    last_manual_action_at = fields.DatetimeField(
        null=True,
        description="最后一次手动操作时间",
    )

    # === 多模态关联 ===
    media_refs = fields.JSONField(
        default=list,
        description="关联的媒体资源 ID 列表",
    )

    # === 时间戳 ===
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "mem_paragraph"
        indexes = [
            ("workspace_id", "cognitive_type"),
            ("workspace_id", "memory_source"),
            ("workspace_id", "is_inactive"),
            ("workspace_id", "event_time"),
        ]

    def __str__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Paragraph({self.cognitive_type.value}:{preview})"

    def compute_effective_weight(self, now_timestamp: float) -> float:
        """计算当前有效权重（读时衰减）

        采用指数衰减公式：W(t) = W_base * 2^(-Δt/T_half) + W_manual

        Args:
            now_timestamp: 当前时间戳

        Returns:
            有效权重值
        """
        import math

        # 冻结状态不衰减
        if self.is_frozen:
            return self.base_weight + self.manual_weight_delta

        # 计算时间差（秒）
        if self.last_reinforced_at:
            last_ts = self.last_reinforced_at.timestamp()
        elif self.event_time:
            last_ts = self.event_time.timestamp()
        else:
            last_ts = self.create_time.timestamp()

        delta_seconds = max(0, now_timestamp - last_ts)

        # 指数衰减
        decay_factor = math.pow(2, -delta_seconds / self.half_life_seconds)
        decayed_weight = self.base_weight * decay_factor

        # 加上手动调整
        return decayed_weight + self.manual_weight_delta

    async def reinforce(self, boost: float = 0.3) -> None:
        """强化记忆（被命中时调用）

        Args:
            boost: 强化增量，默认 0.3
        """
        from datetime import datetime

        self.base_weight = min(self.base_weight + boost, 2.0)  # 上限 2.0
        self.last_reinforced_at = datetime.now()
        await self.save(update_fields=["base_weight", "last_reinforced_at", "update_time"])

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "memory_source": self.memory_source,
            "cognitive_type": self.cognitive_type.value,
            "knowledge_type": self.knowledge_type.value,
            "content": self.content,
            "summary": self.summary,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "episode_id": self.episode_id,
            "episode_phase": self.episode_phase.value if self.episode_phase else None,
            "base_weight": self.base_weight,
            "is_inactive": self.is_inactive,
            "is_protected": self.is_protected,
            "is_frozen": self.is_frozen,
            "origin_kind": self.origin_kind.value,
            "origin_chat_key": self.origin_chat_key,
        }

    def to_qdrant_payload(self) -> dict[str, Any]:
        """转换为 Qdrant payload 格式"""
        return {
            "workspace_id": self.workspace_id,
            "memory_source": self.memory_source,
            "cognitive_type": self.cognitive_type.value,
            "knowledge_type": self.knowledge_type.value,
            "paragraph_id": self.id,
            "is_inactive": self.is_inactive,
            "event_time": int(self.event_time.timestamp()) if self.event_time else None,
            "base_weight": self.base_weight,
        }
