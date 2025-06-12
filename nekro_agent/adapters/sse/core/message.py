"""
SSE 消息转换器
===========

负责在平台消息格式和SSE消息格式之间进行转换。

主要功能:
1. 平台消息段 -> SSE消息段的转换
2. SSE消息段 -> 平台消息段的转换
3. 消息内容解析与构建
"""

import time
from pathlib import Path
from typing import List

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformMessage,
    PlatformSendSegment,
    PlatformSendSegmentType,
)
from nekro_agent.adapters.sse.sdk.models import (
    AtSegment,
    FileSegment,
    ImageSegment,
    MessageSegmentType,
    ReceiveMessage,
    SendMessage,
    TextSegment,
    at,
    file,
    image,
    text,
)
from nekro_agent.adapters.sse.tools.common import get_file_base64, get_file_info
from nekro_agent.adapters.utils import adapter_utils
from nekro_agent.core import logger
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentAt,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
)


class SseMessageConverter:
    """SSE 消息转换器

    用于在不同消息格式之间进行转换
    """

    @staticmethod
    async def platform_to_sse_message(channel_id: str, segments: List[PlatformSendSegment]) -> SendMessage:
        """将平台消息段转换为SSE消息

        Args:
            channel_id: 频道ID
            segments: 平台消息段列表

        Returns:
            SendMessage: SSE消息
        """
        sse_segments = []

        for segment in segments:
            if segment.type == PlatformSendSegmentType.TEXT:
                # 文本消息
                sse_segments.append(text(segment.content))

            elif segment.type == PlatformSendSegmentType.IMAGE:
                # 图片消息
                if segment.file_path:
                    try:
                        # 图片文件路径处理
                        file_name = Path(segment.file_path).name
                        file_suffix = Path(segment.file_path).suffix
                        # 获取base64编码和MIME类型
                        base64_url, mime_type, _ = await get_file_base64(segment.file_path)

                        sse_segments.append(
                            image(base64_url=base64_url, name=file_name, mime_type=mime_type, suffix=file_suffix),
                        )
                    except Exception as e:
                        logger.error(f"图片处理失败: {e}")
                        sse_segments.append(text(f"[图片上传失败: {Path(segment.file_path).name}]"))

            elif segment.type == PlatformSendSegmentType.FILE:
                # 文件消息
                if segment.file_path:
                    try:
                        # 文件路径处理
                        file_name = Path(segment.file_path).name
                        file_suffix = Path(segment.file_path).suffix
                        # 获取base64编码和MIME类型
                        base64_url, mime_type, _ = await get_file_base64(segment.file_path)

                        # 获取文件大小
                        file_bytes, _, _ = await get_file_info(segment.file_path)
                        file_size = len(file_bytes)

                        sse_segments.append(
                            file(
                                base64_url=base64_url,
                                name=file_name,
                                size=file_size,
                                mime_type=mime_type,
                                suffix=file_suffix,
                            ),
                        )
                    except Exception as e:
                        logger.error(f"文件处理失败: {e}")
                        sse_segments.append(text(f"[文件上传失败: {Path(segment.file_path).name}]"))

            elif segment.type == PlatformSendSegmentType.AT and segment.at_info:
                # @消息
                sse_segments.append(
                    at(
                        user_id=segment.at_info.platform_user_id,
                        nickname=segment.at_info.nickname,
                    ),
                )

        return SendMessage(
            channel_id=channel_id,
            segments=sse_segments,
            timestamp=int(time.time()),
        )

    @staticmethod
    async def sse_to_platform_message(message: ReceiveMessage) -> PlatformMessage:
        """将SSE接收消息转换为平台消息

        Args:
            message: SSE接收消息

        Returns:
            PlatformMessage: 平台消息
        """
        adapter = adapter_utils.get_adapter("sse")
        # 消息段列表
        content_data: List[ChatMessageSegment] = []
        # 文本内容
        content_text = ""

        # 构建chat_key用于文件处理
        chat_key = adapter.build_chat_key(message.channel_id)

        # 遍历消息段
        for segment in message.segments:
            if segment.type == MessageSegmentType.TEXT:
                # 必须先判断类型，然后才能安全访问属性
                if isinstance(segment, TextSegment):
                    content_text += segment.content
                    content_data.append(
                        ChatMessageSegment(
                            type=ChatMessageSegmentType.TEXT,
                            text=segment.content,
                        ),
                    )

            elif segment.type == MessageSegmentType.IMAGE:
                # 图片消息段
                if isinstance(segment, ImageSegment):
                    if segment.base64_url:
                        # 处理文件名
                        file_name = segment.name or ""
                        # 使用现成的base64方法处理
                        image_msg = await ChatMessageSegmentImage.create_from_base64(
                            base64_str=segment.base64_url,
                            from_chat_key=chat_key,
                            file_name=file_name,
                        )
                        content_data.append(image_msg)

                    elif segment.url:
                        # 处理文件名
                        file_name = segment.name or ""
                        # 使用现成的URL方法处理
                        image_msg = await ChatMessageSegmentImage.create_from_url(
                            url=segment.url,
                            from_chat_key=chat_key,
                            file_name=file_name,
                        )
                        content_data.append(image_msg)

            elif segment.type == MessageSegmentType.FILE:
                # 文件消息段
                if isinstance(segment, FileSegment):
                    if segment.base64_url:
                        # 处理文件名
                        file_name = segment.name or ""
                        # 使用现成的base64方法处理
                        file_msg = await ChatMessageSegmentFile.create_from_base64(
                            base64_str=segment.base64_url,
                            from_chat_key=chat_key,
                            file_name=file_name,
                        )
                        content_data.append(file_msg)

                    elif segment.url:
                        # 处理文件名
                        file_name = segment.name or ""
                        # 使用现成的URL方法处理
                        file_msg = await ChatMessageSegmentFile.create_from_url(
                            url=segment.url,
                            from_chat_key=chat_key,
                            file_name=file_name,
                        )
                        content_data.append(file_msg)

            elif segment.type == MessageSegmentType.AT:
                # @消息段
                if isinstance(segment, AtSegment):
                    nickname = segment.nickname or segment.user_id
                    content_data.append(
                        ChatMessageSegmentAt(
                            type=ChatMessageSegmentType.AT,
                            text=f"@{nickname}",
                            target_platform_userid=segment.user_id,
                            target_nickname=nickname,
                        ),
                    )
                    # 添加到文本内容
                    content_text += f"@{nickname} "
            else:
                logger.warning(f"未知的消息段类型: {segment.type}")

        return PlatformMessage(
            message_id=message.msg_id,
            sender_id=message.from_id,
            sender_name=message.from_name,
            sender_nickname=message.from_nickname or message.from_name,
            content_data=content_data,
            content_text=content_text,
            is_tome=message.is_to_me,
            timestamp=message.timestamp,
            is_self=message.is_self,
        )
