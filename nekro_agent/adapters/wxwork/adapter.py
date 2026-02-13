
"""
企业微信智能机器人适配器

支持企业微信的自定义智能机器人功能
"""

from typing import List, Optional, Type

from fastapi import APIRouter

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger

from .config import WxWorkConfig
from .crypto import WxWorkBotCrypt


logger = get_sub_logger("adapter.wxwork")
class WxWorkAdapter(BaseAdapter[WxWorkConfig]):
    """企业微信智能机器人适配器"""

    crypto: Optional[WxWorkBotCrypt]

    def __init__(self, config_cls: Type[WxWorkConfig] = WxWorkConfig):
        super().__init__(config_cls)

        # 初始化加密工具
        if not self.config.TOKEN or not self.config.ENCODING_AES_KEY:
            logger.warning("企业微信智能机器人未完全配置，需要设置 TOKEN 和 ENCODING_AES_KEY")
            self.crypto = None
        else:
            self.crypto = WxWorkBotCrypt(
                token=self.config.TOKEN,
                encoding_aes_key=self.config.ENCODING_AES_KEY,
            )
            logger.info("企业微信智能机器人加密工具初始化成功")

    @property
    def key(self) -> str:
        return "wxwork"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="企业微信智能机器人",
            description="连接到企业微信平台的智能机器人适配器，支持在企业内部与成员进行交互",
            version="1.0.0",
            author="KroMiose",
            homepage="https://github.com/KroMiose/nekro-agent",
            tags=["wxwork", "wechat", "企业微信", "智能机器人", "chat", "im"],
        )

    def get_adapter_router(self) -> APIRouter:
        """获取适配器路由"""
        from .routers import router, set_adapter

        # 将当前适配器实例传递给路由模块
        set_adapter(self)

        return router

    async def init(self) -> None:
        """初始化适配器"""
        if not self.crypto:
            logger.warning("企业微信智能机器人未完全配置，跳过初始化")
            return

        logger.info(f"企业微信智能机器人适配器 [{self.key}] 已初始化")
        logger.info("请在企业微信后台配置回调 URL:")
        logger.info("  - URL: http://your-domain/adapters/wxwork/callback")
        logger.info(f"  - Token: {self.config.TOKEN}")
        logger.info(f"  - EncodingAESKey: {self.config.ENCODING_AES_KEY}")

    async def cleanup(self) -> None:
        """清理适配器"""
        logger.info("企业微信智能机器人适配器已清理")

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到企业微信

        注意：企业微信智能机器人目前只支持被动回复模式，
        不支持主动推送消息。需要在接收到用户消息时才能回复。

        Args:
            request: 协议端发送请求

        Returns:
            PlatformSendResponse: 发送结果
        """
        logger.warning("企业微信智能机器人暂不支持主动推送消息，只支持被动回复")
        return PlatformSendResponse(
            success=False,
            error_message="企业微信智能机器人只支持被动回复模式，不支持主动推送",
        )

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息

        注意：企业微信智能机器人 API 较为简单，可能无法获取完整的机器人信息
        """
        return PlatformUser(
            platform_name="wxwork",
            user_id="bot",
            user_name="企业微信智能机器人",
            user_avatar="",
        )

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        """获取用户信息

        注意：企业微信智能机器人 API 较为简单，可能无法获取详细的用户信息
        """
        return PlatformUser(
            platform_name="wxwork",
            user_id=user_id,
            user_name=user_id,  # 暂时使用 user_id 作为用户名
            user_avatar="",
        )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        from nekro_agent.schemas.chat_message import ChatType

        return PlatformChannel(
            channel_id=channel_id,
            channel_name=channel_id,  # 暂时使用 channel_id 作为频道名
            channel_type=ChatType.PRIVATE,  # 智能机器人通常是私聊场景
        )
