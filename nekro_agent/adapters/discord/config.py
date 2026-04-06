from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig


class DiscordConfig(BaseAdapterConfig):
    """Discord 适配器配置"""

    BOT_TOKEN: str = Field(
        default="",
        title="机器人令牌",
        description="从 <a href='https://discord.com/developers/applications' target='_blank'>Discord Developer Portal</a> 获取 Bot Token",
    )

    PROXY_URL: str = Field(
        default="",
        title="代理地址",
        description="可选，Discord Gateway/API 连接使用的代理地址，例如 http://127.0.0.1:7890",
    )

    PROXY_USERNAME: str = Field(
        default="",
        title="代理用户名",
        description="可选，代理认证用户名",
    )

    PROXY_PASSWORD: str = Field(
        default="",
        title="代理密码",
        description="可选，代理认证密码",
    )
