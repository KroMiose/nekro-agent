from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class BasicResponse(BaseModel):
    """基本响应"""

    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(default=None, description="消息")
    error: Optional[str] = Field(default=None, description="错误信息")
