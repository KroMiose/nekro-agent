from pydantic import Field, SecretStr

from nekro_agent.adapters.interface.base import BaseAdapterConfig


class DiscordConfig(BaseAdapterConfig):
    """Discord 适配器配置"""

    BOT_TOKEN: str = Field(
        default="",
        title="Discord Bot Token",
        description="从 <a href='https://discord.com/developers/applications' target='_blank'>Discord Developer Portal</a> 获取你的 Bot Token",
    )
