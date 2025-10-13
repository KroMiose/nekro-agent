from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig


class WxWorkConfig(BaseAdapterConfig):
    """企业微信智能机器人适配器配置"""

    TOKEN: str = Field(
        default="",
        title="Token",
        description="企业微信智能机器人后台配置的 Token，用于验证请求来源",
    )
    
    ENCODING_AES_KEY: str = Field(
        default="",
        title="EncodingAESKey",
        description="企业微信智能机器人后台配置的 EncodingAESKey（43位随机字符串），用于消息加解密",
    )

