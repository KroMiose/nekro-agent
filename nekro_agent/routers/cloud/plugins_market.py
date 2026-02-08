from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import (
    CloudServiceError,
    ConflictError,
    NotFoundError,
    OperationFailedError,
    PermissionDeniedError,
)
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.systems.cloud.api.plugin import (
    create_plugin,
    delete_plugin,
    get_plugin,
    get_plugin_repo_info,
    list_plugins,
    list_user_plugins,
)
from nekro_agent.systems.cloud.api.plugin import update_plugin as cloud_update_plugin
from nekro_agent.systems.cloud.schemas.plugin import PluginCreate, PluginUpdate, RepoData
from nekro_agent.tools.image_utils import process_image_data_url

logger = get_sub_logger("cloud_api")
router = APIRouter(prefix="/cloud/plugins-market", tags=["Cloud Plugins Market"])


class CloudPlugin(BaseModel):
    id: str
    name: str
    moduleName: str
    description: str
    author: str
    hasWebhook: bool
    homepageUrl: Optional[str] = None
    githubUrl: Optional[str] = None
    cloneUrl: Optional[str] = None
    licenseType: Optional[str] = None
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    is_local: bool
    version: Optional[str] = None
    can_update: Optional[bool] = None
    icon: Optional[str] = None
    isOwner: Optional[bool] = None


class CloudPluginListResponse(BaseModel):
    total: int
    items: List[CloudPlugin]
    page: int
    page_size: int
    total_pages: int


class UserPlugin(BaseModel):
    id: str
    name: str
    moduleName: str


class ActionResponse(BaseModel):
    ok: bool = True


class CreateResponse(BaseModel):
    id: str


@router.get("/list", summary="获取云端插件列表")
@require_role(Role.Admin)
async def get_cloud_plugins_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    keyword: Optional[str] = None,
    has_webhook: Optional[bool] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> CloudPluginListResponse:
    """获取云端插件列表"""
    response = await list_plugins(page=page, page_size=page_size, keyword=keyword, has_webhook=has_webhook)

    if not response.success:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    if not response.data or not response.data.items:
        return CloudPluginListResponse(
            total=0,
            items=[],
            page=page,
            page_size=page_size,
            total_pages=0,
        )

    local_plugins = []
    local_plugin_ids = plugin_collector.package_data.get_remote_ids()

    result: List[CloudPlugin] = []
    for item in response.data.items:
        is_local = item.id in local_plugin_ids

        version = None
        can_update = False
        if is_local:
            for plugin in local_plugins:
                if getattr(plugin, "remote_id", None) == item.id:
                    version = getattr(plugin, "version", None)
                    can_update = False
                    break

        result.append(
            CloudPlugin(
                id=item.id,
                name=item.name,
                moduleName=item.moduleName,
                description=item.description,
                author=item.author,
                hasWebhook=item.hasWebhook,
                homepageUrl=item.homepageUrl,
                githubUrl=item.githubUrl,
                cloneUrl=item.cloneUrl,
                licenseType=item.licenseType,
                created_at=item.createdAt,
                updated_at=item.updatedAt,
                is_local=is_local,
                version=version,
                can_update=can_update,
                icon=item.icon,
                isOwner=getattr(item, "isOwner", False),
            ),
        )

    return CloudPluginListResponse(
        total=response.data.total,
        items=result,
        page=page,
        page_size=page_size,
        total_pages=(response.data.total + page_size - 1) // page_size,
    )


@router.get("/user-plugins", summary="获取用户已上传的插件")
@require_role(Role.Admin)
async def get_user_plugins(
    _current_user: DBUser = Depends(get_current_active_user),
) -> List[UserPlugin]:
    """获取用户已上传的插件列表"""
    response = await list_user_plugins()

    if not response.success:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    if not response.data or not response.data.items:
        return []

    return [UserPlugin(**item.model_dump()) for item in response.data.items]


@router.get("/detail/{plugin_id}", summary="获取插件详情")
@require_role(Role.Admin)
async def get_plugin_detail(
    plugin_id: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> CloudPlugin:
    """获取插件详情"""
    response = await get_plugin(plugin_id)

    if not response.success or not response.data:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    plugin_data = response.data

    return CloudPlugin(
        id=plugin_data.id,
        name=plugin_data.name,
        moduleName=plugin_data.moduleName,
        description=plugin_data.description,
        author=plugin_data.author,
        hasWebhook=plugin_data.hasWebhook,
        homepageUrl=plugin_data.homepageUrl,
        githubUrl=plugin_data.githubUrl,
        cloneUrl=plugin_data.cloneUrl,
        licenseType=plugin_data.licenseType,
        created_at=plugin_data.created_at,
        updated_at=plugin_data.updated_at,
        is_local=False,
        version=None,
        can_update=False,
        icon=plugin_data.icon,
        isOwner=plugin_data.isOwner,
    )


@router.get("/repo/{module_name}", summary="获取插件仓库信息")
@require_role(Role.Admin)
async def get_plugin_repo(
    module_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> RepoData:
    """获取插件仓库详细信息"""
    response = await get_plugin_repo_info(module_name)

    if not response.success or not response.data:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    return response.data


@router.post("/download/{module_name}", summary="下载云端插件到本地")
@require_role(Role.Admin)
async def download_plugin(
    module_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """下载云端插件到本地"""
    local_plugins = plugin_collector.package_data.get_remote_ids()
    if module_name in local_plugins:
        raise ConflictError(resource="插件")

    response = await get_plugin(module_name)
    if not response.success or not response.data:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    plugin_data = response.data

    if not plugin_data.cloneUrl:
        raise NotFoundError(resource="插件仓库")

    await plugin_collector.clone_package(
        module_name=plugin_data.moduleName,
        git_url=plugin_data.cloneUrl,
        remote_id=plugin_data.id,
        auto_load=True,
    )

    await plugin_collector.reload_plugin_by_module_name(plugin_data.moduleName, is_package=True)

    return ActionResponse(ok=True)


@router.post("/update/{module_name}", summary="更新本地插件")
@require_role(Role.Admin)
async def update_plugin(
    module_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """更新本地插件"""
    local_plugins = plugin_collector.package_data.get_remote_ids()
    if module_name not in local_plugins:
        raise NotFoundError(resource="插件")

    response = await get_plugin(module_name)
    if not response.success or not response.data:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    logger.info(f"准备更新插件: {module_name}")

    await plugin_collector.update_package(
        module_name=response.data.moduleName,
        auto_reload=True,
    )

    return ActionResponse(ok=True)


@router.post("/create", summary="创建插件")
@require_role(Role.Admin)
async def create_cloud_plugin(
    plugin_data: PluginCreate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> CreateResponse:
    """创建云端插件"""
    if plugin_data.icon and plugin_data.icon.startswith("data:image/"):
        plugin_data.icon = await process_image_data_url(plugin_data.icon)

    response = await create_plugin(plugin_data)

    if not response.success:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    if not response.data or "id" not in response.data:
        raise OperationFailedError(operation="创建插件")

    return CreateResponse(id=str(response.data.get("id")))


@router.delete("/plugin/{module_name}", summary="下架云端插件")
@require_role(Role.Admin)
async def delete_cloud_plugin(
    module_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """下架云端插件"""
    response = await delete_plugin(module_name)

    if not response.success:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    return ActionResponse(ok=True)


@router.put("/plugin/{module_name}", summary="更新插件信息")
@require_role(Role.Admin)
async def update_user_plugin(
    module_name: str,
    plugin_data: PluginUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """更新用户发布的插件信息"""
    current_plugin = await get_plugin(module_name)
    if not current_plugin.success:
        raise CloudServiceError(reason=str(current_plugin.error or current_plugin.message or "未知错误"))

    if not current_plugin.data or not current_plugin.data.isOwner:
        raise PermissionDeniedError()

    if plugin_data.icon and plugin_data.icon.startswith("data:image/"):
        plugin_data.icon = await process_image_data_url(plugin_data.icon)

    update_data = plugin_data.model_dump(exclude_unset=True, exclude_none=True)
    response = await cloud_update_plugin(module_name, update_data)

    if not response.success:
        raise CloudServiceError(reason=str(response.error or response.message or "未知错误"))

    return ActionResponse(ok=True)
