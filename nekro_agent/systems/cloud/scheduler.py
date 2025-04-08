import asyncio
import random
from datetime import datetime, timedelta

from nekro_agent.core.logger import logger
from nekro_agent.systems.cloud.api.telemetry import send_telemetry_report


async def telemetry_task():
    """遥测任务 - 定时收集和上报遥测数据"""
    while True:
        try:
            # 获取当前时间和上一个整点时间
            now = datetime.now()
            current_hour = now.replace(minute=0, second=0, microsecond=0)

            if now.minute < 5:
                # 刚过整点，需要等待随机时间再上报上一个小时的数据
                prev_hour = current_hour - timedelta(hours=1)
                delay_seconds = random.randint(1, 300)  # 随机延迟0-5分钟
                await asyncio.sleep(delay_seconds)

                # 上报上一个小时的数据
                hour_start = prev_hour
                hour_end = current_hour

                response = await send_telemetry_report(hour_start, hour_end)
                if response.success:
                    logger.debug(f"遥测数据上报成功: {hour_start} - {hour_end}")
                else:
                    logger.warning(f"与 Nekro Cloud 通信发生错误: {response.message}")

            # 计算到下一个整点的等待时间
            next_hour = current_hour + timedelta(hours=1)
            wait_seconds = (next_hour - datetime.now()).total_seconds()

            # 如果错过了整点，则等到下一个整点
            if wait_seconds < 0:
                next_hour = now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0)
                wait_seconds = (next_hour - now).total_seconds()

            logger.debug(f"等待到下一个整点触发遥测: {next_hour}, 等待 {wait_seconds} 秒")
            await asyncio.sleep(wait_seconds)

        except Exception as e:
            logger.error(f"与 Nekro Cloud 通信发生错误: {e}")
            await asyncio.sleep(60)  # 发生异常，等待一分钟后重试


def start_telemetry_task():
    """启动遥测任务"""
    asyncio.create_task(telemetry_task())
