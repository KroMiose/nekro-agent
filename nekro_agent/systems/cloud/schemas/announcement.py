from typing import List, Optional

from pydantic import BaseModel, Field

from nekro_agent.systems.cloud.schemas.base import BasicResponse


class AnnouncementSummary(BaseModel):
    """公告摘要（精简字段）"""

    id: str
    title: str
    type: str
    priority: int
    is_pinned: bool = Field(alias="isPinned")
    created_at: str = Field(alias="createdAt")


class AnnouncementDetail(BaseModel):
    """公告详情"""

    id: str
    title: str
    content: str
    type: str
    priority: int
    is_pinned: bool = Field(alias="isPinned")
    author_name: str = Field(alias="authorName")
    expires_at: Optional[str] = Field(default=None, alias="expiresAt")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class AnnouncementLatestResponse(BasicResponse):
    """最新公告摘要响应"""

    data: Optional[List[AnnouncementSummary]] = None

    @classmethod
    def process_exception(cls, exc: Exception):
        return cls(
            success=False,
            message=f"获取公告失败: {exc!s}",
            data=None,
        )


class AnnouncementDetailResponse(BasicResponse):
    """公告详情响应"""

    data: Optional[AnnouncementDetail] = None

    @classmethod
    def process_exception(cls, exc: Exception):
        return cls(
            success=False,
            message=f"获取公告详情失败: {exc!s}",
            data=None,
        )
