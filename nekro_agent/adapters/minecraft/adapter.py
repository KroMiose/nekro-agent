import asyncio
import json
import os
import re
import websockets
from typing import Any, Dict, List, Optional, Type

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

    ENABLE_QUEQIAO_V2: bool = Field(
        default=False,
        title="启用 Queqiao V2 协议",
        description="为该服务器启用 Queqiao V2（开=V2，关=V1；关闭时下面的 QUEQIAO_* 配置会被忽略）",
    )
    QUEQIAO_WS_URL: str = Field(
        default="ws://localhost:8080",
        title="Queqiao V2 WebSocket 地址",
        description="Queqiao 插件的 WebSocket 服务地址（仅该服务器启用 V2 时生效，未启用将忽略）",
    )
    QUEQIAO_TOKEN: str = Field(
        default="",
        title="Queqiao V2 Token",
        description="连接 Queqiao 的认证 Token（仅该服务器启用 V2 时生效，未启用将忽略）",
    )
    QUEQIAO_CLIENT_NAME: str = Field(
        default="nekro-agent",
        title="Queqiao V2 客户端名称",
        description="连接时使用的客户端名称 (x-self-name，仅该服务器启用 V2 时生效，未启用将忽略)",
    )
    QUEQIAO_SELF_ID: str = Field(
        default="",
        title="Queqiao V2 自身标识符",
        description=(
            "用于识别自身消息的稳定标识符（严格匹配 player.uuid）；"
            "留空则不判定为自身消息"
        ),
    )
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
        description="在这里配置你的 Minecraft 服务器（每个服务器可选择 V1/V2；未启用 V2 时可忽略 QUEQIAO_* 字段）",
        json_schema_extra=ExtraField(
            is_need_restart= True,
        ).model_dump(),
    )
    MINECRAFT_WS_URLS: str = Field(
        default="{}",
        title="Minecraft 服务器 WebSocket 地址",
        description="Minecraft 服务器 WebSocket 地址，可配置多个服务器（仅 V1 模式使用）",
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
        description="用于验证连接（仅 V1 模式使用，所有 V1 服务器共用）",
        json_schema_extra=ExtraField(
            load_to_nonebot_env=True,
            load_nbenv_as="minecraft_access_token",
        ).model_dump(),
    )
    MINECRAFT_SERVER_RCON: str = Field(
        default="{}",
        title="Minecraft 服务器 RCON 地址",
        description="Minecraft 服务器 RCON 地址，用于远程执行指令（仅 V1 模式使用）",
        json_schema_extra=ExtraField(
            load_to_nonebot_env=True,
            load_nbenv_as="minecraft_server_rcon",
            is_textarea=True,
            is_hidden=True,
        ).model_dump(),
    )
    # V2 连接信息已下沉到 ServerConfig

    @model_validator(mode="after")
    def _convert_servers_to_legacy_config(self):
        """将 SERVERS 转换为旧版配置项"""
        # 仅转换 V1 服务器，适配 nonebot-adapter-minecraft 所需的旧版配置
        servers = self.SERVERS
        if not servers:
            return self

        ws_urls: Dict[str, List[str]] = {}
        rcon_config: Dict[str, Dict] = {}

        for server in servers:
            if not server.SERVER_NAME:
                continue
            if server.ENABLE_QUEQIAO_V2:
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
        # Queqiao V2 related
        self._running = False
        self._connect_tasks: Dict[str, asyncio.Task] = {}
        self._reconnect_interval = 5
        self._v2_ws: Dict[str, Any] = {}

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
        v2_servers = self._get_v2_servers()
        if v2_servers:
            logger.info("Minecraft Adapter: 检测到 V2 服务器配置，正在初始化 WebSocket 连接...")
            self._running = True
            seen_names: set[str] = set()
            for server in v2_servers:
                if server.SERVER_NAME in seen_names:
                    logger.error(
                        "Minecraft Adapter: 检测到重复的 V2 服务器名称 %s，将跳过该配置",
                        server.SERVER_NAME,
                    )
                    continue
                seen_names.add(server.SERVER_NAME)
                self._connect_tasks[server.SERVER_NAME] = self._create_connect_task(server)

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
                logger.info(f"Minecraft 适配器 [{self.key}] 已加载 (Legacy/NineBot Mode)")
                register_matcher(self)
            else:
                if not v2_servers:
                    logger.warning("Minecraft 适配器 由于以下几个配置项错误未能加载 (V1)")
                    if not ws_urls_valid:
                        logger.warning("- minecraft_ws_urls 应该是一个字典")
                    if not token_valid:
                        logger.warning("- minecraft_access_token 应该是一个字符串")
                    if not rcon_valid:
                        logger.warning("- minecraft_server_rcon 应该是一个字典")
        except Exception as e:
            logger.error(f"Minecraft 适配器初始化失败: {e}", exc_info=True)
            logger.warning("Minecraft 适配器未能加载")

    def _create_connect_task(self, server: ServerConfig):
        return asyncio.create_task(self._queqiao_loop(server))

    async def cleanup(self) -> None:
        """清理适配器"""
        if self._running:
            import asyncio
            self._running = False
            for ws in list(self._v2_ws.values()):
                try:
                    await ws.close()
                except Exception:
                    pass
            for task in list(self._connect_tasks.values()):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        return

    def _get_v2_servers(self) -> List[ServerConfig]:
        return [
            server for server in self.config.SERVERS if server.SERVER_NAME and server.ENABLE_QUEQIAO_V2
        ]

    def _get_server_config(self, server_name: str) -> Optional[ServerConfig]:
        for server in self.config.SERVERS:
            if server.SERVER_NAME == server_name:
                return server
        return None

    def _extract_text_from_component(self, raw: Any) -> str:
        if isinstance(raw, list):
            return "".join(
                str(item.get("text", "")) for item in raw if isinstance(item, dict)
            )
        if isinstance(raw, dict):
            return str(raw.get("text", ""))
        if raw is None:
            return ""
        return str(raw)

    def _resolve_v2_is_self(
        self, player: Dict[str, Any], server_config: Optional[ServerConfig]
    ) -> bool:
        if not server_config:
            return False
        self_id = str(server_config.QUEQIAO_SELF_ID).strip()
        if not self_id:
            return False
        player_uuid = player.get("uuid")
        if not player_uuid:
            return False
        return str(player_uuid).lower() == self_id.lower()

    def _parse_v2_chat_event(
        self,
        data: Dict[str, Any],
        server_config: Optional[ServerConfig],
    ) -> Optional[Dict[str, Any]]:
        post_type = data.get("post_type")
        event_name = data.get("event_name") or None
        sub_type = data.get("sub_type") or None
        if post_type != "message":
            return None
        valid_message_events = {
            ("PlayerChatEvent", "player_chat"),
        }
        if (event_name, sub_type) not in valid_message_events:
            return None

        server_name = data.get("server_name") or (
            server_config.SERVER_NAME if server_config else None
        )
        if not server_name:
            server_name = "default"
        player = data.get("player") if isinstance(data.get("player"), dict) else {}
        sender_name = str(player.get("nickname") or player.get("name") or "Unknown")
        sender_id = str(player.get("uuid") or sender_name)

        raw_msg = data.get("message")
        if raw_msg is None:
            raw_msg = data.get("raw_message")
        if raw_msg is None:
            raw_msg = data.get("rawMessage")
        text_content = self._extract_text_from_component(raw_msg)

        return {
            "channel_id": str(server_name),
            "channel_name": str(server_name),
            "sender_id": sender_id,
            "sender_name": sender_name,
            "message_id": str(data.get("message_id", "")),
            "text": text_content,
            "is_self": self._resolve_v2_is_self(player, server_config),
        }

    def _build_v2_message_components(self, request: PlatformSendRequest) -> List[Dict[str, Any]]:
        components: List[Dict[str, Any]] = []
        for seg in request.segments:
            if seg.type == PlatformSendSegmentType.TEXT:
                text = self._remove_at_mentions(seg.content)
                if text:
                    components.append({"text": text})
            elif seg.type == PlatformSendSegmentType.AT and seg.at_info:
                nickname = seg.at_info.nickname or seg.at_info.platform_user_id
                text = self._remove_at_mentions(f"@{nickname}")
                if text:
                    components.append({"text": text})
        return components

    async def _queqiao_loop(self, server: ServerConfig):
        """Queqiao V2 WebSocket Loop"""
        import asyncio
        import websockets

        server_name = server.SERVER_NAME or "default"

        while self._running:
            try:
                headers = {
                    "x-self-name": server.QUEQIAO_CLIENT_NAME
                }
                if server.QUEQIAO_TOKEN:
                    headers["Authorization"] = f"Bearer {server.QUEQIAO_TOKEN}"

                logger.info(
                    f"Queqiao 正在连接到 {server.QUEQIAO_WS_URL} (server={server_name})..."
                )
                async with websockets.connect(
                    server.QUEQIAO_WS_URL, additional_headers=headers
                ) as ws:
                    self._v2_ws[server_name] = ws
                    logger.info(f"Queqiao V2 连接成功 (server={server_name})")
                    await self._recv_loop(ws, server)
            except Exception as e:
                logger.warning(
                    "Queqiao 连接断开或失败 (server=%s): %s，%s秒后重连",
                    server_name,
                    e,
                    self._reconnect_interval,
                )
            finally:
                self._v2_ws.pop(server_name, None)
            
            if self._running:
                await asyncio.sleep(self._reconnect_interval)

    async def _recv_loop(self, ws: Any, server_config: ServerConfig):
        """Recv Loop for Queqiao"""
        # 延迟导入以避免循环依赖
        from nekro_agent.adapters.interface.collector import collect_message
        from nekro_agent.schemas.chat_message import ChatMessageSegment, ChatMessageSegmentType
        from nekro_agent.adapters.interface.schemas.platform import PlatformMessage

        async for message in ws:
            try:
                data = json.loads(message)
                logger.debug(f"Queqiao V2 收到消息: {data}")

                parsed = self._parse_v2_chat_event(data, server_config)
                if not parsed:
                    continue

                platform_user = PlatformUser(
                    platform_name=self.key,
                    user_id=parsed["sender_id"],
                    user_name=parsed["sender_name"],
                    user_avatar="",
                )

                platform_channel = PlatformChannel(
                    platform_name=self.key,
                    channel_id=parsed["channel_id"],
                    channel_name=parsed["channel_name"],
                    channel_type=ChatType.GROUP,
                )

                msg_segments = [
                    ChatMessageSegment(
                        type=ChatMessageSegmentType.TEXT,
                        text=parsed["text"],
                    ),
                ]

                platform_message = PlatformMessage(
                    message_id=parsed["message_id"],
                    sender_id=parsed["sender_id"],
                    sender_name=parsed["sender_name"],
                    content_text=parsed["text"],
                    content_data=msg_segments,
                    sender_nickname=parsed["sender_name"],
                    is_self=parsed["is_self"],
                    is_tome=False,
                )

                await collect_message(self, platform_channel, platform_user, platform_message)
                    
            except json.JSONDecodeError:
                logger.warning(f"Queqiao V2 收到非 JSON 消息: {message}")
            except Exception as e:
                logger.error(f"Queqiao V2 处理消息异常: {e}", exc_info=True)

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
        _, target = self.parse_chat_key(request.chat_key)
        server_config = self._get_server_config(target)
        use_v2 = bool(server_config and server_config.ENABLE_QUEQIAO_V2)

        if use_v2:
            ws = self._v2_ws.get(server_config.SERVER_NAME)
            if not ws:
                return PlatformSendResponse(
                    success=False,
                    error_message="Queqiao V2 未连接",
                )
            try:
                from websockets.protocol import State
            except Exception:
                State = None
            if State is not None and ws.state != State.OPEN:
                return PlatformSendResponse(success=False, error_message="Queqiao V2 未连接")
            try:
                if len(request.segments) == 1 and request.segments[0].type == PlatformSendSegmentType.TEXT:
                    raw_payload = request.segments[0].content.strip()
                    if raw_payload.startswith("{"):
                        try:
                            payload = json.loads(raw_payload)
                            if isinstance(payload, dict) and payload.get("api") and payload.get("data") is not None:
                                await ws.send(json.dumps(payload))
                                return PlatformSendResponse(success=True)
                        except json.JSONDecodeError:
                            pass

                msg_components = self._build_v2_message_components(request)
                if not msg_components:
                    return PlatformSendResponse(success=False, error_message="Queqiao V2 发送内容为空")

                # 默认只实现 broadcast (对应 chat_key 无特定区分或 'broadcast' 关键字)
                # 后续可根据 request.chat_key 区分私聊 (send_private_msg)

                # Assume if target is not a known generic, it's a player? 
                # For now simplify: All messages are broadcast unless specifically marked

                payload = {
                    "api": "broadcast",
                    "data": {
                        "message": msg_components
                    }
                }
                
                import json
                await ws.send(json.dumps(payload))
                return PlatformSendResponse(success=True)
            except Exception as e:
                logger.error(f"Queqiao V2 发送失败: {e}")
                return PlatformSendResponse(success=False, error_message=str(e))
                
        # Legacy/NoneBot Logic
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
