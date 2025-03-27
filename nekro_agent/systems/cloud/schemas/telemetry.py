from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from nekro_agent.models.db_exec_code import ExecStopType
from nekro_agent.systems.cloud.schemas.base import BasicResponse


class TelemetryStatsType(str, Enum):
    """遥测统计类型"""

    TOTAL = "total"  # 总体统计
    HOURLY = "hourly"  # 小时统计


class ExecStopTypeStat(BaseModel):
    """执行停止类型统计"""

    stop_type: ExecStopType = Field(..., description="停止类型")
    count: int = Field(..., description="次数")


class TelemetryStats(BaseModel):
    """遥测统计数据"""

    stats_type: TelemetryStatsType = Field(..., description="统计类型")
    total_users: int = Field(default=0, description="总用户量")
    total_sessions: int = Field(default=0, description="总会话量")
    total_messages: int = Field(default=0, description="总消息量")
    total_sandbox_calls: int = Field(default=0, description="总沙盒执行次数")
    stop_type_stats: List[ExecStopTypeStat] = Field(default_factory=list, description="停止类型统计")

    active_users: Optional[int] = Field(default=None, description="活跃用户量（小时统计专用）")
    active_sessions: Optional[int] = Field(default=None, description="活跃会话量（小时统计专用）")

    # 性能指标
    avg_exec_time_ms: Optional[float] = Field(default=None, description="平均执行时间(毫秒)")
    max_exec_time_ms: Optional[float] = Field(default=None, description="最大执行时间(毫秒)")

    # 会话类型分布
    group_messages: Optional[int] = Field(default=None, description="群聊消息数")
    private_messages: Optional[int] = Field(default=None, description="私聊消息数")

    # 统计时间范围
    stats_start_time: Optional[datetime] = Field(default=None, description="统计开始时间")
    stats_end_time: Optional[datetime] = Field(default=None, description="统计结束时间")
    hour_timestamp: Optional[int] = Field(default=None, description="统计小时时间戳（整点时间戳）")


class TelemetryData(BaseModel):
    """遥测数据包"""

    instance_id: str = Field(..., description="实例唯一ID")
    total_stats: TelemetryStats = Field(..., description="总览统计信息")
    hourly_stats: TelemetryStats = Field(..., description="小时统计信息")
    app_version: str = Field(..., description="应用版本")
    is_docker: bool = Field(..., description="是否Docker运行")
    report_time: datetime = Field(default_factory=datetime.now, description="汇报时间戳")

    # 可选系统信息
    system_info: Optional[Dict] = Field(default=None, description="系统信息")


class TelemetryResponse(BasicResponse):
    """遥测响应"""

    data: Optional[TelemetryData] = Field(default=None, description="遥测数据")
