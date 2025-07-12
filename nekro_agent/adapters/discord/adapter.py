from typing import List, Type

import discord
from nonebot import get_driver
from nonebot.drivers import Driver

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core.logger import logger

from .client import DiscordClient
from .config import DiscordConfig
from .tools import SegAt, parse_at_from_text


class DiscordAdapter(BaseAdapter[DiscordConfig]):
    def __init__(self, config_cls: Type[DiscordConfig] = DiscordConfig):
        super().__init__(config_cls)
        self.client = DiscordClient(
            token=self.config.BOT_TOKEN,
            adapter=self,
        )

    async def init(self) -> None:
        await self.client.start()

    async def cleanup(self) -> None:
        await self.client.stop()

    @property
    def key(self) -> str:
        return "discord"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="Discord",
            description="连接到 Discord 平台的适配器，允许通过 Bot 与服务器和用户进行交互。",
            version="1.0.0",
            author="KroMiose",
            homepage="https://github.com/KroMiose/nekro-agent",
            tags=["discord", "chat", "im"],
        )

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        try:
            _, channel_id = self.parse_chat_key(request.chat_key)
            channel = self.client.get_channel(int(channel_id))

            if not isinstance(channel, discord.abc.Messageable):
                error_msg = f"Channel {channel_id} is not a messageable channel."
                logger.warning(error_msg)
                return PlatformSendResponse(success=False, error_message=error_msg)

            content_parts: List[str] = []
            files_to_send: List[discord.File] = []

            for seg in request.segments:
                if seg.type == PlatformSendSegmentType.TEXT:
                    # 使用新的解析器将文本分解为字符串和 SegAt 对象
                    parsed_segments = parse_at_from_text(seg.content)
                    for parsed_seg in parsed_segments:
                        if isinstance(parsed_seg, str):
                            content_parts.append(parsed_seg)
                        elif isinstance(parsed_seg, SegAt):
                            content_parts.append(f"<@{parsed_seg.platform_user_id}>")
                elif seg.type == PlatformSendSegmentType.AT:
                    if seg.at_info:
                        content_parts.append(f"<@{seg.at_info.platform_user_id}>")
                elif seg.type in [PlatformSendSegmentType.IMAGE, PlatformSendSegmentType.FILE]:
                    if seg.file_path:
                        files_to_send.append(discord.File(seg.file_path))

            final_content = "".join(content_parts)

            if not final_content.strip() and not files_to_send:
                logger.info("Empty message, skipping send.")
                return PlatformSendResponse(success=True)

            # 准备发送参数
            send_kwargs: dict = {}
            if final_content.strip():
                send_kwargs["content"] = final_content
            if files_to_send:
                send_kwargs["files"] = files_to_send

            # 处理引用回复
            if request.ref_msg_id:
                try:
                    message_reference = discord.MessageReference(
                        message_id=int(request.ref_msg_id),
                        channel_id=int(channel_id),
                        fail_if_not_exists=False,
                    )
                    send_kwargs["reference"] = message_reference
                except (ValueError, TypeError):
                    logger.warning(f"Invalid ref_msg_id: {request.ref_msg_id}. Sending as a normal message.")

            sent_message = await channel.send(**send_kwargs)
            return PlatformSendResponse(success=True, message_id=str(sent_message.id))

        except Exception as e:
            logger.exception(f"Failed to send message to Discord channel {request.chat_key}: {e}")
            return PlatformSendResponse(success=False, error_message=str(e))

    async def get_self_info(self) -> PlatformUser:
        if not self.client.user:
            raise RuntimeError("Discord client is not ready yet.")
        user = self.client.user
        return PlatformUser(
            platform_name="discord",
            user_id=str(user.id),
            user_name=user.display_name,
            user_avatar=str(user.display_avatar.url),
        )

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:
        user = self.client.get_user(int(user_id))
        # If user is not in cache, try fetching from the channel (guild)
        if not user and channel_id:
            channel = self.client.get_channel(int(channel_id))
            if isinstance(channel, discord.abc.GuildChannel):
                member = channel.guild.get_member(int(user_id))
                if member:
                    user = member

        if not user:
            # As a last resort, fetch via API, which is a heavier operation
            try:
                user = await self.client.fetch_user(int(user_id))
            except discord.NotFound as e:
                raise ValueError(f"User with ID {user_id} not found.") from e

        return PlatformUser(
            platform_name="discord",
            user_id=str(user.id),
            user_name=user.display_name,
            user_avatar=str(user.display_avatar.url),
        )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        from nekro_agent.schemas.chat_message import ChatType

        channel = self.client.get_channel(int(channel_id))
        if not channel:
            try:
                channel = await self.client.fetch_channel(int(channel_id))
            except discord.NotFound as e:
                raise ValueError(f"Channel with ID {channel_id} not found.") from e

        channel_type = ChatType.PRIVATE if isinstance(channel, discord.DMChannel) else ChatType.GROUP
        channel_name = ""
        if isinstance(channel, discord.abc.GuildChannel):
            channel_name = channel.name
        elif isinstance(channel, discord.DMChannel):
            channel_name = channel.recipient.display_name if channel.recipient else "DM Channel"
        else:
            channel_name = str(channel)

        return PlatformChannel(
            channel_id=str(channel.id),
            channel_name=channel_name,
            channel_type=channel_type,
        )

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:
        """为消息添加或移除反应"""
        from nekro_agent.models.db_chat_message import DBChatMessage

        try:
            # 1. 通过 message_id 反向查询数据库获取 chat_key
            db_message = await DBChatMessage.get_or_none(message_id=message_id)
            if not db_message:
                logger.warning(f"Reaction failed: Message with ID {message_id} not found in DB.")
                return False

            # 2. 解析出 channel_id
            _, channel_id = self.parse_chat_key(db_message.chat_key)
            channel = self.client.get_channel(int(channel_id))

            if not isinstance(channel, discord.abc.Messageable):
                return False

            # 3. 获取消息对象
            message = await channel.fetch_message(int(message_id))

            # 4. 添加或移除反应
            processing_emoji = "⏳"
            if status:
                await message.add_reaction(processing_emoji)
            else:
                # 移除机器人自身的特定反应
                await message.clear_reaction(processing_emoji)

        except discord.errors.NotFound:
            logger.warning(f"Reaction failed: Message or Channel for {message_id} not found on Discord.")
            return False
        except Exception as e:
            logger.exception(f"Failed to set reaction for message {message_id}: {e}")
            return False
        else:
            return True
