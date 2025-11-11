"""
Telegram 适配器配置
"""

from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField


def _get_default_proxy() -> str:
    """获取系统默认代理配置"""
    try:
        from nekro_agent.core.config import config
        return config.DEFAULT_PROXY or ""
    except Exception:
        return ""


class TelegramConfig(BaseAdapterConfig):
    """Telegram 适配器配置类"""

    BOT_TOKEN: str = Field(
        default="",
        title="Bot Token",
        description="Telegram Bot API Token",
        json_schema_extra={"is_secret": True},
    )

    PROXY_URL: str = Field(
        default_factory=_get_default_proxy,
        title="代理地址",
        description="Telegram API 访问代理，支持 http/https/socks5 协议.空白表示不使用代理",
        json_schema_extra=ExtraField(placeholder="例: http://127.0.0.1:7890 或 socks5://127.0.0.1:1080").model_dump(),
    )

    @property
    def is_configured(self) -> bool:
        """检查配置是否完整"""
        return bool(self.BOT_TOKEN)
