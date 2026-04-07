"""
Telegram 适配器配置
"""

from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text


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
        json_schema_extra=ExtraField(
            required=True,
            is_secret=True,
            i18n_category=i18n_text(zh_CN="Bot 配置", en_US="Bot Settings"),
            i18n_title=i18n_text(zh_CN="Bot Token", en_US="Bot Token"),
            i18n_description=i18n_text(
                zh_CN="Telegram Bot API Token",
                en_US="Telegram Bot API token.",
            ),
        ).model_dump(),
    )

    PROXY_URL: str = Field(
        default_factory=_get_default_proxy,
        title="代理地址",
        description="Telegram API 访问代理，支持 http/https/socks5 协议.空白表示不使用代理",
        json_schema_extra=ExtraField(
            placeholder="例: http://127.0.0.1:7890 或 socks5://127.0.0.1:1080",
            i18n_category=i18n_text(zh_CN="网络", en_US="Network"),
            i18n_title=i18n_text(zh_CN="代理地址", en_US="Proxy URL"),
            i18n_description=i18n_text(
                zh_CN="Telegram API 访问代理，支持 http/https/socks5 协议。空白表示不使用代理",
                en_US="Proxy used to access the Telegram API. Supports http/https/socks5. Leave blank to disable the proxy.",
            ),
        ).model_dump(),
    )

    @property
    def is_configured(self) -> bool:
        """检查配置是否完整"""
        return bool(self.BOT_TOKEN)
