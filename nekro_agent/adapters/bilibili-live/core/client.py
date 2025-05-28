from pathlib import Path  # Added for __main__ test
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

import aiohttp
from pydantic import BaseModel, Field

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger


class Danmaku(BaseModel):
    from_live_room: int = Field(
        default=0, description="消息来源(房间号)",
    )
    uid: str = Field(default="0", description="消息用户ID")
    username: str = Field(default="unknown", description="用户名")
    text: str = Field(default="", description="弹幕内容")
    time: int = Field(default=0, description="弹幕发送时间")
    url: str = Field(default="", description="弹幕中的图片url 没有则留空")
    is_trigget: bool = Field(
        default=True, description="是否触发LLM (由ws客户端接收并处理)",
    )
    is_system: bool = Field(
        default=False, description="是否作为system身份发送 (由ws客户端接收并处理)",
    )

