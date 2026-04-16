from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import CloudServiceError
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.systems.cloud.api.favorite import (
    add_favorite,
    list_favorites,
    remove_favorite,
)

logger = get_sub_logger("cloud_api")
router = APIRouter(prefix="/cloud/favorites", tags=["Cloud Favorites"])


class FavoriteResource(BaseModel):
    """收藏资源信息"""

    id: str = Field(..., description="资源ID")
    name: str = Field(..., description="资源名称")
    title: str = Field(..., description="资源标题")
    avatar: Optional[str] = Field(None, description="头像URL")
    icon: Optional[str] = Field(None, description="插件图标URL")
    author: str = Field(..., description="作者")
    description: str = Field(..., description="资源描述")
    moduleName: Optional[str] = Field(None, description="插件模块名")
    hasWebhook: Optional[bool] = Field(None, description="是否有Webhook")
    isLocal: Optional[bool] = Field(None, description="是否已获取到本地")


class FavoriteItem(BaseModel):
    """收藏列表项"""

    id: str = Field(..., description="收藏ID")
    targetType: str = Field(..., description="目标类型: plugin 或 preset")
    targetId: str = Field(..., description="目标资源ID")
    createdAt: int = Field(..., description="收藏时间戳(毫秒)")
    resource: FavoriteResource = Field(..., description="资源详细信息")


class FavoriteListData(BaseModel):
    """收藏列表数据"""

    items: List[FavoriteItem] = Field(..., description="收藏列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    pageSize: int = Field(..., description="每页记录数")
    totalPages: int = Field(..., description="总页数")


class FavoriteListResponse(BaseModel):
    """获取收藏列表响应"""

    success: bool = Field(True, description="是否成功")
    data: FavoriteListData = Field(..., description="响应数据")


class FavoriteCreateRequest(BaseModel):
    """添加收藏请求"""

    target_type: str = Field(..., alias="targetType", description="目标类型: plugin 或 preset")
    target_id: str = Field(..., alias="targetId", description="目标资源ID")


class ActionResponse(BaseModel):
    """操作响应"""

    ok: bool = Field(..., description="操作是否成功")


@router.get("", summary="获取收藏列表")
@require_role(Role.Admin)
async def get_favorites(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=1000, description="每页数量"),
    target_type: Optional[str] = Query(None, description="筛选类型: plugin 或 preset"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> FavoriteListResponse:
    """获取当前用户的收藏列表"""
    response = await list_favorites(
        page=page,
        page_size=page_size,
        target_type=target_type,
    )
    if not response.success:
        raise CloudServiceError(reason=str(response.error or response.message or "获取收藏列表失败"))

    if not response.data:
        return FavoriteListResponse(
            data=FavoriteListData(
                items=[],
                total=0,
                page=page,
                pageSize=page_size,
                totalPages=0,
            )
        )

    items = [
        FavoriteItem(
            id=item.id,
            targetType=item.target_type,
            targetId=item.target_id,
            createdAt=item.created_at,
            resource=FavoriteResource(
                id=item.resource.id,
                name=item.resource.name,
                title=item.resource.title,
                avatar=item.resource.avatar,
                icon=getattr(item.resource, 'icon', None),
                author=item.resource.author,
                description=item.resource.description,
                moduleName=item.resource.moduleName,
                hasWebhook=getattr(item.resource, 'hasWebhook', None),
                isLocal=getattr(item.resource, 'isLocal', None),
            ),
        )
        for item in response.data.items
    ]

    return FavoriteListResponse(
        data=FavoriteListData(
            items=items,
            total=response.data.total,
            page=response.data.page,
            pageSize=response.data.page_size,
            totalPages=response.data.total_pages,
        )
    )


@router.post("", summary="添加收藏")
@require_role(Role.Admin)
async def create_favorite(
    request: FavoriteCreateRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """添加收藏"""
    response = await add_favorite(
        target_type=request.target_type,
        target_id=request.target_id,
    )

    if not response.success:
        raise CloudServiceError(reason=str(response.error or response.message or "添加收藏失败"))

    return ActionResponse(ok=True)


@router.delete("", summary="取消收藏")
@require_role(Role.Admin)
async def delete_favorite(
    targetType: str = Query(..., alias="targetType", description="目标类型: plugin 或 preset"),
    targetId: str = Query(..., alias="targetId", description="目标资源ID"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """取消收藏"""
    response = await remove_favorite(
        target_type=targetType,
        target_id=targetId,
    )

    if not response.success:
        raise CloudServiceError(reason=str(response.error or response.message or "取消收藏失败"))

    return ActionResponse(ok=True)
