import json
import os
import re
from typing import Dict, List, Optional, Type

import nonebot
from fastapi import APIRouter
from nonebot.adapters.minecraft import Bot, Message, MessageSegment
from nonebot.adapters.minecraft.model import ClickEvent, HoverEvent, TextColor
from pydantic import BaseModel, Field, model_validator

from nekro_agent.adapters.interface.base import (
    AdapterMetadata,
    BaseAdapter,
    BaseAdapterConfig,
)
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core import logger
from nekro_agent.core.config import ExtraField
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.schemas.chat_message import ChatType


class ServerConfig(BaseModel):
    """服务器配置"""

    SERVER_NAME: str = Field(
        default="",
        title="服务器名称",
        description="服务器名称",
    )
    SERVER_WS_URL: str = Field(
        default="",
        title="服务器WebSocket地址",
        description="服务器WebSocket地址",
    )
    IS_SERVER_RCON: bool = Field(
        default=False,
        title="是否启用RCON",
        description="是否启用RCON",
    )
    SERVER_RCON_PORT: int = Field(
        default=25575,
        title="服务器RCON端口",
        description="服务器RCON端口",
    )
    SERVER_RCON_PASSWORD: str = Field(
        default="",
        title="服务器RCON密码",
        description="服务器RCON密码",
    )


class MinecraftConfig(BaseAdapterConfig):
    """Minecraft 适配器配置"""

    SESSION_ENABLE_AT: bool = Field(
        default=False,
        title="启用 @用户 功能",
        description="关闭后 AI 发送的 @用户 消息将被解析为纯文本用户名，避免反复打扰用户",
        json_schema_extra=ExtraField(
            is_hidden=True,
        ).model_dump(),
    )
    SESSION_PROCESSING_WITH_EMOJI: bool = Field(
        default=False,
        title="显示处理中表情反馈",
        description="当 AI 开始处理消息时，对应消息会显示处理中表情反馈",
        json_schema_extra=ExtraField(
            is_hidden=True,
        ).model_dump(),
    )
    SERVERS: List[ServerConfig] = Field(
        default_factory=list,
        title="服务器列表",
        description="在这里配置你的 Minecraft 服务器",
    )
    MINECRAFT_WS_URLS: str = Field(
        default="{}",
        title="Minecraft 服务器 WebSocket 地址",
        description="Minecraft 服务器 WebSocket 地址，可配置多个服务器",
        json_schema_extra=ExtraField(
            load_to_nonebot_env=True,
            load_nbenv_as="minecraft_ws_urls",
            is_textarea=True,
            is_hidden=True,
        ).model_dump(),
    )
    MINECRAFT_ACCESS_TOKEN: str = Field(
        default="",
        title="Minecraft 服务器 WebSocket 认证密钥",
        description="用于验证连接",
        json_schema_extra=ExtraField(
            load_to_nonebot_env=True,
            load_nbenv_as="minecraft_access_token",
        ).model_dump(),
    )
    MINECRAFT_SERVER_RCON: str = Field(
        default="{}",
        title="Minecraft 服务器 RCON 地址",
        description="Minecraft 服务器 RCON 地址，用于远程执行指令",
        json_schema_extra=ExtraField(
            load_to_nonebot_env=True,
            load_nbenv_as="minecraft_server_rcon",
            is_textarea=True,
            is_hidden=True,
        ).model_dump(),
    )

    @model_validator(mode="after")
    def _convert_servers_to_legacy_config(self):
        """将 SERVERS 转换为旧版配置项"""
        servers = self.SERVERS
        if not servers:
            return self

        ws_urls: Dict[str, List[str]] = {}
        rcon_config: Dict[str, Dict] = {}

        for server in servers:
            if not server.SERVER_NAME:
                continue
            if server.SERVER_WS_URL:
                ws_urls[server.SERVER_NAME] = [server.SERVER_WS_URL]
            if server.IS_SERVER_RCON:
                rcon_config[server.SERVER_NAME] = {
                    "enable_rcon": server.IS_SERVER_RCON,
                    "rcon_port": server.SERVER_RCON_PORT,
                    "rcon_password": server.SERVER_RCON_PASSWORD,
                }
        self.MINECRAFT_WS_URLS = json.dumps(ws_urls)
        self.MINECRAFT_SERVER_RCON = json.dumps(rcon_config)

        return self


class MinecraftAdapter(BaseAdapter[MinecraftConfig]):
    """Minecraft 适配器"""

    def __init__(self, config_cls: Type[MinecraftConfig] = MinecraftConfig):
        """初始化Minecraft适配器"""
        super().__init__(config_cls)

    @property
    def key(self) -> str:
        return "minecraft"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="Minecraft",
            description="Minecraft 服务器适配器，通过 RCON 协议与游戏服务器通信，支持游戏内聊天互动",
            version="1.0.0",
            author="Zaxpris",
            homepage="https://github.com/nekro-agent/nekro-agent",
            tags=["minecraft", "rcon", "gaming", "chat", "server"],
        )

    @property
    def chat_key_rules(self) -> List[str]:
        # TODO: 根据 Minecraft 的实际情况修改
        return [
            "Server chat: `minecraft-servername` (where servername is the name of the Minecraft server)",
            "YOU CAN NOT USE ANY AT MESSAGES IN MINECRAFT SERVER CHAT!",
            "YOU CAN NOT SEND ANY PICTURES OR FILES IN MINECRAFT SERVER CHAT!",
        ]

    async def init(self) -> None:
        """初始化适配器"""
        try:
            driver = nonebot.get_driver()
            # 直接从 driver.config 获取配置
            minecraft_ws_urls = getattr(driver.config, "minecraft_ws_urls", None)
            minecraft_access_token = getattr(
                driver.config,
                "minecraft_access_token",
                "",
            )
            minecraft_server_rcon = getattr(driver.config, "minecraft_server_rcon", None)

            # 检查配置项类型是否正确
            ws_urls_valid = isinstance(minecraft_ws_urls, dict) and minecraft_ws_urls
            token_valid = isinstance(minecraft_access_token, str) and minecraft_access_token
            rcon_valid = isinstance(minecraft_server_rcon, dict) and minecraft_server_rcon

            if ws_urls_valid or (token_valid and rcon_valid):
                from nonebot.adapters.minecraft import (
                    Adapter as MinecraftNoneBotAdapter,  # Rename to avoid conflict
                )

                from .matchers.message import register_matcher
                from .matchers.notice import notice_manager

                driver.register_adapter(MinecraftNoneBotAdapter)
                logger.info(f"Minecraft 适配器 [{self.key}] 已加载")
                register_matcher(self)
            else:
                logger.warning("Minecraft 适配器 由于以下几个配置项错误未能加载")
                if not ws_urls_valid:
                    logger.warning("- minecraft_ws_urls 应该是一个字典")
                if not token_valid:
                    logger.warning("- minecraft_access_token 应该是一个字符串")
                if not rcon_valid:
                    logger.warning("- minecraft_server_rcon 应该是一个字典")
        except Exception as e:
            logger.error(f"Minecraft 适配器初始化失败: {e}", exc_info=True)
            logger.warning("Minecraft 适配器未能加载")

    async def cleanup(self) -> None:
        """清理适配器"""
        return

    def _remove_at_mentions(self, text: str) -> str:
        """移除文本中的特定格式的 @ 提及 (例如 [@id:123;nickname:test@] 或 [@id:123@])"""
        processed_text = re.sub(r"\[@(?:id:[^;@]+(?:;nickname:[^@]+)?|[^@\]]+)@\]", "", text)
        # 将多个空格替换为单个空格，并去除首尾空格
        return re.sub(r"\\s+", " ", processed_text).strip()

    async def _send_text(self, text: str, chat_key: str):
        """将文本消息通过 Bot 发送到 Minecraft 服务器"""
        from .core.bot import get_bot

        try:
            bot_instance: Optional[Bot] = get_bot(chat_key)
            if not bot_instance:
                logger.error(f"没有找到对应的 Minecraft 服务器: {chat_key}")
                return

            cleaned_text = self._remove_at_mentions(text)
            channel = await DBChatChannel.get_channel(chat_key)
            preset = await channel.get_preset()

            message_to_send = Message(
                [
                    MessageSegment.text(f"<{preset.name}>", color=TextColor.GREEN),
                    MessageSegment.text(
                        cleaned_text,
                    ),
                ],
            )
            await bot_instance.send_msg(message=message_to_send)

        except Exception as e:
            logger.error(f"发送消息时错误 ({chat_key}): {e}", exc_info=True)

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到 Minecraft 协议端"""
        for seg in request.segments:
            if seg.type == PlatformSendSegmentType.TEXT:
                await self._send_text(seg.content, request.chat_key)
        return PlatformSendResponse(success=True)

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        return PlatformUser(platform_name="Minecraft", user_id="MinecraftBot", user_name="MinecraftBot")

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        """获取用户(或者群聊用户)信息"""
        raise NotImplementedError

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息"""
        return PlatformChannel(channel_id=channel_id, channel_name=channel_id, channel_type=ChatType.GROUP)

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:  # noqa: ARG002
        """设置消息反应（可选实现）"""
        return True
