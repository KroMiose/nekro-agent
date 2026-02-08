from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from nekro_agent.systems.cloud.schemas.base import BasicResponse


class PluginBase(BaseModel):
    """插件基础信息模型"""

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
    icon: Optional[str] = None  # 插件图标URL
    isOwner: Optional[bool] = None  # 是否为当前用户上传的插件


class PluginCreate(BaseModel):
    """创建插件请求模型"""

    name: str
    moduleName: str
    description: str
    author: str
    hasWebhook: bool
    homepageUrl: Optional[str] = None
    githubUrl: Optional[str] = None
    cloneUrl: Optional[str] = None
    licenseType: Optional[str] = None
    isSfw: bool = True
    icon: Optional[str] = None  # 插件图标，可以是Base64或URL


class PluginUpdate(BaseModel):
    """更新插件请求模型"""

    name: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    hasWebhook: Optional[bool] = None
    homepageUrl: Optional[str] = None
    githubUrl: Optional[str] = None
    cloneUrl: Optional[str] = None
    licenseType: Optional[str] = None
    isSfw: Optional[bool] = None
    icon: Optional[str] = None  # 插件图标，可以是Base64或URL


class PluginCreateResponse(BasicResponse):
    """创建插件响应模型"""

    data: Optional[Dict[str, Any]] = None


class PluginDetailResponse(BasicResponse):
    """获取插件详情响应模型"""

    data: Optional[PluginBase] = None


class PluginListItem(BaseModel):
    """插件列表项模型"""

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
    createdAt: str
    updatedAt: str
    icon: Optional[str] = None  # 插件图标URL
    isOwner: Optional[bool] = None  # 是否为当前用户上传的插件


class PluginListData(BaseModel):
    """插件列表数据模型"""

    items: List[PluginListItem]
    total: int
    page: int
    pageSize: int


class PluginListResponse(BasicResponse):
    """获取插件列表响应模型"""

    data: Optional[PluginListData] = None


class UserPluginItem(BaseModel):
    """用户插件列表项模型"""

    id: str
    name: str
    moduleName: str


class UserPluginListData(BaseModel):
    """用户插件列表数据模型"""

    items: List[UserPluginItem]
    total: int


class UserPluginListResponse(BasicResponse):
    """获取用户插件列表响应模型"""

    data: Optional[UserPluginListData] = None


# --- 仓库信息相关模型 ---

class RepoUser(BaseModel):
    login: str
    avatarUrl: str
    htmlUrl: str


class RepoLabel(BaseModel):
    name: str
    color: str


class RepoIssue(BaseModel):
    number: int
    title: str
    state: str
    htmlUrl: str
    createdAt: str
    updatedAt: str
    user: RepoUser
    comments: int
    labels: List[RepoLabel]


class RepoData(BaseModel):
    """仓库详细数据模型"""
    
    # 基本信息
    fullName: str
    description: Optional[str] = None
    htmlUrl: str
    homepage: Optional[str] = None
    
    # 统计数据
    stargazersCount: int
    forksCount: int
    watchersCount: int
    openIssuesCount: int
    
    # 仓库属性
    language: Optional[str] = None
    license: Optional[str] = None
    defaultBranch: str
    
    # 时间信息
    createdAt: str
    updatedAt: str
    pushedAt: str
    
    # 动态
    recentIssues: List[RepoIssue]
    
    # 快捷链接
    issuesUrl: str
    forksUrl: str
    stargazersUrl: str


class PluginRepoResponse(BasicResponse):
    """获取插件仓库信息响应模型"""
    
    data: Optional[RepoData] = None
