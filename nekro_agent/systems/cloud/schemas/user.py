from typing import Optional

from pydantic import BaseModel, Field

from nekro_agent.systems.cloud.schemas.base import BasicResponse


class CommunityUserData(BaseModel):
    """社区用户数据"""

    github_id: int = Field(..., alias="githubId")
    username: str = Field(..., alias="username")
    email: Optional[str] = Field(default=None, alias="email")
    avatar_url: str = Field(..., alias="avatarUrl")


class CommunityUserResponse(BasicResponse):
    """社区用户信息响应"""

    data: Optional[CommunityUserData] = None

    @classmethod
    def process_exception(cls, exc: Exception):
        return cls(
            success=False,
            message=f"获取社区用户信息失败: {exc!s}",
            data=None,
        )
