from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model


class DBRecurringTimerJob(Model):
    """持久化周期定时任务（cron）"""

    id = fields.UUIDField(pk=True, description="任务ID（UUID）")

    # 对外任务ID：默认 4 位，必要时自动扩展位数；全局唯一
    job_id = fields.CharField(max_length=12, unique=True, index=True, description="对外任务ID（短ID，全局唯一）")

    chat_key = fields.CharField(max_length=64, index=True, description="目标聊天频道唯一标识")

    title = fields.CharField(max_length=128, null=True, description="任务标题（可选）")
    event_desc = fields.TextField(description="触发时提供给 Agent 的事件描述（上下文）")

    cron_expr = fields.CharField(max_length=128, description="Cron 表达式（默认 5 段：min hour day month dow）")
    timezone = fields.CharField(max_length=64, description="时区（IANA TZ，例如 Asia/Shanghai）")

    # none: 不做过滤；mon_fri: 周一到周五；weekend: 周六日；cn_workday: 中国法定工作日（含补班）；cn_restday: 中国休息日
    workday_mode = fields.CharField(
        max_length=16,
        default="none",
        description="触发日模式：none/mon_fri/weekend/cn_workday/cn_restday",
    )

    status = fields.CharField(max_length=16, default="active", index=True, description="状态：active/paused")

    next_run_at = fields.DatetimeField(null=True, index=True, description="下次触发时间（本地时区）")
    last_run_at = fields.DatetimeField(null=True, index=True, description="上次触发时间（本地时区）")

    # misfire: 服务重启或阻塞导致错过触发时的策略
    misfire_policy = fields.CharField(max_length=16, default="fire_once", description="错过触发策略：fire_once/skip")
    misfire_grace_seconds = fields.IntField(default=300, description="错过触发宽限秒数（在宽限内可补发）")

    consecutive_failures = fields.IntField(default=0, description="连续失败次数")
    if TYPE_CHECKING:
        last_error: str | None
        paused_notice_sent_at: datetime | None
    else:
        last_error = fields.TextField(null=True, description="最近一次失败原因（可选）")
        paused_notice_sent_at = fields.DatetimeField(null=True, description="自动暂停后已提示时间（用于去重提示）")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "recurring_timer_job"

