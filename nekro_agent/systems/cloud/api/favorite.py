from typing import Dict, Optional, Union

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_preset import DBPreset
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.systems.cloud.schemas.favorite import (
    FavoriteCreateRequest,
    FavoriteCreateResponse,
    FavoriteDeleteResponse,
    FavoriteListResponse,
)

from .client import get_client

logger = get_sub_logger("cloud_api")

FAVORITE_API = "/api/v2/favorite"


async def add_favorite(target_type: str, target_id: str) -> FavoriteCreateResponse:
    """添加收藏

    Args:
        target_type: 目标类型，可选 "plugin" 或 "preset"
        target_id: 目标资源ID

    Returns:
        FavoriteCreateResponse: 创建响应结果
    """
    try:
        async with get_client(require_auth=True) as client:
            payload = FavoriteCreateRequest(
                target_type=target_type,
                target_id=target_id,
            ).model_dump(by_alias=True, exclude_none=True)
            response = await client.post(
                url=FAVORITE_API,
                json=payload,
            )
            response.raise_for_status()
            logger.debug(f"添加收藏响应数据: {response.json()}")
            return FavoriteCreateResponse(**response.json())
    except Exception as e:
        logger.exception(f"添加收藏发生错误: {e}")
        return FavoriteCreateResponse.process_exception(e)


async def remove_favorite(target_type: str, target_id: str) -> FavoriteDeleteResponse:
    """取消收藏

    Args:
        target_type: 目标类型，可选 "plugin" 或 "preset"
        target_id: 目标资源ID

    Returns:
        FavoriteDeleteResponse: 删除响应结果
    """
    try:
        async with get_client(require_auth=True) as client:
            response = await client.delete(
                url=FAVORITE_API,
                params={
                    "targetType": target_type,
                    "targetId": target_id,
                },
            )
            response.raise_for_status()
            logger.debug(f"取消收藏响应数据: {response.json()}")
            return FavoriteDeleteResponse(**response.json())
    except Exception as e:
        logger.exception(f"取消收藏发生错误: {e}")
        return FavoriteDeleteResponse.process_exception(e)


async def list_favorites(
    page: int = 1,
    page_size: int = 10,
    target_type: Optional[str] = None,
) -> FavoriteListResponse:
    """获取收藏列表

    Args:
        page: 页码，默认1
        page_size: 每页数量，默认10，最大1000
        target_type: 按类型筛选，可选 "plugin" 或 "preset"

    Returns:
        FavoriteListResponse: 收藏列表响应
    """
    try:
        # 云端API限制每页最大32条，这里聚合云端分页后再切成本地所需分页
        cloud_max_page_size = 32
        all_items = []
        current_page = 1
        total = 0
        start_index = (page - 1) * page_size
        end_index = start_index + page_size

        while len(all_items) < end_index:
            params: Dict[str, Union[str, int]] = {
                "page": current_page,
                "pageSize": cloud_max_page_size,
            }

            if target_type:
                params["targetType"] = target_type

            async with get_client(require_auth=True) as client:
                response = await client.get(
                    url=FAVORITE_API,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            if not data.get("success") or not data.get("data"):
                break

            page_items = data["data"].get("items", [])
            all_items.extend(page_items)
            total = data["data"].get("total", 0)

            # 如果已经获取完所有数据或当前页没有数据，则停止
            if len(page_items) < params["pageSize"] or len(all_items) >= total:
                break

            current_page += 1

        page_items = all_items[start_index:end_index]

        # 获取本地已安装的云端插件和已下载云端人设的远程ID列表
        local_plugin_ids = plugin_collector.package_data.get_remote_ids()
        preset_remote_ids = [
            item.get("targetId")
            for item in page_items
            if item.get("targetType") == "preset" and item.get("targetId")
        ]
        local_preset_remote_ids = set()
        if preset_remote_ids:
            local_presets = await DBPreset.filter(remote_id__in=preset_remote_ids).values("remote_id")
            local_preset_remote_ids = {
                preset["remote_id"] for preset in local_presets if preset.get("remote_id")
            }

        # 为每个收藏项补充本地安装状态
        for item in page_items:
            resource = item.get("resource")
            if not isinstance(resource, dict):
                continue

            if item.get("targetType") == "plugin":
                target_id = item.get("targetId")
                resource["isLocal"] = target_id in local_plugin_ids if target_id else False
            else:
                target_id = item.get("targetId")
                resource["isLocal"] = target_id in local_preset_remote_ids if target_id else False

        # 构造响应数据
        from nekro_agent.systems.cloud.schemas.favorite import FavoriteItem, FavoriteListData

        return FavoriteListResponse(
            success=True,
            data=FavoriteListData(
                items=[FavoriteItem(**item) for item in page_items],
                total=total,
                page=page,
                page_size=page_size,
                total_pages=(total + page_size - 1) // page_size if page_size > 0 else 1,
            ),
        )
    except Exception as e:
        logger.exception(f"获取收藏列表发生错误: {e}")
        return FavoriteListResponse.process_exception(e)
