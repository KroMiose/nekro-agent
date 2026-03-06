import asyncio
import random
from datetime import datetime, timedelta

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.systems.cloud.api.telemetry import send_telemetry_report

logger = get_sub_logger("cloud_api")

async def telemetry_task():
    """遥测任务 - 每5分钟收集和上报遥测数据"""
    while True:
        try:
            now = datetime.now()
            # 以当前5分钟区间的起点为统计窗口
            interval_start = now.replace(second=0, microsecond=0) - timedelta(minutes=5)
            interval_end = now.replace(second=0, microsecond=0)

            # 随机延迟 0-30 秒，避免所有实例同时上报
            await asyncio.sleep(random.randint(1, 30))

            response = await send_telemetry_report(interval_start, interval_end)
            if response.success:
                logger.debug(f"遥测数据上报成功: {interval_start} - {interval_end}")
                if response.announcement_updated_at:
                    logger.debug(f"公告最后更新时间: {response.announcement_updated_at}")
            else:
                logger.warning(f"与 Nekro Cloud 通信发生错误: {response.message}")

            # 等待5分钟
            await asyncio.sleep(300)

        except Exception as e:
            logger.error(f"与 Nekro Cloud 通信发生错误: {e}")
            await asyncio.sleep(60)  # 发生异常，等待一分钟后重试


def start_telemetry_task():
    """启动遥测任务"""
    asyncio.create_task(telemetry_task())
