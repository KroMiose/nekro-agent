"""
Telegram 消息处理器
"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from telegram import (
    Audio,
    Document,
    Message,
    PhotoSize,
    Sticker,
    Update,
    Video,
    VideoNote,
    Voice,
)
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    from nekro_agent.adapters.telegram.adapter import TelegramAdapter

from nekro_agent.adapters.interface.schemas.platform import (
    ChatType,
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
)
from nekro_agent.tools.common_util import download_file_from_bytes


class MessageProcessor:
    """消息处理器"""

    def __init__(self, adapter: "TelegramAdapter"):
        self.adapter = adapter

    async def process_update(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """处理 Telegram 更新"""
        try:
            if update.message:
                await self._handle_message(update.message, context)
            elif update.edited_message:
                await self._handle_edited_message(update.edited_message, context)
            # 可以添加更多类型的处理，如 inline_query, callback_query 等
        except Exception as e:
            logger.error(f"处理 Telegram 更新时出错: {e}")

    async def _handle_message(
        self,
        message: Message,
        context: ContextTypes.DEFAULT_TYPE = None,
    ) -> None:
        """处理消息"""
        if not message.from_user:
            return

        # 构造平台用户信息
        platform_user = PlatformUser(
            platform_name=self.adapter.key,
            user_id=str(message.from_user.id),
            user_name=message.from_user.username or str(message.from_user.id),
            user_avatar="",
        )

        # 构造平台频道信息
        chat_type = (
            ChatType.PRIVATE if message.chat.type == "private" else ChatType.GROUP
        )
        platform_channel = PlatformChannel(
            platform_name=self.adapter.key,
            channel_id=f"{chat_type.value}_{message.chat.id}",
            channel_name=message.chat.title
            or message.chat.first_name
            or str(message.chat.id),
            channel_type=chat_type,
        )

        # 处理消息内容
        content_segments = await self._process_message_content(message)

        # 构造平台消息
        platform_message = PlatformMessage(
            message_id=str(message.message_id),
            sender_id=str(message.from_user.id),
            sender_name=message.from_user.first_name
            or message.from_user.username
            or str(message.from_user.id),
            content_text=self._extract_text_content(content_segments),
            content_data=content_segments,
            sender_nickname=message.from_user.first_name
            or message.from_user.username
            or str(message.from_user.id),
            is_self=message.from_user.id == context.bot.id
            if context and context.bot
            else False,
            is_tome=self._is_mentioned(message, context),
        )

        # 收集消息
        from nekro_agent.adapters.interface.collector import collect_message

        await collect_message(
            self.adapter,
            platform_channel,
            platform_user,
            platform_message,
        )

    async def _handle_edited_message(
        self,
        message: Message,
        context: ContextTypes.DEFAULT_TYPE = None,
    ) -> None:
        """处理编辑消息"""
        # 目前简单处理为新消息
        await self._handle_message(message, context)

    async def _process_message_content(
        self,
        message: Message,
    ) -> List[ChatMessageSegment]:
        """处理消息内容，转换为标准消息段"""
        segments: List[ChatMessageSegment] = []

        # 处理文本内容
        if message.text:
            segments.append(
                ChatMessageSegment(
                    type=ChatMessageSegmentType.TEXT,
                    text=message.text,
                ),
            )

        # 处理照片
        if message.photo:
            # 选择最大尺寸的照片
            largest_photo = max(message.photo, key=lambda p: p.file_size or 0)
            photo_bytes = await self._download_file_bytes(largest_photo.file_id)
            if photo_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                segment = await ChatMessageSegmentImage.create_from_bytes(
                    photo_bytes,
                    from_chat_key=chat_key,
                    file_name=f"photo_{largest_photo.file_id}.jpg",
                )
                segments.append(segment)

        # 处理文档
        if message.document:
            doc_bytes = await self._download_file_bytes(message.document.file_id)
            if doc_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    doc_bytes,
                    from_chat_key=chat_key,
                    file_name=message.document.file_name
                    or f"document_{message.document.file_id}",
                )
                segments.append(segment)

        # 处理视频
        if message.video:
            video_bytes = await self._download_file_bytes(message.video.file_id)
            if video_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    video_bytes,
                    from_chat_key=chat_key,
                    file_name=f"video_{message.video.file_id}.mp4",
                )
                segments.append(segment)

        # 处理音频
        if message.audio:
            audio_bytes = await self._download_file_bytes(message.audio.file_id)
            if audio_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    audio_bytes,
                    from_chat_key=chat_key,
                    file_name=message.audio.file_name
                    or f"audio_{message.audio.file_id}.mp3",
                )
                segments.append(segment)

        # 处理语音
        if message.voice:
            voice_bytes = await self._download_file_bytes(message.voice.file_id)
            if voice_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    voice_bytes,
                    from_chat_key=chat_key,
                    file_name=f"voice_{message.voice.file_id}.ogg",
                )
                segments.append(segment)

        # 处理贴纸
        if message.sticker:
            sticker_bytes = await self._download_file_bytes(message.sticker.file_id)
            if sticker_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                segment = await ChatMessageSegmentImage.create_from_bytes(
                    sticker_bytes,
                    from_chat_key=chat_key,
                    file_name=f"sticker_{message.sticker.file_id}.webp",
                )
                segments.append(segment)

        # 处理视频笔记
        if message.video_note:
            video_note_bytes = await self._download_file_bytes(
                message.video_note.file_id,
            )
            if video_note_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    video_note_bytes,
                    from_chat_key=chat_key,
                    file_name=f"video_note_{message.video_note.file_id}.mp4",
                )
                segments.append(segment)

        return segments

    async def _download_file_bytes(self, file_id: str) -> Optional[bytes]:
        """下载文件并返回字节数据"""
        try:
            if not self.adapter.application:
                return None

            file = await self.adapter.application.bot.get_file(file_id)

            # 直接下载到内存中
            file_bytes = await file.download_as_bytearray()
            return bytes(file_bytes)
        except Exception as e:
            logger.error(f"下载文件失败 {file_id}: {e}")
            return None

    def _extract_text_content(self, segments: List[ChatMessageSegment]) -> str:
        """提取文本内容"""
        text_parts = []
        for segment in segments:
            if segment.type == ChatMessageSegmentType.TEXT:
                text_parts.append(segment.text)
        return "".join(text_parts)

    def _is_mentioned(
        self,
        message: Message,
        context: ContextTypes.DEFAULT_TYPE = None,
    ) -> bool:
        """检查是否被提及"""
        # 如果是私聊，默认为 @ 机器人
        if message.chat.type == "private":
            return True

        # 在群聊中检查是否被提及
        if not message.entities:
            return False

        # 获取机器人的用户名
        bot_username = None
        if context and context.bot:
            bot_username = context.bot.username

        # 检查是否有 @机器人 的实体
        for entity in message.entities:
            if entity.type == "mention":
                # 提取 mention 的文本
                start = entity.offset
                end = entity.offset + entity.length
                mention_text = message.text[start:end] if message.text else ""

                # 检查是否提及了机器人
                if bot_username and mention_text == f"@{bot_username}":
                    return True

        return False
