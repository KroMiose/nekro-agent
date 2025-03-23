import asyncio
import json
import random
from datetime import datetime
from pathlib import Path

import httpx

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.systems.cloud.collector import prepare_telemetry_data
from nekro_agent.systems.cloud.schema import TelemetryData, TelemetryResponse


def get_client() -> httpx.AsyncClient:
    """获取 HTTP 客户端

    Returns:
        httpx.AsyncClient: HTTP 客户端
    """
    if not OsEnv.NEKRO_CLOUD_API_BASE_URL or not config.ENABLE_NEKRO_CLOUD:
        raise NekroCloudDisabled
    return httpx.AsyncClient(base_url=OsEnv.NEKRO_CLOUD_API_BASE_URL)


async def send_telemetry_data(telemetry_data: TelemetryData) -> TelemetryResponse:
    """发送遥测数据

    Args:
        telemetry_data: 遥测数据

    Returns:
        TelemetryResponse: 响应结果
    """
    async with get_client() as client:
        response = await client.post(
            url="/api/telemetry",
            json=telemetry_data.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        return TelemetryResponse(**response.json())


async def send_telemetry_report(hour_start: datetime, hour_end: datetime) -> TelemetryResponse:
    """发送遥测报告

    Args:
        hour_start: 小时开始时间
        hour_end: 小时结束时间

    Returns:
        TelemetryResponse: 遥测响应
    """
    try:
        # 准备遥测数据
        telemetry_data = await prepare_telemetry_data(hour_start, hour_end)
        # temp_path = Path(".temp/telemetry_data.json")
        # temp_path.parent.mkdir(parents=True, exist_ok=True)
        # temp_path.write_bytes(
        #     json.dumps(telemetry_data.model_dump(mode="json", exclude_none=True)).encode("utf-8"),
        # )

        # 发送遥测数据
        for _ in range(10):
            response = await send_telemetry_data(telemetry_data)
            if response.success:
                break
            await asyncio.sleep(random.uniform(3, 10))
        if not response.success:
            logger.warning(f"与 Nekro Cloud 通信发生错误: {response.message}")
    except NekroCloudDisabled:
        return TelemetryResponse(success=False, message="Nekro Cloud 未启用")
    except Exception as e:
        logger.error(f"与 Nekro Cloud 通信发生错误: {e}")
        return TelemetryResponse(success=False, message=f"发送遥测报告失败: {e!s}")
    else:
        return response


class NekroCloudDisabled(Exception):
    """Nekro Cloud 未启用异常"""

    def __init__(self, message: str = "Nekro Cloud 未启用"):
        self.message = message
        super().__init__(self.message)
