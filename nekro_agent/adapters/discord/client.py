import asyncio
from typing import TYPE_CHECKING

from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.extra import PlatformMessageExt
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformMessage,
    PlatformUser,
)
from nekro_agent.core.logger import logger
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)

if TYPE_CHECKING:
    from .adapter import DiscordAdapter


try:
    import discord
except ImportError as e:
    raise ImportError("The 'discord' package is not installed. Please install it with: poetry install -E discord") from e


class DiscordClient:
    """
    一个用于管理与 Discord Gateway 连接的客户端。
    """

    def __init__(self, token: str, adapter: "DiscordAdapter"):
        self._token = token
        self._adapter = adapter
        self._intents = discord.Intents.default()
        self._intents.message_content = True  # 需要开启消息内容权限
        self._client = discord.Client(intents=self._intents)

        self._setup_events()

    @property
    def user(self) -> discord.ClientUser | None:
        return self._client.user

    def get_channel(self, channel_id: int) -> discord.abc.GuildChannel | discord.Thread | discord.abc.PrivateChannel | None:
        return self._client.get_channel(channel_id)

    def get_user(self, user_id: int) -> discord.User | None:
        return self._client.get_user(user_id)

    async def fetch_user(self, user_id: int) -> discord.User:
        return await self._client.fetch_user(user_id)

    async def fetch_channel(self, channel_id: int) -> discord.abc.GuildChannel | discord.Thread | discord.abc.PrivateChannel:
        return await self._client.fetch_channel(channel_id)

    def _setup_events(self):
        @self._client.event
        async def on_ready():
            logger.success(f"Discord Bot is ready. Logged in as {self._client.user}")

        @self._client.event
        async def on_message(message: discord.Message):
            # 忽略来自 bot 自身的消息
            if message.author == self._client.user:
                return

            chat_key = self._adapter.build_chat_key(str(message.channel.id))
            segments: list[ChatMessageSegment] = []
            content_text = message.content

            # 1. 处理附件
            for attachment in message.attachments:
                file_name = attachment.filename
                if attachment.content_type and "image" in attachment.content_type:
                    segment = await ChatMessageSegmentImage.create_from_url(
                        url=attachment.url,
                        from_chat_key=chat_key,
                        file_name=file_name,
                    )
                else:
                    segment = await ChatMessageSegmentFile.create_from_url(
                        url=attachment.url,
                        from_chat_key=chat_key,
                        file_name=file_name,
                    )
                segments.append(segment)
                # 将文件信息附加到主文本内容后，确保 Agent 能感知到
                if segment.text not in content_text:
                    content_text += f" {segment.text}"

            # 2. 处理文本内容
            if message.content:
                segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=message.content))

            if not segments:
                logger.debug("空消息，已忽略")
                return

            # 3. 构建 PlatformUser
            user = PlatformUser(
                platform_name="discord",
                user_id=str(message.author.id),
                user_name=message.author.display_name,
                user_avatar=str(message.author.display_avatar.url),
            )

            # 4. 构建 PlatformChannel
            channel_type = ChatType.PRIVATE if isinstance(message.channel, discord.DMChannel) else ChatType.GROUP
            channel = PlatformChannel(
                channel_id=str(message.channel.id),
                channel_name=str(message.channel),  # For DMs, this will be the user's name
                channel_type=channel_type,
            )

            # 5. 构建 PlatformMessage
            ref_msg_id = str(message.reference.message_id) if message.reference else ""
            platform_message = PlatformMessage(
                message_id=str(message.id),
                sender_id=str(message.author.id),
                sender_name=message.author.display_name,
                content_text=content_text.strip(),
                content_data=segments,
                is_tome=self._client.user in message.mentions or isinstance(message.channel, discord.DMChannel),
                sender_nickname=message.author.display_name,
                ext_data=PlatformMessageExt(ref_msg_id=ref_msg_id),
            )

            # 6. 分发消息
            await collect_message(
                adapter=self._adapter,
                platform_channel=channel,
                platform_user=user,
                platform_message=platform_message,
            )

    async def start(self):
        """启动客户端并连接到 Discord"""
        logger.info("Starting Discord client...")
        # discord.py 的 login 和 connect 方法是阻塞的，
        # 需要使用 start 方法在后台任务中运行它。
        # start 会自动处理 login 和 connect。
        asyncio.create_task(self._client.start(self._token))

    async def stop(self):
        """关闭客户端连接"""
        logger.info("Stopping Discord client...")
        await self._client.close()
