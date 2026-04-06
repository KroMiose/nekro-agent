from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig, adapter_extra_field


class DiscordConfig(BaseAdapterConfig):
    """Discord 适配器配置"""

    BOT_TOKEN: str = Field(
        default="",
        title="机器人令牌",
        description="从 <a href='https://discord.com/developers/applications' target='_blank'>Discord Developer Portal</a> 获取 Bot Token",
        json_schema_extra=adapter_extra_field(
            title_zh="机器人令牌",
            title_en="Bot Token",
            description_zh="从 <a href='https://discord.com/developers/applications' target='_blank'>Discord Developer Portal</a> 获取 Bot Token",
            description_en="Get the Bot Token from the <a href='https://discord.com/developers/applications' target='_blank'>Discord Developer Portal</a>.",
            category_zh="Bot 配置",
            category_en="Bot Settings",
            required=True,
        ),
    )

    PROXY_URL: str = Field(
        default="",
        title="代理地址",
        description="可选，Discord Gateway/API 连接使用的代理地址，例如 http://127.0.0.1:7890",
        json_schema_extra=adapter_extra_field(
            title_zh="代理地址",
            title_en="Proxy URL",
            description_zh="可选，Discord Gateway/API 连接使用的代理地址，例如 http://127.0.0.1:7890",
            description_en="Optional proxy used for Discord Gateway/API connections, for example http://127.0.0.1:7890.",
            category_zh="代理",
            category_en="Proxy",
        ),
    )

    PROXY_USERNAME: str = Field(
        default="",
        title="代理用户名",
        description="可选，代理认证用户名",
        json_schema_extra=adapter_extra_field(
            title_zh="代理用户名",
            title_en="Proxy Username",
            description_zh="可选，代理认证用户名",
            description_en="Optional username used for proxy authentication.",
            category_zh="代理",
            category_en="Proxy",
        ),
    )

    PROXY_PASSWORD: str = Field(
        default="",
        title="代理密码",
        description="可选，代理认证密码",
        json_schema_extra=adapter_extra_field(
            title_zh="代理密码",
            title_en="Proxy Password",
            description_zh="可选，代理认证密码",
            description_en="Optional password used for proxy authentication.",
            category_zh="代理",
            category_en="Proxy",
        ),
    )
