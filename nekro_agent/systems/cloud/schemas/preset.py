from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from nekro_agent.systems.cloud.schemas.base import BasicResponse


class NekroCloudModel(BaseModel):
    class Config:
        extra = "ignore"


class PresetCreate(NekroCloudModel):
    """创建人设的请求数据模型"""

    name: str = Field(..., min_length=1, max_length=100, description="人设名称")
    title: str = Field(..., min_length=1, max_length=100, description="资源标题")
    avatar: str = Field(..., description="头像(base64字符串)")
    content: str = Field(..., min_length=1, max_length=5000, description="人设内容")
    description: str = Field(..., min_length=1, max_length=5000, description="详细说明")
    tags: str = Field(..., description="标签(逗号分隔)")
    author: str = Field(..., min_length=1, max_length=50, description="作者")
    ext_data: str = Field("", description="扩展数据(可选)")
    is_sfw: bool = Field(True, description="是否为安全内容")
    instance_id: str = Field(..., min_length=1, description="实例ID")


class PresetUpdate(PresetCreate):
    """更新人设的请求数据模型"""

    # 与创建模型相同，但用于更新操作


class PresetDetail(NekroCloudModel):
    """人设详情响应模型"""

    id: str = Field(..., description="人设ID")
    name: str = Field(..., description="人设名称")
    title: str = Field(..., description="资源标题")
    avatar: str = Field(..., description="头像(base64字符串)")
    content: str = Field(..., description="人设内容")
    description: str = Field(..., description="详细说明")
    tags: str = Field(..., description="标签(逗号分隔)")
    author: str = Field(..., description="作者")
    is_owner: bool = Field(default=False, alias="isOwner", description="是否为当前用户拥有")
    ext_data: Optional[str] = Field("", alias="extData", description="扩展数据")
    created_at: Optional[str] = Field(None, alias="createdAt", description="创建时间")
    updated_at: Optional[str] = Field(None, alias="updatedAt", description="更新时间")


class PresetListItem(PresetDetail):
    """人设列表项模型"""

    # 与详情模型相同


class PresetListData(NekroCloudModel):
    """人设列表数据模型"""

    items: List[PresetListItem] = Field(..., description="人设列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., alias="pageSize", description="每页记录数")
    total_pages: int = Field(..., alias="totalPages", description="总页数")


class UserPresetItem(NekroCloudModel):
    """用户人设列表项模型，简化版"""

    id: str = Field(..., description="人设ID")
    name: str = Field(..., description="人设名称")
    title: str = Field(..., description="资源标题")


class UserPresetListData(NekroCloudModel):
    """用户人设列表数据模型"""

    items: List[UserPresetItem] = Field(..., description="人设列表")
    total: int = Field(..., description="总记录数")


class PresetCreateResponseData(NekroCloudModel):
    """创建人设响应数据模型"""

    id: str = Field(..., description="人设ID")


class PresetCreateResponse(BasicResponse):
    """创建人设响应模型"""

    data: Optional[PresetCreateResponseData] = Field(None, description="响应数据")


class PresetListResponse(BasicResponse):
    """人设列表响应模型"""

    data: Optional[PresetListData] = Field(None, description="响应数据")


class UserPresetListResponse(BasicResponse):
    """用户人设列表响应模型"""

    data: Optional[UserPresetListData] = Field(None, description="响应数据")


class PresetDetailResponse(BasicResponse):
    """人设详情响应模型"""

    data: Optional[PresetDetail] = Field(None, description="响应数据")
