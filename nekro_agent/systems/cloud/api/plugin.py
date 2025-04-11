from typing import Any, Dict, Optional, Union

from fastapi import HTTPException

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.systems.cloud.schemas.plugin import (
    BasicResponse,
    PluginCreate,
    PluginCreateResponse,
    PluginDetailResponse,
    PluginListResponse,
    UserPluginListResponse,
)

from .client import get_client


async def create_plugin(plugin_data: PluginCreate) -> PluginCreateResponse:
    """创建插件资源

    Args:
        plugin_data: 插件数据

    Returns:
        PluginCreateResponse: 创建响应结果
    """
    try:
        async with get_client(require_auth=True) as client:
            response = await client.post(
                url="/api/plugin",
                json={
                    "name": plugin_data.name,
                    "moduleName": plugin_data.moduleName,
                    "description": plugin_data.description,
                    "author": plugin_data.author,
                    "hasWebhook": plugin_data.hasWebhook,
                    "homepageUrl": plugin_data.homepageUrl,
                    "githubUrl": plugin_data.githubUrl,
                    "cloneUrl": plugin_data.cloneUrl,
                    "licenseType": plugin_data.licenseType,
                    "isSfw": plugin_data.isSfw,
                    "icon": plugin_data.icon,
                },
            )
            response.raise_for_status()
            return PluginCreateResponse(**response.json())
    except Exception as e:
        logger.error(f"创建插件资源发生错误: {e}")
        return PluginCreateResponse.process_exception(e)


async def update_plugin(module_name: str, updates: Dict[str, Any]) -> BasicResponse:
    """更新插件资源

    Args:
        module_name: 插件模块名
        updates: 更新的插件数据

    Returns:
        BasicResponse: 响应结果
    """
    try:
        async with get_client(require_auth=True) as client:
            response = await client.put(
                url=f"/api/plugin/{module_name}",
                json=updates,
            )
            response.raise_for_status()
            return BasicResponse(**response.json())
    except Exception as e:
        logger.error(f"更新插件资源发生错误: {e}")
        return BasicResponse.process_exception(e)


async def delete_plugin(module_name: str) -> BasicResponse:
    """删除插件资源

    Args:
        module_name: 插件模块名

    Returns:
        BasicResponse: 响应结果
    """
    try:
        async with get_client(require_auth=True) as client:
            response = await client.delete(
                url=f"/api/plugin/{module_name}",
            )
            response.raise_for_status()
            return BasicResponse(**response.json())
    except Exception as e:
        logger.error(f"删除插件资源发生错误: {e}")
        return BasicResponse.process_exception(e)


async def get_plugin(module_name: str) -> PluginDetailResponse:
    """获取插件详情

    Args:
        module_name: 插件模块名

    Returns:
        PluginDetailResponse: 插件详情响应
    """
    try:
        async with get_client() as client:
            response = await client.get(url=f"/api/plugin/{module_name}")
            response.raise_for_status()
            data = response.json()
            return PluginDetailResponse(**data)
    except Exception as e:
        logger.error(f"获取插件详情发生错误: {e}")
        return PluginDetailResponse.process_exception(e)


async def list_plugins(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    has_webhook: Optional[bool] = None,
) -> PluginListResponse:
    """查询插件列表

    Args:
        page: 页码，默认1
        page_size: 每页数量，默认10
        keyword: 搜索关键词
        has_webhook: 是否有webhook

    Returns:
        PluginListResponse: 插件列表响应
    """
    try:
        params: Dict[str, Union[str, int, bool]] = {
            "page": page,
            "pageSize": page_size,
        }

        if keyword:
            params["keyword"] = keyword
        if has_webhook is not None:
            params["hasWebhook"] = has_webhook
        if not config.ENSURE_SFW_CONTENT:
            params["allowNsfw"] = True

        async with get_client() as client:
            response = await client.get(
                url="/api/plugin",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            return PluginListResponse(**data)
    except Exception as e:
        logger.error(f"查询插件列表发生错误: {e}")
        return PluginListResponse.process_exception(e)


async def list_user_plugins() -> UserPluginListResponse:
    """获取用户上传的插件列表

    Returns:
        UserPluginListResponse: 简化版插件列表响应
    """
    try:
        async with get_client(require_auth=True) as client:
            response = await client.get(url="/api/plugin/user")
            response.raise_for_status()
            return UserPluginListResponse(**response.json())
    except Exception as e:
        logger.error(f"获取用户上传插件列表发生错误: {e}")
        return UserPluginListResponse.process_exception(e)
