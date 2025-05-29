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
from nekro_agent.adapters.sse.schemas import (
    SseMessage,
    SseReceiveMessage,
    SseSegmentType,
    at,
    file,
    image,
    text,
)
from nekro_agent.adapters.sse.tools.common import get_file_url
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
    async def platform_to_sse_message(channel_id: str, segments: List[PlatformSendSegment]) -> SseMessage:
        """将平台消息段转换为SSE消息

        Args:
            platform: 平台标识
            channel_id: 频道ID
            segments: 平台消息段列表

        Returns:
            SseMessage: SSE消息
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
                        remote_url = await get_file_url(segment.file_path)

                        sse_segments.append(
                            image(
                                url=remote_url,
                                name=file_name,
                            ),
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
                        remote_url = await get_file_url(segment.file_path)

                        sse_segments.append(
                            file(
                                url=remote_url,
                                name=file_name,
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

        return SseMessage(
            channel_id=channel_id,
            segments=sse_segments,
            timestamp=int(time.time()),
        )

    @staticmethod
    def sse_to_platform_message(message: SseReceiveMessage) -> PlatformMessage:
        """将SSE接收消息转换为平台消息

        Args:
            message: SSE接收消息

        Returns:
            PlatformMessage: 平台消息
        """
        # 消息段列表
        content_data: List[ChatMessageSegment] = []
        # 文本内容
        content_text = ""

        # 遍历消息段
        for segment in message.segments:
            if segment.type == SseSegmentType.TEXT:
                # 文本消息段
                segment_text = segment.content  # type: ignore
                content_text += segment_text
                content_data.append(
                    ChatMessageSegment(
                        type=ChatMessageSegmentType.TEXT,
                        text=segment_text,
                    ),
                )

            elif segment.type == SseSegmentType.IMAGE:
                # 图片消息段
                url = segment.url  # type: ignore
                name = segment.name or f"image_{int(time.time())}.jpg"  # type: ignore

                content_data.append(
                    ChatMessageSegmentImage(
                        type=ChatMessageSegmentType.IMAGE,
                        text="[图片]",
                        file_name=name,
                        remote_url=url,
                    ),
                )

            elif segment.type == SseSegmentType.FILE:
                # 文件消息段
                url = segment.url  # type: ignore
                name = segment.name or f"file_{int(time.time())}"  # type: ignore

                content_data.append(
                    ChatMessageSegmentFile(
                        type=ChatMessageSegmentType.FILE,
                        text=f"[文件: {name}]",
                        file_name=name,
                        remote_url=url,
                    ),
                )

            elif segment.type == SseSegmentType.AT:
                # @消息段
                user_id = segment.user_id  # type: ignore
                nickname = segment.nickname or user_id  # type: ignore

                content_data.append(
                    ChatMessageSegmentAt(
                        type=ChatMessageSegmentType.AT,
                        text=f"@{nickname}",
                        target_platform_userid=user_id,
                        target_nickname=nickname,
                    ),
                )

        # 如果没有文本内容但有原始文本，使用原始文本
        if not content_text and message.raw_content:
            content_text = message.raw_content

            # 如果没有TEXT类型的消息段但有原始文本，添加一个
            if not any(seg.type == ChatMessageSegmentType.TEXT for seg in content_data):
                content_data.append(
                    ChatMessageSegment(
                        type=ChatMessageSegmentType.TEXT,
                        text=content_text,
                    ),
                )

        # 创建平台消息
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
