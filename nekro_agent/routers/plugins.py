import json
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from nekro_agent.core import logger
from nekro_agent.models.db_plugin_data import DBPluginData
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.plugin.manager import (
    disable_plugin,
    enable_plugin,
    get_all_ext_meta_data,
    get_all_plugin_router_info,
    get_plugin_detail,
)
from nekro_agent.services.plugin.schema import SandboxMethodType
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/plugins", tags=["Plugins"])


class TogglePluginRequest(BaseModel):
    """切换插件状态请求体"""

    enabled: bool


class SavePluginConfigRequest(BaseModel):
    configs: Dict[str, str]


class BatchUpdateConfig(BaseModel):
    """批量更新配置请求体"""

    configs: Dict[str, str]


class PluginDataResponse(BaseModel):
    """插件数据响应模型"""

    id: int
    plugin_key: str
    target_chat_key: str
    target_user_id: str
    data_key: str
    data_value: str
    create_time: str
    update_time: str

    @classmethod
    def from_orm(cls, db_data: DBPluginData) -> "PluginDataResponse":
        return cls(
            id=db_data.id,
            plugin_key=db_data.plugin_key,
            target_chat_key=db_data.target_chat_key,
            target_user_id=db_data.target_user_id,
            data_key=db_data.data_key,
            data_value=db_data.data_value,
            create_time=db_data.create_time.isoformat(),
            update_time=db_data.update_time.isoformat(),
        )


@router.get("/list", summary="获取插件列表")
@require_role(Role.Admin)
async def get_plugins(
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取插件列表"""
    try:
        plugins = await get_all_ext_meta_data()
        return Ret.success(msg="获取成功", data=plugins)
    except Exception as e:
        logger.error(f"获取插件列表失败: {e}")
        return Ret.error(msg=f"获取失败: {e!s}")


@router.get("/detail/{plugin_id}", summary="获取插件详情")
@require_role(Role.Admin)
async def get_plugin_detail_handler(
    plugin_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取插件详情"""
    try:
        plugin = await get_plugin_detail(plugin_id)
        if not plugin:
            return Ret.fail(msg="插件不存在")
        return Ret.success(msg="获取成功", data=plugin)
    except Exception as e:
        logger.error(f"获取插件详情失败: {e}")
        return Ret.error(msg=f"获取失败: {e!s}")


@router.post("/toggle/{plugin_id}", summary="启用/禁用插件")
@require_role(Role.Admin)
async def toggle_plugin(
    plugin_id: str,
    body: TogglePluginRequest = Body(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """启用/禁用插件"""
    try:
        if body.enabled:
            success = await enable_plugin(plugin_id)
            action = "启用"
        else:
            success = await disable_plugin(plugin_id)
            action = "禁用"

        if not success:
            return Ret.fail(msg=f"插件{action}失败，可能插件不存在")
        return Ret.success(msg=f"插件{action}成功")
    except Exception as e:
        logger.error(f"切换插件状态失败: {e}")
        return Ret.error(msg=f"操作失败: {e!s}")


@router.get("/docs/{plugin_id}", summary="获取插件文档")
@require_role(Role.Admin)
async def get_plugin_docs(
    plugin_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取插件文档"""
    plugin = plugin_collector.get_plugin(plugin_id)
    if not plugin:
        return Ret.fail(msg="插件不存在")
    docs = await plugin.get_docs()
    return Ret.success(msg="获取成功", data={"docs": docs, "exists": docs is not None})


@router.post("/reload", summary="重载插件")
@require_role(Role.Admin)
async def reload_plugins(module_name: str, _current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """重载插件"""
    try:
        await plugin_collector.reload_plugin_by_module_name(module_name)
        return Ret.success(msg="重载插件成功")
    except Exception as e:
        logger.exception(f"重载插件失败: {e}")
        return Ret.error(msg=f"重载插件失败: {e!s}")


@router.get("/data/{plugin_id}", summary="获取插件数据列表")
@require_role(Role.Admin)
async def get_plugin_data(
    plugin_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取插件数据列表"""
    try:
        data = await DBPluginData.filter(plugin_key=plugin_id).all()
        return Ret.success(msg="获取成功", data=[PluginDataResponse.from_orm(item) for item in data])
    except Exception as e:
        logger.error(f"获取插件数据失败: {e}")
        return Ret.error(msg=f"获取失败: {e!s}")


@router.delete("/data/{plugin_id}/{data_id}", summary="删除插件数据")
@require_role(Role.Admin)
async def delete_plugin_data(
    plugin_id: str,
    data_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """删除插件数据"""
    try:
        data = await DBPluginData.filter(plugin_key=plugin_id, id=data_id).first()
        if not data:
            return Ret.fail(msg="数据不存在")
        await data.delete()
        return Ret.success(msg="删除成功")
    except Exception as e:
        logger.error(f"删除插件数据失败: {e}")
        return Ret.error(msg=f"删除失败: {e!s}")


@router.delete("/data/{plugin_id}", summary="重置插件数据")
@require_role(Role.Admin)
async def reset_plugin_data(
    plugin_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """重置插件数据（删除所有数据）"""
    try:
        await DBPluginData.filter(plugin_key=plugin_id).delete()
        return Ret.success(msg="重置成功")
    except Exception as e:
        logger.error(f"重置插件数据失败: {e}")
        return Ret.error(msg=f"重置失败: {e!s}")


@router.delete("/package/{module_name}", summary="删除云端插件")
@require_role(Role.Admin)
async def remove_package(
    module_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """删除云端插件"""
    try:
        # remove_package方法现在包含了卸载步骤
        await plugin_collector.remove_package(module_name)
        return Ret.success(msg=f"云端插件 {module_name} 删除成功")
    except Exception as e:
        logger.exception(f"删除云端插件失败: {e}")
        return Ret.error(msg=f"删除失败: {e!s}")


@router.post("/package/update/{module_name}", summary="更新云端插件")
@require_role(Role.Admin)
async def update_package(
    module_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """更新云端插件"""
    try:
        await plugin_collector.update_package(module_name, auto_reload=True)
        return Ret.success(msg=f"云端插件 {module_name} 更新成功")
    except Exception as e:
        logger.error(f"更新云端插件失败: {e}")
        return Ret.error(msg=f"更新失败: {e!s}")


@router.get("/router-info", summary="获取所有插件路由信息")
@require_role(Role.Admin)
async def get_plugin_router_info(
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取所有插件的路由信息"""
    try:
        router_info = await get_all_plugin_router_info()
        return Ret.success(msg="获取插件路由信息成功", data=router_info)
    except Exception as e:
        logger.error(f"获取插件路由信息失败: {e}")
        return Ret.error(msg=f"获取失败: {e!s}")


@router.post("/refresh-routes", summary="刷新插件路由")
@require_role(Role.Admin)
async def refresh_plugin_routes(
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """刷新所有插件路由，更新OpenAPI文档"""
    try:
        from nekro_agent.services.plugin.router_manager import plugin_router_manager

        plugin_router_manager.refresh_all_plugin_routes()
        return Ret.success(msg="插件路由刷新成功")
    except Exception as e:
        logger.error(f"刷新插件路由失败: {e}")
        return Ret.error(msg=f"刷新失败: {e!s}")


@router.get("/debug-routes", summary="调试路由信息")
@require_role(Role.Admin)
async def debug_routes(_current_user: DBUser = Depends(get_current_active_user)):
    """调试当前应用的所有路由信息（管理员专用）"""
    try:
        from nekro_agent.services.plugin.router_manager import plugin_router_manager

        plugin_routes = plugin_router_manager.debug_routes()

        return Ret.success(
            msg="路由调试信息已输出到日志",
            data={
                "plugin_routes": plugin_routes,
                "debug_completed": True,
            },
        )
    except Exception as e:
        logger.exception(f"调试路由失败: {e}")
        return Ret.error(msg=f"调试路由失败: {e!s}")


@router.get("/verify-plugin-routes/{plugin_key}", summary="验证插件路由")
@require_role(Role.Admin)
async def verify_plugin_routes_endpoint(plugin_key: str, _current_user: DBUser = Depends(get_current_active_user)):
    """验证指定插件的路由是否正确挂载（管理员专用）"""
    try:
        from nekro_agent.services.plugin.router_manager import plugin_router_manager

        found_routes = plugin_router_manager.verify_plugin_routes(plugin_key)

        return Ret.success(
            msg=f"插件 {plugin_key} 共找到 {len(found_routes)} 个路由",
            data={
                "plugin_key": plugin_key,
                "found_routes": found_routes,
                "routes_count": len(found_routes),
            },
        )
    except Exception as e:
        logger.exception(f"验证插件路由失败: {e}")
        return Ret.error(msg=f"验证插件路由失败: {e!s}")
