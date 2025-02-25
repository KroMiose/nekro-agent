from enum import IntEnum

from tortoise import fields
from tortoise.models import Model


class ReportStatus(IntEnum):
    """报告状态枚举"""

    NOT_REPORTED = 0  # 未报告
    REPORTED = 1  # 已报告
    PROCESSING = 2  # 处理中
    FAILED = 3  # 报告失败


class DBDashboardStats(Model):
    """仪表盘统计数据模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")

    # 时间维度
    stat_time = fields.DatetimeField(description="统计时间点")
    time_span = fields.CharField(max_length=16, description="时间维度(hour/day/week/month)")

    # 聊天统计
    total_messages = fields.IntField(default=0, description="总消息数")
    active_sessions = fields.IntField(default=0, description="活跃会话数")
    unique_users = fields.IntField(default=0, description="独立用户数")

    # 沙盒执行统计
    total_sandbox_calls = fields.IntField(default=0, description="沙盒调用总数")
    success_sandbox_calls = fields.IntField(default=0, description="成功调用数")
    failed_sandbox_calls = fields.IntField(default=0, description="失败调用数")
    agent_sandbox_calls = fields.IntField(default=0, description="代理调用数")

    # 性能指标
    avg_exec_time_ms = fields.FloatField(default=0, description="平均执行时间(ms)")
    max_exec_time_ms = fields.FloatField(default=0, description="最大执行时间(ms)")
    avg_generation_time_ms = fields.FloatField(default=0, description="平均生成时间(ms)")
    max_generation_time_ms = fields.FloatField(default=0, description="最大生成时间(ms)")

    # 会话类型分布
    group_messages = fields.IntField(default=0, description="群聊消息数")
    private_messages = fields.IntField(default=0, description="私聊消息数")

    # 活跃度排名数据
    most_active_users = fields.JSONField(default=list, description="最活跃用户列表")
    most_active_groups = fields.JSONField(default=list, description="最活跃群组列表")

    # 遥测系统状态
    report_status = fields.IntEnumField(ReportStatus, default=ReportStatus.NOT_REPORTED, description="报告状态")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "dashboard_stats"
        unique_together = (("stat_time", "time_span"),)
