from typing import Any, Dict, Optional, Union

import httpx

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.systems.cloud.exceptions import NekroCloudDisabled
from nekro_agent.systems.cloud.schemas.preset import (
    BasicResponse,
    PresetCreate,
    PresetCreateResponse,
    PresetCreateResponseData,
    PresetDetailResponse,
    PresetListResponse,
    PresetUpdate,
)


def get_client() -> httpx.AsyncClient:
    """获取 HTTP 客户端

    Returns:
        httpx.AsyncClient: HTTP 客户端
    """
    if not OsEnv.NEKRO_CLOUD_API_BASE_URL or not config.ENABLE_NEKRO_CLOUD:
        raise NekroCloudDisabled
    return httpx.AsyncClient(base_url=OsEnv.NEKRO_CLOUD_API_BASE_URL)


async def create_preset(preset_data: PresetCreate) -> PresetCreateResponse:
    """创建人设资源

    Args:
        preset_data: 人设数据

    Returns:
        PresetCreateResponse: 创建响应结果
    """
    try:
        async with get_client() as client:
            response = await client.post(
                url="/api/preset",
                json={
                    "name": preset_data.name,
                    "title": preset_data.title,
                    "avatar": preset_data.avatar,
                    "content": preset_data.content,
                    "description": preset_data.description,
                    "tags": preset_data.tags,
                    "author": preset_data.author,
                    "extData": preset_data.ext_data,
                    "isSfw": preset_data.is_sfw,
                    "instanceId": preset_data.instance_id,
                },
            )
            response.raise_for_status()
            return PresetCreateResponse(**response.json())
    except NekroCloudDisabled:
        return PresetCreateResponse(success=False, error="Nekro Cloud 未启用", data=None)
    except Exception as e:
        logger.error(f"创建人设资源发生错误: {e}")
        return PresetCreateResponse(success=False, error=f"创建人设资源失败: {e!s}", data=None)


async def update_preset(preset_id: str, preset_data: PresetUpdate) -> BasicResponse:
    """更新人设资源

    Args:
        preset_id: 人设ID
        preset_data: 更新的人设数据

    Returns:
        BasicResponse: 响应结果
    """
    try:
        async with get_client() as client:
            response = await client.put(
                url=f"/api/preset/{preset_id}",
                json={
                    "name": preset_data.name,
                    "title": preset_data.title,
                    "avatar": preset_data.avatar,
                    "content": preset_data.content,
                    "description": preset_data.description,
                    "tags": preset_data.tags,
                    "author": preset_data.author,
                    "extData": preset_data.ext_data,
                    "isSfw": preset_data.is_sfw,
                    "instanceId": preset_data.instance_id,
                },
            )
            response.raise_for_status()
            return BasicResponse(**response.json())
    except NekroCloudDisabled:
        return BasicResponse(success=False, error="Nekro Cloud 未启用")
    except Exception as e:
        logger.error(f"更新人设资源发生错误: {e}")
        return BasicResponse(success=False, error=f"更新人设资源失败: {e!s}")


async def delete_preset(preset_id: str, instance_id: str) -> BasicResponse:
    """删除人设资源

    Args:
        preset_id: 人设ID
        instance_id: 实例ID

    Returns:
        BasicResponse: 响应结果
    """
    try:
        async with get_client() as client:
            response = await client.delete(
                url=f"/api/preset/{preset_id}",
                params={"instanceId": instance_id},
            )
            response.raise_for_status()
            return BasicResponse(**response.json())
    except NekroCloudDisabled:
        return BasicResponse(success=False, error="Nekro Cloud 未启用")
    except Exception as e:
        logger.error(f"删除人设资源发生错误: {e}")
        return BasicResponse(success=False, error=f"删除人设资源失败: {e!s}")


async def get_preset(preset_id: str) -> PresetDetailResponse:
    """获取人设详情

    Args:
        preset_id: 人设ID

    Returns:
        PresetDetailResponse: 人设详情响应
    """
    try:
        async with get_client() as client:
            response = await client.get(url=f"/api/preset/{preset_id}")
            response.raise_for_status()
            return PresetDetailResponse(**response.json())
    except NekroCloudDisabled:
        return PresetDetailResponse(success=False, error="Nekro Cloud 未启用", data=None)
    except Exception as e:
        logger.error(f"获取人设详情发生错误: {e}")
        return PresetDetailResponse(success=False, error=f"获取人设详情失败: {e!s}", data=None)


async def list_presets(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    tag: Optional[str] = None,
) -> PresetListResponse:
    """查询人设列表

    Args:
        page: 页码，默认1
        page_size: 每页数量，默认10
        keyword: 搜索关键词
        tag: 按标签筛选
        allow_nsfw: 是否允许返回非安全内容

    Returns:
        PresetListResponse: 人设列表响应
    """
    try:
        params: Dict[str, Union[str, int, bool]] = {
            "page": page,
            "pageSize": page_size,
        }

        if keyword:
            params["keyword"] = keyword
        if tag:
            params["tag"] = tag
        if not config.ENSURE_SFW_CONTENT:
            params["allowNsfw"] = True

        async with get_client() as client:
            response = await client.get(
                url="/api/preset",
                params=params,
            )
            response.raise_for_status()
            return PresetListResponse(**response.json())
    except NekroCloudDisabled:
        return PresetListResponse(success=False, error="Nekro Cloud 未启用", data=None)
    except Exception as e:
        logger.error(f"查询人设列表发生错误: {e}")
        return PresetListResponse(success=False, error=f"查询人设列表失败: {e!s}", data=None)
