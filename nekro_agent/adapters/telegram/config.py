"""
Telegram 适配器配置
"""

from pydantic import Field
from typing import Optional

from nekro_agent.adapters.interface.base import BaseAdapterConfig


class TelegramConfig(BaseAdapterConfig):
    USE_BOT_API: bool = Field(
        default=False,
        title="使用 Telegram Bot API 模式",
        description="无需 API_ID/API_HASH，仅需 BOT_TOKEN，适合中国手机号用户。",
    )
    """Telegram 适配器配置类"""
    BOT_TOKEN: str = Field(
        default="",
        title="Telegram Bot Token",
        description="从 @BotFather 获取的 Telegram Bot Token",
        json_schema_extra={"is_secret": True},
    )
    API_ID: Optional[str] = Field(
        default="",
        title="Telegram API ID",
        description="从 my.telegram.org 获取的 API ID",
        json_schema_extra={"is_secret": True},
    )
    API_HASH: Optional[str] = Field(
        default="",
        title="Telegram API Hash",
        description="从 my.telegram.org 获取的 API Hash",
        json_schema_extra={"is_secret": True},
    )
    ALLOWED_USERS: list[str] = Field(
        default=[],
        title="允许的用户 ID 列表",
        description="留空表示允许所有用户使用",
    )
    ALLOWED_CHATS: list[str] = Field(
        default=[],
        title="允许的群组 ID 列表",
        description="留空表示允许所有群组使用",
    )
    PROXY_URL: Optional[str] = Field(
        default="",
        title="代理服务器地址",
        description="如: http://127.0.0.1:7890 或 socks5://127.0.0.1:7890",
    )
    PROXY_USERNAME: Optional[str] = Field(
        default="",
        title="代理服务器用户名",
        description="如果代理服务器需要认证",
    )
    PROXY_PASSWORD: Optional[str] = Field(
        default="",
        title="代理服务器密码",
        description="如果代理服务器需要认证",
        json_schema_extra={"is_secret": True},
    )
    MAX_MESSAGE_LENGTH: int = Field(
        default=4096,
        title="最大消息长度",
        description="Telegram 消息的最大长度限制",
    )
    SESSION_FILE: str = Field(
        default="nekro_agent.session",
        title="会话文件名",
        description="用于存储 Telegram 客户端会话信息的文件名",
    )