from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text


class DiscordConfig(BaseAdapterConfig):
    """Discord 适配器配置"""

    BOT_TOKEN: str = Field(
        default="",
        title="机器人令牌",
        description="从 <a href='https://discord.com/developers/applications' target='_blank'>Discord Developer Portal</a> 获取 Bot Token",
        json_schema_extra=ExtraField(
            required=True,
            i18n_category=i18n_text(zh_CN="Bot 配置", en_US="Bot Settings"),
            i18n_title=i18n_text(zh_CN="机器人令牌", en_US="Bot Token"),
            i18n_description=i18n_text(
                zh_CN="从 <a href='https://discord.com/developers/applications' target='_blank'>Discord Developer Portal</a> 获取 Bot Token",
                en_US="Get the Bot Token from the <a href='https://discord.com/developers/applications' target='_blank'>Discord Developer Portal</a>.",
            ),
        ).model_dump(),
    )

    PROXY_URL: str = Field(
        default="",
        title="代理地址",
        description="可选，Discord Gateway/API 连接使用的代理地址，例如 http://127.0.0.1:7890",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="代理", en_US="Proxy"),
            i18n_title=i18n_text(zh_CN="代理地址", en_US="Proxy URL"),
            i18n_description=i18n_text(
                zh_CN="可选，Discord Gateway/API 连接使用的代理地址，例如 http://127.0.0.1:7890",
                en_US="Optional proxy used for Discord Gateway/API connections, for example http://127.0.0.1:7890.",
            ),
        ).model_dump(),
    )

    PROXY_USERNAME: str = Field(
        default="",
        title="代理用户名",
        description="可选，代理认证用户名",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="代理", en_US="Proxy"),
            i18n_title=i18n_text(zh_CN="代理用户名", en_US="Proxy Username"),
            i18n_description=i18n_text(
                zh_CN="可选，代理认证用户名",
                en_US="Optional username used for proxy authentication.",
            ),
        ).model_dump(),
    )

    PROXY_PASSWORD: str = Field(
        default="",
        title="代理密码",
        description="可选，代理认证密码",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="代理", en_US="Proxy"),
            i18n_title=i18n_text(zh_CN="代理密码", en_US="Proxy Password"),
            i18n_description=i18n_text(
                zh_CN="可选，代理认证密码",
                en_US="Optional password used for proxy authentication.",
            ),
        ).model_dump(),
    )
