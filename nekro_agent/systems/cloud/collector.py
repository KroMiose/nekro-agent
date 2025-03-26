import platform
import socket
import time
from datetime import datetime

from tortoise.functions import Avg, Max

from nekro_agent.core.logger import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_exec_code import DBExecCode, ExecStopType
from nekro_agent.models.db_user import DBUser
from nekro_agent.systems.cloud.schemas.telemetry import (
    ExecStopTypeStat,
    TelemetryData,
    TelemetryStats,
    TelemetryStatsType,
)
from nekro_agent.tools.common_util import get_app_version
from nekro_agent.tools.telemetry_util import (
    generate_instance_id,
    get_system_info,
    is_running_in_docker,
)


async def collect_total_stats() -> TelemetryStats:
    """收集总体统计数据

    Returns:
        TelemetryStats: 总体统计数据
    """
    total_users = await DBUser.all().count()
    total_sessions = await DBChatChannel.all().count()
    total_messages = await DBChatMessage.all().count()
    total_sandbox_calls = await DBExecCode.all().count()

    # 收集所有停止类型的统计
    stop_type_stats = []
    for stop_type in ExecStopType:
        count = await DBExecCode.filter(stop_type=stop_type).count()
        if count > 0:
            stop_type_stats.append(ExecStopTypeStat(stop_type=stop_type, count=count))

    # 收集消息类型分布
    group_messages = await DBChatMessage.filter(chat_type="group").count()
    private_messages = await DBChatMessage.filter(chat_type="friend").count()

    # 收集性能指标
    avg_exec_time = await DBExecCode.all().annotate(avg=Avg("exec_time_ms")).values("avg")
    max_exec_time = await DBExecCode.all().annotate(max=Max("exec_time_ms")).values("max")

    avg_exec_time_ms = avg_exec_time[0]["avg"] if avg_exec_time and avg_exec_time[0]["avg"] else 0
    max_exec_time_ms = max_exec_time[0]["max"] if max_exec_time and max_exec_time[0]["max"] else 0

    return TelemetryStats(
        stats_type=TelemetryStatsType.TOTAL,
        total_users=total_users,
        total_sessions=total_sessions,
        total_messages=total_messages,
        total_sandbox_calls=total_sandbox_calls,
        stop_type_stats=stop_type_stats,
        group_messages=group_messages,
        private_messages=private_messages,
        avg_exec_time_ms=avg_exec_time_ms,
        max_exec_time_ms=max_exec_time_ms,
    )


async def collect_hourly_stats(hour_start: datetime, hour_end: datetime) -> TelemetryStats:
    """收集指定小时的统计数据

    Args:
        hour_start: 小时开始时间
        hour_end: 小时结束时间

    Returns:
        TelemetryStats: 小时统计数据
    """
    # 获取活跃用户和会话数
    active_users = len(
        await DBChatMessage.filter(
            create_time__gte=hour_start,
            create_time__lt=hour_end,
        )
        .distinct()
        .values_list("sender_id", flat=True),
    )

    active_sessions = await DBChatChannel.filter(
        update_time__gte=hour_start,
        update_time__lt=hour_end,
    ).count()

    # 获取消息数和沙盒执行次数
    hourly_messages = await DBChatMessage.filter(
        create_time__gte=hour_start,
        create_time__lt=hour_end,
    ).count()

    hourly_sandbox_calls = await DBExecCode.filter(
        create_time__gte=hour_start,
        create_time__lt=hour_end,
    ).count()

    # 收集停止类型统计
    stop_type_stats = []
    for stop_type in ExecStopType:
        count = await DBExecCode.filter(
            create_time__gte=hour_start,
            create_time__lt=hour_end,
            stop_type=stop_type,
        ).count()
        if count > 0:
            stop_type_stats.append(ExecStopTypeStat(stop_type=stop_type, count=count))

    # 收集消息类型分布
    group_messages = await DBChatMessage.filter(
        create_time__gte=hour_start,
        create_time__lt=hour_end,
        chat_type="group",
    ).count()

    private_messages = await DBChatMessage.filter(
        create_time__gte=hour_start,
        create_time__lt=hour_end,
        chat_type="friend",
    ).count()

    # 收集性能指标
    hourly_execs = DBExecCode.filter(create_time__gte=hour_start, create_time__lt=hour_end)
    avg_exec_time = await hourly_execs.annotate(avg=Avg("exec_time_ms")).values("avg")
    max_exec_time = await hourly_execs.annotate(max=Max("exec_time_ms")).values("max")

    avg_exec_time_ms = avg_exec_time[0]["avg"] if avg_exec_time and avg_exec_time[0]["avg"] else 0
    max_exec_time_ms = max_exec_time[0]["max"] if max_exec_time and max_exec_time[0]["max"] else 0

    # 计算小时时间戳（整点时间戳）
    hour_timestamp = int(time.mktime(hour_start.timetuple()))

    return TelemetryStats(
        stats_type=TelemetryStatsType.HOURLY,
        total_users=0,  # 这里不关注总用户数
        total_sessions=0,  # 这里不关注总会话数
        total_messages=hourly_messages,
        total_sandbox_calls=hourly_sandbox_calls,
        stop_type_stats=stop_type_stats,
        active_users=active_users,
        active_sessions=active_sessions,
        group_messages=group_messages,
        private_messages=private_messages,
        avg_exec_time_ms=avg_exec_time_ms,
        max_exec_time_ms=max_exec_time_ms,
        stats_start_time=hour_start,
        stats_end_time=hour_end,
        hour_timestamp=hour_timestamp,
    )


async def prepare_telemetry_data(hour_start: datetime, hour_end: datetime) -> TelemetryData:
    """准备遥测数据

    Args:
        hour_start: 小时开始时间
        hour_end: 小时结束时间

    Returns:
        TelemetryData: 遥测数据
    """
    total_stats = await collect_total_stats()
    hourly_stats = await collect_hourly_stats(hour_start, hour_end)

    app_version = get_app_version()
    is_docker = is_running_in_docker()
    instance_id = generate_instance_id()

    # 添加基本系统信息
    system_info = get_system_info()

    return TelemetryData(
        instance_id=instance_id,
        total_stats=total_stats,
        hourly_stats=hourly_stats,
        app_version=app_version,
        is_docker=is_docker,
        report_time=datetime.now(),
        system_info=system_info,
    )
