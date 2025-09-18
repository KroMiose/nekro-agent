"""
Telegram 适配器配置
"""

from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig


class TelegramConfig(BaseAdapterConfig):
    """Telegram 适配器配置类"""
    
    BOT_TOKEN: str = Field(
        default="",
        title="Bot Token",
        description="Telegram Bot API Token",
        json_schema_extra={"is_secret": True},
    )
    
    @property
    def is_configured(self) -> bool:
        """检查配置是否完整"""
        return bool(self.BOT_TOKEN)