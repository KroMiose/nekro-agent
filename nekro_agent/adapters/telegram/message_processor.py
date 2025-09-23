"""
Telegram 消息处理器
"""

import asyncio
from typing import TYPE_CHECKING, Optional, List, Any, Dict, Tuple

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

from telegram import Update, Message, Document, PhotoSize, Video, Audio, Voice, VideoNote, Sticker
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    from nekro_agent.adapters.telegram.adapter import TelegramAdapter

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformMessage,
    PlatformUser,
    ChatType,
)
from nekro_agent.core.logger import logger
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentType,
    ChatMessageSegmentImage,
    ChatMessageSegmentFile,
)
from nekro_agent.tools.common_util import download_file_from_bytes


class MessageProcessor:
    """消息处理器"""

    def __init__(self, adapter: "TelegramAdapter"):
        self.adapter = adapter

    async def process_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理 Telegram 更新"""
        try:
            if update.message:
                await self._handle_message(update.message, context)
            elif update.edited_message:
                await self._handle_edited_message(update.edited_message, context)
            # 可以添加更多类型的处理，如 inline_query, callback_query 等
        except Exception as e:
            logger.error(f"处理 Telegram 更新时出错: {e}")

    async def _handle_message(self, message: Message, context: ContextTypes.DEFAULT_TYPE = None) -> None:
        """处理消息"""
        if not message.from_user:
            return

        # 获取用户真实昵称和显示名称
        user_display_name, user_nickname = await self._get_user_display_info(
            message.from_user, message.chat
        )

        # 构造平台用户信息
        platform_user = PlatformUser(
            platform_name=self.adapter.key,
            user_id=str(message.from_user.id),
            user_name=user_display_name,
            user_avatar="",
        )

        # 获取频道显示名称
        channel_display_name = await self._get_channel_display_name(message.chat)

        # 构造平台频道信息
        chat_type = ChatType.PRIVATE if message.chat.type == "private" else ChatType.GROUP
        platform_channel = PlatformChannel(
            platform_name=self.adapter.key,
            channel_id=f"{chat_type.value}_{message.chat.id}",
            channel_name=channel_display_name,
            channel_type=chat_type,
        )

        # 处理消息内容
        content_segments = await self._process_message_content(message)
        
        # 构造平台消息
        platform_message = PlatformMessage(
            message_id=str(message.message_id),
            sender_id=str(message.from_user.id),
            sender_name=user_display_name,
            content_text=self._extract_text_content(content_segments),
            content_data=content_segments,
            sender_nickname=user_nickname,
            is_self=message.from_user.id == context.bot.id if context and context.bot else False,
            is_tome=self._is_mentioned(message, context),
        )

        # 收集消息
        from nekro_agent.adapters.interface.collector import collect_message
        await collect_message(self.adapter, platform_channel, platform_user, platform_message)

    async def _handle_edited_message(self, message: Message, context: ContextTypes.DEFAULT_TYPE = None) -> None:
        """处理编辑消息"""
        # 目前简单处理为新消息
        await self._handle_message(message, context)

    async def _process_message_content(self, message: Message) -> List[ChatMessageSegment]:
        """处理消息内容，转换为标准消息段"""
        segments: List[ChatMessageSegment] = []

        # 处理文本内容
        if message.text:
            segment = ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=message.text)
            segments.append(segment)

        # 处理照片
        if message.photo:
            # 选择最大尺寸的照片
            largest_photo = max(message.photo, key=lambda p: p.file_size or 0)
            photo_bytes = await self._download_file_bytes(largest_photo.file_id)
            if photo_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                
                # 智能检测文件类型
                mime_type, extension = self._detect_file_type_and_extension(photo_bytes)
                filename = f"photo_{largest_photo.file_id}{extension or '.jpg'}"
                
                segment = await ChatMessageSegmentImage.create_from_bytes(
                    photo_bytes,
                    from_chat_key=chat_key,
                    file_name=filename
                )
                segments.append(segment)

        # 处理文档
        if message.document:
            doc_bytes = await self._download_file_bytes(message.document.file_id)
            if doc_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                
                # 智能检测文件类型
                mime_type, extension = self._detect_file_type_and_extension(
                    doc_bytes, message.document.file_name
                )
                
                # 构建文件名
                if message.document.file_name:
                    filename = message.document.file_name
                else:
                    filename = f"document_{message.document.file_id}{extension or '.bin'}"
                
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    doc_bytes,
                    from_chat_key=chat_key,
                    file_name=filename
                )
                segments.append(segment)

        # 处理视频
        if message.video:
            video_bytes = await self._download_file_bytes(message.video.file_id)
            if video_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                
                # 智能检测文件类型
                mime_type, extension = self._detect_file_type_and_extension(video_bytes)
                filename = f"video_{message.video.file_id}{extension or '.mp4'}"
                
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    video_bytes,
                    from_chat_key=chat_key,
                    file_name=filename
                )
                segments.append(segment)

        # 处理音频
        if message.audio:
            audio_bytes = await self._download_file_bytes(message.audio.file_id)
            if audio_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                
                # 智能检测文件类型
                mime_type, extension = self._detect_file_type_and_extension(
                    audio_bytes, message.audio.file_name
                )
                
                # 构建文件名
                if message.audio.file_name:
                    filename = message.audio.file_name
                else:
                    filename = f"audio_{message.audio.file_id}{extension or '.mp3'}"
                
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    audio_bytes,
                    from_chat_key=chat_key,
                    file_name=filename
                )
                segments.append(segment)

        # 处理语音
        if message.voice:
            voice_bytes = await self._download_file_bytes(message.voice.file_id)
            if voice_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                
                # 智能检测文件类型
                mime_type, extension = self._detect_file_type_and_extension(voice_bytes)
                filename = f"voice_{message.voice.file_id}{extension or '.ogg'}"
                
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    voice_bytes,
                    from_chat_key=chat_key,
                    file_name=filename
                )
                segments.append(segment)

        # 处理贴纸
        if message.sticker:
            sticker_bytes = await self._download_file_bytes(message.sticker.file_id)
            if sticker_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                
                # 智能检测文件类型
                mime_type, extension = self._detect_file_type_and_extension(sticker_bytes)
                filename = f"sticker_{message.sticker.file_id}{extension or '.webp'}"
                
                segment = await ChatMessageSegmentImage.create_from_bytes(
                    sticker_bytes,
                    from_chat_key=chat_key,
                    file_name=filename
                )
                segments.append(segment)

        # 处理视频笔记
        if message.video_note:
            video_note_bytes = await self._download_file_bytes(message.video_note.file_id)
            if video_note_bytes:
                # 使用适配器的 chat_key 格式
                chat_key = self.adapter.build_chat_key(message.chat.id)
                
                # 智能检测文件类型
                mime_type, extension = self._detect_file_type_and_extension(video_note_bytes)
                filename = f"video_note_{message.video_note.file_id}{extension or '.mp4'}"
                
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    video_note_bytes,
                    from_chat_key=chat_key,
                    file_name=filename
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

    def _detect_file_type_and_extension(self, file_bytes: bytes, original_filename: Optional[str] = None) -> tuple[str, str]:
        """检测文件类型和扩展名
        
        Args:
            file_bytes: 文件字节数据
            original_filename: 原始文件名
            
        Returns:
            tuple[str, str]: (MIME类型, 扩展名)
        """
        mime_type = "application/octet-stream"  # 默认类型
        extension = ""
        
        # 优先使用 magic 库检测
        if HAS_MAGIC and file_bytes:
            try:
                mime_type = magic.from_buffer(file_bytes, mime=True)
                
                # 根据 MIME 类型推断扩展名
                mime_to_ext = {
                    "image/jpeg": ".jpg",
                    "image/png": ".png",
                    "image/gif": ".gif",
                    "image/webp": ".webp",
                    "video/mp4": ".mp4",
                    "video/avi": ".avi",
                    "video/quicktime": ".mov",
                    "audio/mpeg": ".mp3",
                    "audio/wav": ".wav",
                    "audio/ogg": ".ogg",
                    "audio/mp4": ".m4a",
                    "application/pdf": ".pdf",
                    "application/zip": ".zip",
                    "text/plain": ".txt",
                }
                extension = mime_to_ext.get(mime_type, "")
            except Exception as e:
                logger.debug(f"Magic 库检测文件类型失败: {e}")
        
        # 如果 magic 库未检测出扩展名，尝试从原始文件名获取
        if not extension and original_filename:
            import os
            _, ext = os.path.splitext(original_filename.lower())
            if ext:
                extension = ext
                
        return mime_type, extension

    def _extract_text_content(self, segments: List[ChatMessageSegment]) -> str:
        """提取文本内容"""
        text_parts = []
        for segment in segments:
            if segment.type == ChatMessageSegmentType.TEXT:
                text_parts.append(segment.text)
        return "".join(text_parts)

    def _is_mentioned(self, message: Message, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
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

    async def _get_user_display_info(
        self,
        user,
        chat,
    ) -> tuple[str, str]:
        """获取用户显示信息
        
        优先使用 message.from_user 中已有的信息，避免不必要的 API 调用
        
        Returns:
            tuple[str, str]: (显示名称, 昵称)
        """
        # 构建完整的用户昵称（优先级：first_name + last_name > first_name > username > user_id）
        full_nickname = self._build_full_name(user)
        
        # 构建显示名称（用于 user_name 字段）
        display_name = (
            user.first_name  # 优先使用 first_name
            or user.username  # 然后是 username
            or str(user.id)   # 最后使用 user_id
        )
        
        # 对于私聊，直接返回基于 message.from_user 的信息
        if chat.type == "private":
            return display_name, full_nickname
        
        # 对于群聊，也直接使用 message.from_user 的信息
        # Telegram 的 message.from_user 已经包含了最新的用户信息
        # 没有必要额外调用 getChatMember API
        
        logger.debug(f"获取用户信息: display_name={display_name}, nickname={full_nickname}")
        return display_name, full_nickname
    
    async def _get_channel_display_name(self, chat) -> str:
        """获取频道/群聊的显示名称"""
        # 对于群聊，优先使用 title
        if chat.type in ["group", "supergroup", "channel"]:
            return chat.title or f"群聊 {chat.id}"
        
        # 对于私聊，使用对方的名称
        elif chat.type == "private":
            return (
                chat.first_name
                or chat.username
                or f"私聊 {chat.id}"
            )
        
        # 其他情况
        return str(chat.id)
    
    def _build_full_name(self, user) -> str:
        """构建用户的完整名称"""
        if hasattr(user, 'first_name') and hasattr(user, 'last_name'):
            if user.first_name and user.last_name:
                return f"{user.first_name} {user.last_name}"
            elif user.first_name:
                return user.first_name
            elif user.username:
                return user.username
        elif hasattr(user, 'first_name') and user.first_name:
            return user.first_name
        elif hasattr(user, 'username') and user.username:
            return user.username
        
        return str(getattr(user, 'id', 'Unknown'))
    
    def _build_full_name_from_dict(self, user_dict: dict) -> str:
        """从字典构建用户的完整名称"""
        first_name = user_dict.get("first_name", "")
        last_name = user_dict.get("last_name", "")
        username = user_dict.get("username", "")
        
        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif first_name:
            return first_name
        elif username:
            return username
        
        return user_dict.get("id", "Unknown")
    
    async def _get_channel_display_name(self, chat) -> str:
        """获取频道/群聊的显示名称"""
        # 对于群聊，优先使用 title
        if chat.type in ["group", "supergroup", "channel"]:
            return chat.title or f"群聊 {chat.id}"
        
        # 对于私聊，使用对方的名称
        elif chat.type == "private":
            return (
                chat.first_name
                or chat.username
                or f"私聊 {chat.id}"
            )
        
        # 其他情况
        return str(chat.id)