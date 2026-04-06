"""
Telegram 适配器配置
"""

from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig, adapter_extra_field


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
        json_schema_extra=adapter_extra_field(
            title_zh="Bot Token",
            title_en="Bot Token",
            description_zh="Telegram Bot API Token",
            description_en="Telegram Bot API token.",
            category_zh="Bot 配置",
            category_en="Bot Settings",
            required=True,
            is_secret=True,
        ),
    )

    PROXY_URL: str = Field(
        default_factory=_get_default_proxy,
        title="代理地址",
        description="Telegram API 访问代理，支持 http/https/socks5 协议.空白表示不使用代理",
        json_schema_extra=adapter_extra_field(
            title_zh="代理地址",
            title_en="Proxy URL",
            description_zh="Telegram API 访问代理，支持 http/https/socks5 协议。空白表示不使用代理",
            description_en="Proxy used to access the Telegram API. Supports http/https/socks5. Leave blank to disable the proxy.",
            category_zh="网络",
            category_en="Network",
            placeholder="例: http://127.0.0.1:7890 或 socks5://127.0.0.1:1080",
        ),
    )

    @property
    def is_configured(self) -> bool:
        """检查配置是否完整"""
        return bool(self.BOT_TOKEN)
