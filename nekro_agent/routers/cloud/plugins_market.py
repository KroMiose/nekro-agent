from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from nekro_agent.core.logger import logger
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.systems.cloud.api.plugin import (
    create_plugin,
    delete_plugin,
    get_plugin,
    list_plugins,
    list_user_plugins,
)
from nekro_agent.systems.cloud.api.plugin import (
    update_plugin as cloud_update_plugin,
)
from nekro_agent.systems.cloud.schemas.plugin import PluginCreate, PluginUpdate
from nekro_agent.tools.image_utils import process_image_data_url

router = APIRouter(prefix="/cloud/plugins-market", tags=["Cloud Plugins Market"])


@router.get("/list", summary="获取云端插件列表")
@require_role(Role.Admin)
async def get_cloud_plugins_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    keyword: Optional[str] = None,
    has_webhook: Optional[bool] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取云端插件列表"""
    try:
        # 查询云端插件列表
        response = await list_plugins(page=page, page_size=page_size, keyword=keyword, has_webhook=has_webhook)

        if not response.success:
            return Ret.fail(msg=response.message)

        if not response.data or not response.data.items:
            return Ret.success(msg="暂无数据", data={"total": 0, "items": []})

        # 获取所有云端插件的ID
        # remote_ids = [item.id for item in response.data.items]

        # 查询本地插件，获取版本信息
        # 这里只是预留位置，实际实现需要根据你的系统进行调整
        local_plugins = []
        local_plugin_ids = plugin_collector.package_data.get_remote_ids()

        # 构建返回结果，添加是否已在本地的标记
        result = []
        for item in response.data.items:
            # 检查是否本地存在该插件
            is_local = item.id in local_plugin_ids

            # 获取本地版本，如果存在
            version = None
            can_update = False
            if is_local:
                # 查找对应的本地插件获取版本信息
                for plugin in local_plugins:
                    if getattr(plugin, "remote_id", None) == item.id:
                        version = getattr(plugin, "version", None)
                        # 简单判断是否可更新，实际逻辑可能更复杂
                        can_update = False  # 这里先设为False，实际应该比较版本
                        break

            result.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "moduleName": item.moduleName,
                    "description": item.description,
                    "author": item.author,
                    "hasWebhook": item.hasWebhook,
                    "homepageUrl": item.homepageUrl,
                    "githubUrl": item.githubUrl,
                    "cloneUrl": item.cloneUrl,
                    "licenseType": item.licenseType,
                    "createdAt": item.createdAt,
                    "updatedAt": item.updatedAt,
                    "is_local": is_local,
                    "version": version,
                    "can_update": can_update,
                    "icon": item.icon,
                    "isOwner": getattr(item, "isOwner", False),
                },
            )

        return Ret.success(
            msg="获取成功",
            data={
                "total": response.data.total,
                "items": result,
                "page": page,
                "pageSize": page_size,
                "totalPages": (response.data.total + page_size - 1) // page_size,  # 计算总页数
            },
        )

    except Exception as e:
        logger.error(f"获取云端插件列表失败: {e}")
        return Ret.fail(msg=f"获取失败: {e}")


@router.get("/user-plugins", summary="获取用户已上传的插件")
@require_role(Role.Admin)
async def get_user_plugins(
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取用户已上传的插件列表"""
    try:
        response = await list_user_plugins()

        if not response.success:
            return Ret.fail(msg=f"获取失败: {response.error}")

        if not response.data or not response.data.items:
            return Ret.success(msg="暂无数据", data=[])

        return Ret.success(msg="获取成功", data=response.data.items)

    except Exception as e:
        logger.error(f"获取用户插件列表失败: {e}")
        return Ret.fail(msg=f"获取失败: {e}")


@router.get("/detail/{plugin_id}", summary="获取插件详情")
@require_role(Role.Admin)
async def get_plugin_detail(
    plugin_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取插件详情"""
    try:
        # 获取云端插件详情
        response = await get_plugin(plugin_id)

        if not response.success or not response.data:
            return Ret.fail(msg=f"获取失败: {response.error}")

        plugin_data = response.data

        # 查询本地是否存在该插件
        is_local = False
        version = None
        can_update = False

        # 构建返回数据
        result = {
            "id": plugin_data.id,
            "name": plugin_data.name,
            "moduleName": plugin_data.moduleName,
            "description": plugin_data.description,
            "author": plugin_data.author,
            "hasWebhook": plugin_data.hasWebhook,
            "homepageUrl": plugin_data.homepageUrl,
            "githubUrl": plugin_data.githubUrl,
            "cloneUrl": plugin_data.cloneUrl,
            "licenseType": plugin_data.licenseType,
            "createdAt": plugin_data.created_at,
            "updatedAt": plugin_data.updated_at,
            "is_local": is_local,
            "version": version,
            "can_update": can_update,
            "icon": plugin_data.icon,
            "isOwner": plugin_data.isOwner,
        }

        return Ret.success(msg="获取成功", data=result)

    except Exception as e:
        logger.error(f"获取插件详情失败: {e}")
        return Ret.fail(msg=f"获取失败: {e}")


@router.post("/download/{module_name}", summary="下载云端插件到本地")
@require_role(Role.Admin)
async def download_plugin(
    module_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """下载云端插件到本地"""
    try:
        # 检查插件是否已存在
        local_plugins = plugin_collector.package_data.get_remote_ids()
        if module_name in local_plugins:
            return Ret.fail(msg="插件已存在")

        # 获取云端插件详情
        response = await get_plugin(module_name)
        if not response.success or not response.data:
            return Ret.fail(msg=response.message)

        plugin_data = response.data

        if not plugin_data.cloneUrl:
            return Ret.fail(msg=f"找不到插件 `{module_name}` 的仓库克隆地址")

        try:
            await plugin_collector.clone_package(
                module_name=plugin_data.moduleName,
                git_url=plugin_data.cloneUrl,
                remote_id=plugin_data.id,
                auto_load=True,
            )
        except Exception as e:
            return Ret.fail(msg=f"下载插件失败: {e}")

        try:
            await plugin_collector.reload_plugin_by_module_name(plugin_data.moduleName, is_package=True)
        except Exception as e:
            logger.exception(f"加载插件失败: {e}")
            return Ret.fail(msg=f"加载插件失败: {e}")

        return Ret.success(msg="下载成功，插件已安装")

    except Exception as e:
        logger.error(f"下载插件失败: {e}")
        return Ret.fail(msg=f"下载失败: {e}")


@router.post("/update/{module_name}", summary="更新本地插件")
@require_role(Role.Admin)
async def update_plugin(
    module_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """更新本地插件"""
    try:
        # 检查插件是否存在于本地
        local_plugins = plugin_collector.package_data.get_remote_ids()
        if module_name not in local_plugins:
            return Ret.fail(msg="该插件不存在于本地，请先下载")

        # 获取云端插件详情
        response = await get_plugin(module_name)
        if not response.success or not response.data:
            return Ret.fail(msg=response.message)

        logger.info(f"准备更新插件: {module_name}")

        try:
            await plugin_collector.update_package(
                module_name=response.data.moduleName,
                auto_reload=True,
            )
        except Exception as e:
            return Ret.fail(msg=f"更新插件失败: {e}")

        return Ret.success(msg="更新成功，插件已更新至最新版本")

    except Exception as e:
        logger.error(f"更新插件失败: {e}")
        return Ret.fail(msg=f"更新失败: {e}")


@router.post("/create", summary="创建插件")
@require_role(Role.Admin)
async def create_cloud_plugin(
    plugin_data: PluginCreate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """创建云端插件"""
    try:
        # 处理图标，如果是Base64格式的，进行压缩处理
        if plugin_data.icon and plugin_data.icon.startswith("data:image/"):
            # 尝试压缩图标图片
            try:
                compressed_icon = await process_image_data_url(plugin_data.icon)
                plugin_data.icon = compressed_icon
            except Exception as e:
                logger.error(f"压缩插件图标失败: {e}")
                # 如果压缩失败，继续使用原图标

        # 创建插件
        response = await create_plugin(plugin_data)

        if not response.success:
            return Ret.fail(msg=response.message)

        if not response.data:
            return Ret.fail(msg="创建失败，服务返回数据为空")

        return Ret.success(msg="插件创建成功", data=response.data)

    except Exception as e:
        logger.error(f"创建插件失败: {e}")
        return Ret.fail(msg=f"创建失败: {e}")


@router.delete("/plugin/{module_name}", summary="下架云端插件")
@require_role(Role.Admin)
async def delete_cloud_plugin(
    module_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """下架云端插件"""
    try:
        # 调用云端接口删除插件
        response = await delete_plugin(module_name)

        if not response.success:
            # 处理可能的错误，比如权限不足或插件不存在
            return Ret.fail(msg=response.message)

        return Ret.success(msg=f"插件 '{module_name}' 已成功从云端删除")

    except Exception as e:
        logger.error(f"下架云端插件 '{module_name}' 失败: {e}")
        # 处理调用过程中的其他异常
        return Ret.fail(msg=f"删除插件失败: {e}")


@router.put("/plugin/{module_name}", summary="更新插件信息")
@require_role(Role.Admin)
async def update_user_plugin(
    module_name: str,
    plugin_data: PluginUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """更新用户发布的插件信息

    Args:
        module_name: 插件模块名称
        plugin_data: 要更新的插件数据
        _current_user: 当前用户

    Returns:
        Ret: 请求结果
    """
    try:
        # 获取当前插件信息，判断用户是否有权限修改
        current_plugin = await get_plugin(module_name)
        if not current_plugin.success:
            return Ret.fail(msg=f"获取插件信息失败: {current_plugin.error}")

        if not current_plugin.data or not current_plugin.data.isOwner:
            return Ret.fail(msg="您没有权限修改此插件信息")

        # 处理图标，如果是Base64格式的，进行压缩处理
        if plugin_data.icon and plugin_data.icon.startswith("data:image/"):
            try:
                compressed_icon = await process_image_data_url(plugin_data.icon)
                plugin_data.icon = compressed_icon
            except Exception as e:
                logger.error(f"压缩插件图标失败: {e}")
                # 如果压缩失败，继续使用原图标

        # 准备更新数据
        update_data = plugin_data.dict(exclude_unset=True, exclude_none=True)

        # 调用云端API更新插件信息
        response = await cloud_update_plugin(module_name, update_data)

        if not response.success:
            return Ret.fail(msg=f"更新插件信息失败: {response.error}")

        return Ret.success(msg="插件信息更新成功")

    except Exception as e:
        logger.error(f"更新插件信息失败: {e}")
        return Ret.fail(msg=f"更新失败: {e}")
