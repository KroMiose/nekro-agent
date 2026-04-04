from typing import List, Optional

from pydantic import BaseModel, Field

from nekro_agent.systems.cloud.schemas.base import BasicResponse


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

    class Config:
        populate_by_name = True
        extra = "ignore"


class FavoriteItem(BaseModel):
    """收藏列表项"""

    id: str = Field(..., description="收藏ID")
    target_type: str = Field(..., alias="targetType", description="目标类型: plugin 或 preset")
    target_id: str = Field(..., alias="targetId", description="目标资源ID")
    created_at: int = Field(..., alias="createdAt", description="收藏时间戳(毫秒)")
    resource: FavoriteResource = Field(..., description="资源详细信息")

    class Config:
        populate_by_name = True
        extra = "ignore"


class FavoriteListData(BaseModel):
    """收藏列表数据"""

    items: List[FavoriteItem] = Field(..., description="收藏列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., alias="pageSize", description="每页记录数")
    total_pages: int = Field(..., alias="totalPages", description="总页数")

    class Config:
        populate_by_name = True
        extra = "ignore"


class FavoriteCreateRequest(BaseModel):
    """添加收藏请求"""

    target_type: str = Field(..., alias="targetType", description="目标类型: plugin 或 preset")
    target_id: str = Field(..., alias="targetId", description="目标资源ID")

    class Config:
        populate_by_name = True
        extra = "ignore"


class FavoriteListResponse(BasicResponse):
    """获取收藏列表响应"""

    data: Optional[FavoriteListData] = Field(None, description="响应数据")


class FavoriteCreateResponse(BasicResponse):
    """添加收藏响应"""
    pass


class FavoriteDeleteResponse(BasicResponse):
    """取消收藏响应"""
    pass
