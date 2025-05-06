from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from httpx import HTTPStatusError
from pydantic import BaseModel, Field

from nekro_agent.systems.cloud.exceptions import NekroCloudDisabled


class BasicResponse(BaseModel):
    """基本响应"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    error: Optional[str] = Field(default=None, description="错误信息")

    @classmethod
    def process_exception(cls, e: Exception):
        if isinstance(e, NekroCloudDisabled):
            return cls(
                success=False,
                message="Nekro AI 社区服务遥测未启用，当前实例暂无权限使用",
                error="Nekro AI 社区服务遥测未启用，当前实例暂无权限使用",
            )
        if isinstance(e, HTTPStatusError) and e.response.status_code in [401, 403]:
            print(f"111 {e.response.text} {e.response.status_code}")
            return cls(
                success=False,
                message="Nekro AI 社区 API Key 无效，请前往 Nekro AI 社区获取并配置",
                error=e.response.text,
            )
        raise e

    class Config:
        extra = "ignore"
