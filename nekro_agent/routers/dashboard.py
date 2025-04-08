import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from tortoise.functions import Avg, Count

from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_exec_code import DBExecCode, ExecStopType
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.user.deps import get_current_active_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


async def get_time_range(time_range: str = "day") -> datetime:
    now = datetime.now()
    if time_range == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if time_range == "week":
        start_time = now - timedelta(days=now.weekday())
        return start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    if time_range == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return now - timedelta(days=1)


@router.get("/overview", summary="获取仪表盘概览数据")
async def get_dashboard_overview(
    time_range: str = "day",
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    start_time = await get_time_range(time_range)

    total_messages = await DBChatMessage.filter(create_time__gte=start_time).count()
    active_sessions = await DBChatChannel.filter(update_time__gte=start_time).count()
    unique_users = await DBChatMessage.filter(create_time__gte=start_time).distinct().values_list("sender_id", flat=True)
    total_sandbox_calls = await DBExecCode.filter(create_time__gte=start_time).count()
    success_calls = await DBExecCode.filter(create_time__gte=start_time, success=True).count()
    failed_calls = total_sandbox_calls - success_calls
    success_rate = round(success_calls / total_sandbox_calls * 100, 2) if total_sandbox_calls > 0 else 0

    return Ret.success(
        msg="获取成功",
        data={
            "total_messages": total_messages,
            "active_sessions": active_sessions,
            "unique_users": len(unique_users),
            "total_sandbox_calls": total_sandbox_calls,
            "success_calls": success_calls,
            "failed_calls": failed_calls,
            "success_rate": success_rate,
        },
    )


@router.get("/trends", summary="获取趋势数据")
async def get_trends(
    metrics: str,
    time_range: str = "day",
    interval: str = "hour",
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取趋势数据"""
    # 计算时间范围
    now = datetime.now()
    if time_range == "day":
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if interval == "hour":
            intervals = 24
            delta = timedelta(hours=1)
        else:
            intervals = 24
            delta = timedelta(hours=1)
    elif time_range == "week":
        start_time = now - timedelta(days=now.weekday())
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        if interval == "day":
            intervals = 7
            delta = timedelta(days=1)
        else:
            intervals = 7 * 24
            delta = timedelta(hours=1)
    elif time_range == "month":
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if interval == "day":
            intervals = 30
            delta = timedelta(days=1)
        else:
            intervals = 30
            delta = timedelta(days=1)
    else:
        start_time = now - timedelta(days=1)
        intervals = 24
        delta = timedelta(hours=1)

    # 解析请求的指标
    metrics_list = metrics.split(",")

    # 准备结果数据
    result = []
    current_time = start_time

    for _ in range(intervals):
        next_time = current_time + delta
        data_point: Dict[str, Union[str, int, float]] = {"timestamp": current_time.isoformat()}

        # 查询各指标数据
        if "messages" in metrics_list:
            messages_count = await DBChatMessage.filter(create_time__gte=current_time, create_time__lt=next_time).count()
            data_point["messages"] = messages_count

        if any(m in metrics_list for m in ["sandbox_calls", "success_calls", "failed_calls", "success_rate"]):
            sandbox_calls = await DBExecCode.filter(create_time__gte=current_time, create_time__lt=next_time).count()

            if "sandbox_calls" in metrics_list:
                data_point["sandbox_calls"] = sandbox_calls

            if any(m in metrics_list for m in ["success_calls", "failed_calls", "success_rate"]):
                success_calls = await DBExecCode.filter(
                    create_time__gte=current_time,
                    create_time__lt=next_time,
                    success=True,
                ).count()

                if "success_calls" in metrics_list:
                    data_point["success_calls"] = success_calls

                if "failed_calls" in metrics_list:
                    data_point["failed_calls"] = sandbox_calls - success_calls

                if "success_rate" in metrics_list:
                    data_point["success_rate"] = round(success_calls / sandbox_calls * 100, 2) if sandbox_calls > 0 else 0

        result.append(data_point)
        current_time = next_time

    return Ret.success(
        msg="获取成功",
        data=result,
    )


@router.get("/ranking", summary="获取排名数据")
async def get_ranking(
    ranking_type: str,
    time_range: str = "day",
    limit: int = 10,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    start_time = await get_time_range(time_range)

    if ranking_type == "users":
        execs = await DBExecCode.filter(
            create_time__gte=start_time,
            trigger_user_id__not_in=[0, -1],  # 过滤掉系统触发的执行
        ).all()

        user_counts = {}
        for _exec in execs:
            user_id = _exec.trigger_user_id
            user_name = _exec.trigger_user_name

            if user_id not in user_counts:
                user_counts[user_id] = {
                    "id": user_id,
                    "name": user_name,
                    "value": 0,
                }

            user_counts[user_id]["value"] += 1

        result = sorted(user_counts.values(), key=lambda x: x["value"], reverse=True)[:limit]

        return Ret.success(
            msg="获取成功",
            data=result,
        )

    return Ret.success(
        msg="获取成功",
        data=[],
    )


@router.get("/stats/stream", summary="获取实时统计数据流")
async def get_stats_stream(
    granularity: int = Query(10, description="数据粒度（分钟）", ge=1, le=60),
    _current_user: DBUser = Depends(get_current_active_user),
):
    async def generate():
        try:
            # 初始化计数器
            last_message_count = await DBChatMessage.all().count()
            last_sandbox_count = await DBExecCode.all().count()
            last_success_count = await DBExecCode.filter(success=True).all().count()

            # 计算开始时间（当前时间减去50个粒度单位）
            start_time = datetime.now() - timedelta(minutes=granularity * 50)

            # 对齐到粒度的整点时间
            current_time = start_time.replace(
                minute=(start_time.minute // granularity) * granularity,
                second=0,
                microsecond=0,
            )

            # 发送历史数据（最多50个数据点）
            while current_time < datetime.now():
                next_time = current_time + timedelta(minutes=granularity)

                # 查询该时间段内的数据
                messages = await DBChatMessage.filter(
                    create_time__gte=current_time,
                    create_time__lt=next_time,
                ).count()

                sandbox_calls = await DBExecCode.filter(
                    create_time__gte=current_time,
                    create_time__lt=next_time,
                ).count()

                success_calls = await DBExecCode.filter(
                    create_time__gte=current_time,
                    create_time__lt=next_time,
                    success=True,
                ).count()

                execs = await DBExecCode.filter(
                    create_time__gte=current_time,
                    create_time__lt=next_time,
                ).all()

                avg_exec_time = sum(_exec.exec_time_ms for _exec in execs) / len(execs) if execs else 0

                # 发送数据（即使没有活动也发送，以保持图表连续性）
                yield json.dumps(
                    {
                        "timestamp": current_time.isoformat(),
                        "recent_messages": messages,
                        "recent_sandbox_calls": sandbox_calls,
                        "recent_success_calls": success_calls,
                        "recent_avg_exec_time": round(avg_exec_time, 2),
                    },
                )
                await asyncio.sleep(0.01)  # 短暂延迟，避免一次性发送太多数据

                current_time = next_time

            # 计算下一个对齐的时间点
            now = datetime.now()
            next_aligned_time = now.replace(
                minute=((now.minute // granularity) * granularity + granularity) % 60,
                second=0,
                microsecond=0,
            )
            # 如果下一个对齐时间的分钟小于当前分钟，说明跨小时了
            if next_aligned_time.minute < now.minute:
                next_aligned_time = next_aligned_time.replace(hour=next_aligned_time.hour + 1)

            # 实时监控循环
            while True:
                # 等待到下一个对齐的时间点
                wait_seconds = (next_aligned_time - datetime.now()).total_seconds()
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)

                # 查询从上次发送到现在的数据
                current_message_count = await DBChatMessage.all().count()
                current_sandbox_count = await DBExecCode.all().count()
                current_success_count = await DBExecCode.filter(success=True).all().count()

                recent_messages = current_message_count - last_message_count
                recent_sandbox_calls = current_sandbox_count - last_sandbox_count
                recent_success_calls = current_success_count - last_success_count

                # 查询最近一个粒度时间内的平均执行时间
                recent_execs = await DBExecCode.filter(
                    create_time__gte=datetime.now() - timedelta(minutes=granularity),
                ).all()
                recent_avg_exec_time = (
                    sum(_exec.exec_time_ms for _exec in recent_execs) / len(recent_execs) if recent_execs else 0
                )

                # 更新计数器
                last_message_count = current_message_count
                last_sandbox_count = current_sandbox_count
                last_success_count = current_success_count

                # 发送数据
                yield json.dumps(
                    {
                        "timestamp": next_aligned_time.isoformat(),
                        "recent_messages": recent_messages,
                        "recent_sandbox_calls": recent_sandbox_calls,
                        "recent_success_calls": recent_success_calls,
                        "recent_avg_exec_time": round(recent_avg_exec_time, 2),
                    },
                )

                # 计算下一个对齐的时间点
                next_aligned_time = next_aligned_time + timedelta(minutes=granularity)

        except Exception as e:
            print(f"Stream error: {e}")
            yield json.dumps({"error": str(e)})

    return EventSourceResponse(generate())


@router.get("/distributions", summary="获取所有分布数据")
async def get_distributions(
    time_range: str = "day",
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    start_time = await get_time_range(time_range)

    total_execs = await DBExecCode.filter(create_time__gte=start_time).count()
    stop_type_data = []

    if total_execs > 0:
        for stop_type in ExecStopType:
            count = await DBExecCode.filter(create_time__gte=start_time, stop_type=stop_type).count()
            if count > 0:
                stop_type_data.append(
                    {
                        "label": stop_type.value,
                        "value": count,
                        "percentage": round(count / total_execs * 100, 2),
                    },
                )

    total_messages = await DBChatMessage.filter(create_time__gte=start_time).count()
    message_type_data = []

    if total_messages > 0:
        group_count = await DBChatMessage.filter(create_time__gte=start_time, chat_type="group").count()
        private_count = total_messages - group_count

        message_type_data = [
            {
                "label": "群聊消息",
                "value": group_count,
                "percentage": round(group_count / total_messages * 100, 2),
            },
            {
                "label": "私聊消息",
                "value": private_count,
                "percentage": round(private_count / total_messages * 100, 2),
            },
        ]

    return Ret.success(
        msg="获取成功",
        data={
            "stop_type": stop_type_data,
            "message_type": message_type_data,
        },
    )
