from typing import Dict, List

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel

from nekro_agent.models.db_plugin_data import DBPluginData
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import NotFoundError, PluginLoadError, PluginNotFoundError
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.plugin.manager import (
    disable_plugin,
    enable_plugin,
    get_all_ext_meta_data,
    get_all_plugin_router_info,
    get_plugin_detail,
)
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


class ActionResponse(BaseModel):
    ok: bool = True


class PluginDocsResponse(BaseModel):
    docs: str | None
    exists: bool


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
    def from_orm(cls, obj: DBPluginData) -> "PluginDataResponse":
        return cls(
            id=obj.id,
            plugin_key=obj.plugin_key,
            target_chat_key=obj.target_chat_key,
            target_user_id=obj.target_user_id,
            data_key=obj.data_key,
            data_value=obj.data_value,
            create_time=obj.create_time.isoformat(),
            update_time=obj.update_time.isoformat(),
        )


class PluginRoutesResponse(BaseModel):
    plugin_routes: list[dict]
    debug_completed: bool


class PluginRouteVerifyResponse(BaseModel):
    plugin_key: str
    found_routes: list[dict]
    routes_count: int


@router.get("/list", summary="获取插件列表", response_model=List[dict])
@require_role(Role.Admin)
async def get_plugins(
    _current_user: DBUser = Depends(get_current_active_user),
) -> List[dict]:
    """获取插件列表"""
    return await get_all_ext_meta_data()


@router.get("/detail/{plugin_id}", summary="获取插件详情", response_model=dict)
@require_role(Role.Admin)
async def get_plugin_detail_handler(
    plugin_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> dict:
    """获取插件详情"""
    plugin = await get_plugin_detail(plugin_id)
    if not plugin:
        raise PluginNotFoundError(plugin_id=plugin_id)
    return plugin


@router.post("/toggle/{plugin_id}", summary="启用/禁用插件", response_model=ActionResponse)
@require_role(Role.Admin)
async def toggle_plugin(
    plugin_id: str,
    body: TogglePluginRequest = Body(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """启用/禁用插件"""
    module_name = plugin_id.split(".")[-1]
    failed_plugin = plugin_collector.get_failed_plugin_by_module_name(module_name)
    if failed_plugin:
        raise PluginLoadError(plugin_id=plugin_id, detail=failed_plugin.error_message)

    if body.enabled:
        success = await enable_plugin(plugin_id)
    else:
        success = await disable_plugin(plugin_id)

    if not success:
        raise PluginNotFoundError(plugin_id=plugin_id)
    return ActionResponse(ok=True)


@router.get("/docs/{plugin_id}", summary="获取插件文档", response_model=PluginDocsResponse)
@require_role(Role.Admin)
async def get_plugin_docs(
    plugin_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> PluginDocsResponse:
    """获取插件文档"""
    plugin = plugin_collector.get_plugin(plugin_id)
    if not plugin:
        raise PluginNotFoundError(plugin_id=plugin_id)
    docs = await plugin.get_docs()
    return PluginDocsResponse(docs=docs, exists=docs is not None)


@router.post("/reload", summary="重载插件", response_model=ActionResponse)
@require_role(Role.Admin)
async def reload_plugins(module_name: str, _current_user: DBUser = Depends(get_current_active_user)) -> ActionResponse:
    """重载插件"""
    await plugin_collector.reload_plugin_by_module_name(module_name)
    return ActionResponse(ok=True)


@router.get("/data/{plugin_id}", summary="获取插件数据列表", response_model=List[PluginDataResponse])
@require_role(Role.Admin)
async def get_plugin_data(
    plugin_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> List[PluginDataResponse]:
    """获取插件数据列表"""
    data = await DBPluginData.filter(plugin_key=plugin_id).all()
    return [PluginDataResponse.from_orm(item) for item in data]


@router.delete("/data/{plugin_id}/{data_id}", summary="删除插件数据", response_model=ActionResponse)
@require_role(Role.Admin)
async def delete_plugin_data(
    plugin_id: str,
    data_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """删除插件数据"""
    data = await DBPluginData.filter(plugin_key=plugin_id, id=data_id).first()
    if not data:
        raise NotFoundError(resource="插件数据")
    await data.delete()
    return ActionResponse(ok=True)


@router.delete("/data/{plugin_id}", summary="重置插件数据", response_model=ActionResponse)
@require_role(Role.Admin)
async def reset_plugin_data(
    plugin_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """重置插件数据（删除所有数据）"""
    await DBPluginData.filter(plugin_key=plugin_id).delete()
    return ActionResponse(ok=True)


@router.delete("/package/{module_name}", summary="删除云端插件", response_model=ActionResponse)
@require_role(Role.Admin)
async def remove_package(
    module_name: str,
    clear_data: bool = Query(False, description="是否删除插件在数据库中的存储数据"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """删除云端插件"""
    if clear_data:
        await plugin_collector.remove_package(module_name, clear_config=True)
        await plugin_collector.clear_plugin_store_data_by_module_name(module_name)
    else:
        await plugin_collector.remove_package(module_name, clear_config=False)
    return ActionResponse(ok=True)


@router.post("/package/update/{module_name}", summary="更新云端插件", response_model=ActionResponse)
@require_role(Role.Admin)
async def update_package(
    module_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """更新云端插件"""
    await plugin_collector.update_package(module_name, auto_reload=True)
    return ActionResponse(ok=True)


@router.get("/router-info", summary="获取所有插件路由信息", response_model=list[dict])
@require_role(Role.Admin)
async def get_plugin_router_info(
    _current_user: DBUser = Depends(get_current_active_user),
) -> list[dict]:
    """获取所有插件的路由信息"""
    return await get_all_plugin_router_info()


@router.post("/refresh-routes", summary="刷新插件路由", response_model=ActionResponse)
@require_role(Role.Admin)
async def refresh_plugin_routes(
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """刷新所有插件路由，更新OpenAPI文档"""
    from nekro_agent.services.plugin.router_manager import plugin_router_manager

    plugin_router_manager.refresh_all_plugin_routes()
    return ActionResponse(ok=True)


@router.get("/debug-routes", summary="调试路由信息", response_model=PluginRoutesResponse)
@require_role(Role.Admin)
async def debug_routes(_current_user: DBUser = Depends(get_current_active_user)) -> PluginRoutesResponse:
    """调试当前应用的所有路由信息（管理员专用）"""
    from nekro_agent.services.plugin.router_manager import plugin_router_manager

    plugin_routes = plugin_router_manager.debug_routes()
    return PluginRoutesResponse(plugin_routes=plugin_routes, debug_completed=True)


@router.get("/verify-plugin-routes/{plugin_key}", summary="验证插件路由", response_model=PluginRouteVerifyResponse)
@require_role(Role.Admin)
async def verify_plugin_routes_endpoint(
    plugin_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> PluginRouteVerifyResponse:
    """验证指定插件的路由是否正确挂载（管理员专用）"""
    from nekro_agent.services.plugin.router_manager import plugin_router_manager

    found_routes = plugin_router_manager.verify_plugin_routes(plugin_key)

    return PluginRouteVerifyResponse(
        plugin_key=plugin_key,
        found_routes=found_routes,
        routes_count=len(found_routes),
    )
