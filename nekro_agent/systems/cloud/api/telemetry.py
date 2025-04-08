import asyncio
import json
import random
import time
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.systems.cloud.collector import prepare_telemetry_data
from nekro_agent.systems.cloud.exceptions import NekroCloudDisabled
from nekro_agent.systems.cloud.schemas.telemetry import TelemetryData, TelemetryResponse

# 内存缓存
_CACHE: Dict[str, Dict[str, Any]] = {"community_stats": {"data": None, "expires_at": 0}}


def get_client() -> httpx.AsyncClient:
    """获取 HTTP 客户端

    Returns:
        httpx.AsyncClient: HTTP 客户端
    """
    if not OsEnv.NEKRO_CLOUD_API_BASE_URL or not config.ENABLE_NEKRO_CLOUD:
        raise NekroCloudDisabled
    return httpx.AsyncClient(base_url=OsEnv.NEKRO_CLOUD_API_BASE_URL)


async def _send_telemetry_data(telemetry_data: TelemetryData) -> TelemetryResponse:
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

        # 发送遥测数据
        for _ in range(10):
            response = await _send_telemetry_data(telemetry_data)
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


async def get_community_stats(force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """获取社区统计数据，带有1小时缓存

    Args:
        force_refresh: 是否强制刷新缓存

    Returns:
        Optional[Dict[str, Any]]: 社区统计数据，如果失败则返回 None
    """
    cache = _CACHE["community_stats"]
    current_time = time.time()

    # 检查缓存是否有效且未过期
    if not force_refresh and cache["data"] is not None and current_time < cache["expires_at"]:
        logger.debug("使用缓存的社区统计数据")
        return cache["data"]

    try:
        logger.debug("从社区获取统计数据")
        async with get_client() as client:
            response = await client.get("/api/telemetry/community-stats")
            response.raise_for_status()
            stats = response.json()

            # 更新缓存，设置1小时有效期
            _CACHE["community_stats"]["data"] = stats
            _CACHE["community_stats"]["expires_at"] = current_time + 3600  # 1小时 = 3600秒

            return stats
    except NekroCloudDisabled:
        logger.warning("Nekro Cloud 未启用，无法获取社区统计数据")
        return None
    except Exception as e:
        logger.error(f"获取社区统计数据失败: {e}")
        return None
