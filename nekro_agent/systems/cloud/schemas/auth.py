from typing import List, Optional

from pydantic import BaseModel, Field

from nekro_agent.systems.cloud.schemas.base import BasicResponse


class StarCheckData(BaseModel):
    """Star 检查数据结构"""

    starred_repositories: List[str] = Field(default_factory=list, alias="starredRepositories")
    unstarred_repositories: List[str] = Field(default_factory=list, alias="unstarredRepositories")
    all_starred: bool = Field(default=False, alias="allStarred")


class StarCheckResponse(BasicResponse):
    """官方仓库 Star 检查响应"""

    data: Optional[StarCheckData] = None

    @classmethod
    def process_exception(cls, exc: Exception):
        return cls(
            success=False,
            message=f"检查 GitHub Star 状态失败: {exc!s}",
            data=None,
        )
