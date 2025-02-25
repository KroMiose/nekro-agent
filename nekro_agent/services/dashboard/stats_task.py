import asyncio
from datetime import datetime, timedelta

from tortoise.expressions import Q
from tortoise.functions import Count, Avg, Sum

from nekro_agent.core.logger import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_dashboard_stats import DBDashboardStats
from nekro_agent.models.db_exec_code import DBExecCode, ExecStopType


async def generate_hourly_stats():
    """生成每小时统计数据"""
    now = datetime.now()
    hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    hour_end = hour_start + timedelta(hours=1)

    logger.info(f"开始生成 {hour_start} 到 {hour_end} 的小时统计数据")

    try:
        # 检查是否已有该小时的统计
        existing = await DBDashboardStats.get_or_none(stat_time=hour_start, time_span="hour")

        if existing:
            logger.info(f"{hour_start} 小时统计数据已存在，跳过")
            return

        # 计算该小时内的消息统计
        total_messages = await DBChatMessage.filter(
            send_timestamp__gte=int(hour_start.timestamp()), send_timestamp__lt=int(hour_end.timestamp())
        ).count()

        # 活跃会话数
        active_sessions = await DBChatChannel.filter(update_time__gte=hour_start, update_time__lt=hour_end).count()

        # 独立用户数
        unique_users = (
            await DBChatMessage.filter(
                send_timestamp__gte=int(hour_start.timestamp()), send_timestamp__lt=int(hour_end.timestamp())
            )
            .distinct()
            .values_list("sender_id", flat=True)
        )

        # 消息类型分布
        messages = await DBChatMessage.filter(
            send_timestamp__gte=int(hour_start.timestamp()), send_timestamp__lt=int(hour_end.timestamp())
        ).all()

        group_messages = 0
        private_messages = 0

        for msg in messages:
            if "group" in msg.chat_key:
                group_messages += 1
            else:
                private_messages += 1

        # 沙盒执行统计
        total_sandbox_calls = await DBExecCode.filter(create_time__gte=hour_start, create_time__lt=hour_end).count()

        success_sandbox_calls = await DBExecCode.filter(
            create_time__gte=hour_start, create_time__lt=hour_end, success=True
        ).count()

        failed_sandbox_calls = await DBExecCode.filter(
            create_time__gte=hour_start, create_time__lt=hour_end, success=False
        ).count()

        agent_sandbox_calls = await DBExecCode.filter(
            create_time__gte=hour_start, create_time__lt=hour_end, stop_type=ExecStopType.AGENT
        ).count()

        # 平均执行时间和最大执行时间
        exec_time_sum = 0
        exec_count = 0
        generation_time_sum = 0
        max_exec_time_ms = 0
        max_generation_time_ms = 0

        exec_records = await DBExecCode.filter(create_time__gte=hour_start, create_time__lt=hour_end).all()

        for record in exec_records:
            if record.exec_time_ms is not None and record.exec_time_ms > 0:
                exec_time_sum += record.exec_time_ms
                exec_count += 1
                # 更新最大执行时间
                max_exec_time_ms = max(max_exec_time_ms, record.exec_time_ms)

            if record.generation_time_ms is not None and record.generation_time_ms > 0:
                generation_time_sum += record.generation_time_ms
                # 更新最大生成时间
                max_generation_time_ms = max(max_generation_time_ms, record.generation_time_ms)

        avg_exec_time_ms = exec_time_sum / exec_count if exec_count > 0 else 0
        avg_generation_time_ms = generation_time_sum / exec_count if exec_count > 0 else 0

        # 最活跃用户
        user_counts = {}
        for msg in messages:
            user_id = msg.sender_id
            if user_id not in user_counts:
                user_counts[user_id] = {"id": user_id, "name": msg.sender_real_nickname, "count": 0}
            user_counts[user_id]["count"] += 1

        most_active_users = sorted(list(user_counts.values()), key=lambda x: x["count"], reverse=True)[:10]  # 取前10个

        # 最活跃群组
        group_counts = {}
        for msg in messages:
            if "group" in msg.chat_key:
                group_id = msg.chat_key
                if group_id not in group_counts:
                    group_counts[group_id] = {"id": group_id, "name": f"群 {group_id.split('_')[1]}", "count": 0}
                group_counts[group_id]["count"] += 1

        most_active_groups = sorted(list(group_counts.values()), key=lambda x: x["count"], reverse=True)[:10]  # 取前10个

        # 存储统计结果
        await DBDashboardStats.create(
            stat_time=hour_start,
            time_span="hour",
            total_messages=total_messages,
            active_sessions=active_sessions,
            unique_users=len(unique_users),
            total_sandbox_calls=total_sandbox_calls,
            success_sandbox_calls=success_sandbox_calls,
            failed_sandbox_calls=failed_sandbox_calls,
            agent_sandbox_calls=agent_sandbox_calls,
            avg_exec_time_ms=round(avg_exec_time_ms, 2),
            max_exec_time_ms=round(max_exec_time_ms, 2),
            avg_generation_time_ms=round(avg_generation_time_ms, 2),
            max_generation_time_ms=round(max_generation_time_ms, 2),
            group_messages=group_messages,
            private_messages=private_messages,
            most_active_users=most_active_users,
            most_active_groups=most_active_groups,
            report_status=0,  # 默认未报告
        )

        logger.info(f"生成 {hour_start} 小时统计数据完成")

    except Exception as e:
        logger.error(f"生成小时统计数据出错: {e}")


async def generate_daily_stats():
    """生成每日统计数据"""
    now = datetime.now()
    day_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    logger.info(f"开始生成 {day_start.date()} 的日统计数据")

    try:
        # 检查是否已有该日的统计
        existing = await DBDashboardStats.get_or_none(stat_time=day_start, time_span="day")

        if existing:
            logger.info(f"{day_start.date()} 日统计数据已存在，跳过")
            return

        # 可以直接从小时统计汇总，也可以重新计算
        # 这里选择从小时统计汇总，确保数据一致性

        hourly_stats = await DBDashboardStats.filter(stat_time__gte=day_start, stat_time__lt=day_end, time_span="hour").all()

        if not hourly_stats:
            logger.warning(f"{day_start.date()} 没有小时统计数据，无法生成日统计")
            return

        # 初始化聚合数据
        total_messages = 0
        active_sessions = 0
        unique_users_set = set()
        total_sandbox_calls = 0
        success_sandbox_calls = 0
        failed_sandbox_calls = 0
        agent_sandbox_calls = 0
        exec_time_values = []
        generation_time_values = []
        max_exec_time_ms = 0
        max_generation_time_ms = 0
        group_messages = 0
        private_messages = 0

        # 用户活跃度统计
        user_counts = {}
        group_counts = {}

        # 汇总小时数据
        for stat in hourly_stats:
            total_messages += stat.total_messages
            active_sessions = max(active_sessions, stat.active_sessions)  # 取最大值

            # 合并独立用户
            for user in stat.most_active_users:
                user_id = user["id"]
                unique_users_set.add(user_id)

                if user_id not in user_counts:
                    user_counts[user_id] = {"id": user_id, "name": user["name"], "count": 0}
                user_counts[user_id]["count"] += user["count"]

            # 合并群组统计
            for group in stat.most_active_groups:
                group_id = group["id"]
                if group_id not in group_counts:
                    group_counts[group_id] = {"id": group_id, "name": group["name"], "count": 0}
                group_counts[group_id]["count"] += group["count"]

            # 累加其他统计
            total_sandbox_calls += stat.total_sandbox_calls
            success_sandbox_calls += stat.success_sandbox_calls
            failed_sandbox_calls += stat.failed_sandbox_calls
            agent_sandbox_calls += stat.agent_sandbox_calls

            # 加权平均执行时间
            if stat.total_sandbox_calls > 0:
                exec_time_values.append((stat.avg_exec_time_ms, stat.total_sandbox_calls))
                generation_time_values.append((stat.avg_generation_time_ms, stat.total_sandbox_calls))
            
            # 更新最大执行时间和最大生成时间
            max_exec_time_ms = max(max_exec_time_ms, stat.max_exec_time_ms)
            max_generation_time_ms = max(max_generation_time_ms, stat.max_generation_time_ms)

            # 消息类型
            group_messages += stat.group_messages
            private_messages += stat.private_messages

        # 计算加权平均执行时间
        avg_exec_time_ms = 0
        if exec_time_values:
            total_weight = sum(weight for _, weight in exec_time_values)
            if total_weight > 0:
                avg_exec_time_ms = sum(value * weight for value, weight in exec_time_values) / total_weight

        avg_generation_time_ms = 0
        if generation_time_values:
            total_weight = sum(weight for _, weight in generation_time_values)
            if total_weight > 0:
                avg_generation_time_ms = sum(value * weight for value, weight in generation_time_values) / total_weight

        # 最活跃用户和群组
        most_active_users = sorted(list(user_counts.values()), key=lambda x: x["count"], reverse=True)[:10]

        most_active_groups = sorted(list(group_counts.values()), key=lambda x: x["count"], reverse=True)[:10]

        # 存储日统计结果
        await DBDashboardStats.create(
            stat_time=day_start,
            time_span="day",
            total_messages=total_messages,
            active_sessions=active_sessions,
            unique_users=len(unique_users_set),
            total_sandbox_calls=total_sandbox_calls,
            success_sandbox_calls=success_sandbox_calls,
            failed_sandbox_calls=failed_sandbox_calls,
            agent_sandbox_calls=agent_sandbox_calls,
            avg_exec_time_ms=round(avg_exec_time_ms, 2),
            max_exec_time_ms=round(max_exec_time_ms, 2),
            avg_generation_time_ms=round(avg_generation_time_ms, 2),
            max_generation_time_ms=round(max_generation_time_ms, 2),
            group_messages=group_messages,
            private_messages=private_messages,
            most_active_users=most_active_users,
            most_active_groups=most_active_groups,
            report_status=0,  # 默认未报告
        )

        logger.info(f"生成 {day_start.date()} 日统计数据完成")

    except Exception as e:
        logger.error(f"生成日统计数据出错: {e}")


async def stats_task_runner():
    """统计任务运行器"""
    while True:
        try:
            # 获取当前时间
            now = datetime.now()

            # 执行小时统计任务
            if now.minute == 5:  # 每小时5分时执行上一小时统计
                await generate_hourly_stats()

            # 执行日统计任务
            if now.hour == 1 and now.minute == 5:  # 每天凌晨1:05执行前一日统计
                await generate_daily_stats()

            # 等待下一分钟
            next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            sleep_time = (next_minute - now).total_seconds()
            await asyncio.sleep(sleep_time)

        except Exception as e:
            logger.error(f"统计任务出错: {e}")
            await asyncio.sleep(60)  # 出错后等待1分钟
