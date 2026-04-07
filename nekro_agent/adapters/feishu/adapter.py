from pathlib import Path
from typing import List, Optional, Type

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import ChatType

from .client import FeishuClient
from .config import FeishuConfig
from .tools import SegAt, parse_at_from_text

logger = get_sub_logger("adapter.feishu")


class FeishuAdapter(BaseAdapter[FeishuConfig]):
    client: Optional[FeishuClient]

    def __init__(self, config_cls: Type[FeishuConfig] = FeishuConfig):
        super().__init__(config_cls)
        if not self.config.APP_ID or not self.config.APP_SECRET:
            logger.warning("飞书适配器未启用，需要设置 APP_ID 和 APP_SECRET")
            self.client = None
            return
        self.client = FeishuClient(
            app_id=self.config.APP_ID,
            app_secret=self.config.APP_SECRET,
            adapter=self,
        )

    async def init(self) -> None:
        if self.client is not None:
            await self.client.start()

    async def cleanup(self) -> None:
        if self.client is not None:
            await self.client.stop()

    @property
    def key(self) -> str:
        return "feishu"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="飞书",
            description="飞书开放平台适配器，通过 WebSocket 长连接接收和发送消息，支持群聊和私聊。",
            version="1.0.0",
            author="NekroAI",
            homepage="https://github.com/KroMiose/nekro-agent",
            tags=["feishu", "lark", "im"],
        )

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "群聊: feishu-group_{chat_id}（chat_id 形如 oc_xxx）",
            "私聊: feishu-private_{open_id}（open_id 形如 ou_xxx）",
        ]

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        if self.client is None:
            error_msg = "飞书客户端未初始化，请检查 APP_ID 和 APP_SECRET 配置"
            logger.warning(error_msg)
            return PlatformSendResponse(success=False, error_message=error_msg)

        try:
            _, channel_id = self.parse_chat_key(request.chat_key)

            # 从 channel_id 解析 receive_id 和 receive_id_type
            if channel_id.startswith("group_"):
                receive_id = channel_id[len("group_") :]
                receive_id_type = "chat_id"
            elif channel_id.startswith("private_"):
                receive_id = channel_id[len("private_") :]
                receive_id_type = "open_id"
            else:
                error_msg = f"无法解析 channel_id: {channel_id}"
                logger.warning(error_msg)
                return PlatformSendResponse(success=False, error_message=error_msg)

            # 合并文本段 + AT 段为一条消息
            content_parts: List[str] = []
            last_message_id: Optional[str] = None

            for seg in request.segments:
                if seg.type == PlatformSendSegmentType.TEXT:
                    parsed_segments = parse_at_from_text(seg.content)
                    for parsed_seg in parsed_segments:
                        if isinstance(parsed_seg, str):
                            content_parts.append(parsed_seg)
                        elif isinstance(parsed_seg, SegAt):
                            if self.config.SESSION_ENABLE_AT:
                                content_parts.append(f'<at user_id="{parsed_seg.platform_user_id}"></at>')
                            else:
                                content_parts.append(parsed_seg.platform_user_id)

                elif seg.type == PlatformSendSegmentType.AT:
                    if seg.at_info:
                        if self.config.SESSION_ENABLE_AT:
                            content_parts.append(f'<at user_id="{seg.at_info.platform_user_id}"></at>')
                        else:
                            content_parts.append(seg.at_info.nickname or seg.at_info.platform_user_id)

                elif seg.type == PlatformSendSegmentType.IMAGE:
                    # 先发送已累积的文本
                    if content_parts:
                        text = "".join(content_parts).strip()
                        if text:
                            last_message_id = await self.client.send_text_message(receive_id, receive_id_type, text)
                        content_parts.clear()

                    if seg.file_path:
                        image_bytes = Path(seg.file_path).read_bytes()
                        image_key = await self.client.upload_image(image_bytes)
                        last_message_id = await self.client.send_image_message(receive_id, receive_id_type, image_key)

                elif seg.type == PlatformSendSegmentType.FILE:
                    # 先发送已累积的文本
                    if content_parts:
                        text = "".join(content_parts).strip()
                        if text:
                            last_message_id = await self.client.send_text_message(receive_id, receive_id_type, text)
                        content_parts.clear()

                    if seg.file_path:
                        file_path = Path(seg.file_path)
                        file_bytes = file_path.read_bytes()
                        file_key = await self.client.upload_file(file_bytes, file_path.name)
                        last_message_id = await self.client.send_file_message(receive_id, receive_id_type, file_key)

            # 发送剩余的文本
            if content_parts:
                text = "".join(content_parts).strip()
                if text:
                    last_message_id = await self.client.send_text_message(receive_id, receive_id_type, text)

            return PlatformSendResponse(success=True, message_id=last_message_id)

        except Exception as e:
            logger.exception(f"发送消息到飞书失败 {request.chat_key}: {e}")
            return PlatformSendResponse(success=False, error_message=str(e))

    async def get_self_info(self) -> PlatformUser:
        if self.client is None:
            raise RuntimeError("飞书客户端未初始化，请检查 APP_ID 和 APP_SECRET 配置")
        if not self.client.bot_info:
            raise RuntimeError("飞书机器人信息尚未就绪")
        return self.client.bot_info

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        if self.client is None:
            raise RuntimeError("飞书客户端未初始化，请检查 APP_ID 和 APP_SECRET 配置")

        user_info = await self.client.get_user_info(user_id)
        return PlatformUser(
            platform_name="feishu",
            user_id=user_id,
            user_name=user_info.get("name", user_id),
            user_avatar=user_info.get("avatar", {}).get("avatar_72", ""),
        )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        if self.client is None:
            raise RuntimeError("飞书客户端未初始化，请检查 APP_ID 和 APP_SECRET 配置")

        if channel_id.startswith("group_"):
            chat_id = channel_id[len("group_") :]
            chat_info = await self.client.get_chat_info(chat_id)
            return PlatformChannel(
                channel_id=channel_id,
                channel_name=chat_info.get("name", channel_id),
                channel_type=ChatType.GROUP,
            )
        elif channel_id.startswith("private_"):
            open_id = channel_id[len("private_") :]
            user_info = await self.client.get_user_info(open_id)
            return PlatformChannel(
                channel_id=channel_id,
                channel_name=user_info.get("name", channel_id),
                channel_type=ChatType.PRIVATE,
            )
        else:
            return PlatformChannel(
                channel_id=channel_id,
                channel_name=channel_id,
                channel_type=ChatType.UNKNOWN,
            )

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:
        """为消息添加或移除处理中表情回应"""
        if self.client is None:
            logger.warning("飞书客户端未初始化，请检查 APP_ID 和 APP_SECRET 配置")
            return False

        try:
            if status:
                reaction_id = await self.client.add_message_reaction(message_id, "THUMBSUP")
                return reaction_id is not None
            else:
                # 飞书移除 reaction 需要 reaction_id，此处尝试添加后移除的模式较复杂
                # 简化处理：不主动移除 reaction
                return True
        except Exception as e:
            logger.warning(f"设置消息表情回应失败 {message_id}: {e}")
            return False
