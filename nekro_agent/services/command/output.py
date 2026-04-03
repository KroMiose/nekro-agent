"""命令输出辅助工具

提供命令富媒体输出的标准化处理：
1. 将命令输出段中的文件复制到 uploads 目录并生成 WebUI 可访问 URL
2. 将命令响应归一化为统一输出段
3. 将输出段映射为增强消息段或平台发送段
"""

from pathlib import Path
from urllib.parse import quote

from nekro_agent.adapters.interface.schemas.platform import PlatformSendSegment, PlatformSendSegmentType
from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.agent_message import AgentMessageSegment, AgentMessageSegmentType
from nekro_agent.services.command.schemas import (
    CommandOutputSegment,
    CommandOutputSegmentType,
    CommandResponse,
)
from nekro_agent.tools.common_util import copy_to_upload_dir

logger = get_sub_logger("command.output")


def _build_upload_web_url(chat_key: str, file_name: str) -> str:
    return f"/api/common/uploads/{quote(chat_key, safe='')}/{quote(file_name, safe='')}"


async def materialize_command_output_segment(
    chat_key: str,
    segment: CommandOutputSegment,
) -> CommandOutputSegment:
    """为命令输出段补全 WebUI 可访问字段。

    对 `image/file` 段会将源文件复制到 uploads 目录，并返回可直接给浏览器使用的 `web_url`。
    """
    if segment.type == CommandOutputSegmentType.TEXT:
        return segment

    if not segment.file_path:
        return segment

    src_path = Path(segment.file_path)
    if not src_path.exists() or not src_path.is_file():
        logger.warning(f"命令输出附件不存在，跳过物化: {src_path}")
        return segment

    target_name = segment.file_name or src_path.name
    copied_path, copied_name = await copy_to_upload_dir(
        file_path=str(src_path),
        file_name=target_name,
        from_chat_key=chat_key,
    )
    materialized_path = str(Path(copied_path).resolve())
    logger.debug(f"命令输出附件已物化到 uploads: {materialized_path}")
    return segment.model_copy(
        update={
            "file_path": materialized_path,
            "file_name": copied_name,
            "web_url": _build_upload_web_url(chat_key, copied_name),
        },
        deep=True,
    )


async def materialize_command_response(
    chat_key: str,
    response: CommandResponse,
) -> CommandResponse:
    """为命令响应中的富媒体输出补全可分发信息。"""
    if not response.output_segments:
        return response

    prepared_segments = [
        await materialize_command_output_segment(chat_key, segment)
        for segment in response.output_segments
    ]
    return response.model_copy(update={"output_segments": prepared_segments}, deep=True)


def _normalize_command_segments(
    response: CommandResponse,
    prefix: str,
) -> list[CommandOutputSegment]:
    """将命令响应归一化为可直接发送的统一输出段。"""
    segments = list(response.output_segments or [])
    summary = response.message.strip()
    normalized_prefix = prefix.strip()

    has_segments = bool(segments)
    first_is_text = (
        has_segments
        and segments[0].type == CommandOutputSegmentType.TEXT
        and bool(segments[0].text.strip())
    )

    leading_text: str | None = None
    if summary:
        leading_text = f"{normalized_prefix} {summary}".strip()
    elif first_is_text and normalized_prefix:
        segments[0] = segments[0].model_copy(
            update={"text": f"{normalized_prefix} {segments[0].text}".strip()},
            deep=True,
        )
    elif normalized_prefix:
        leading_text = normalized_prefix

    normalized_segments: list[CommandOutputSegment] = []
    if leading_text is not None:
        normalized_segments.append(
            CommandOutputSegment(
                type=CommandOutputSegmentType.TEXT,
                text=leading_text,
            )
        )

    normalized_segments.extend(segments)
    return normalized_segments


def _segments_to_agent_messages(
    segments: list[CommandOutputSegment],
) -> list[AgentMessageSegment]:
    messages: list[AgentMessageSegment] = []

    for segment in segments:
        if segment.type == CommandOutputSegmentType.TEXT:
            text = segment.text.strip()
            if not text:
                continue
            messages.append(
                AgentMessageSegment(
                    type=AgentMessageSegmentType.TEXT,
                    content=text,
                )
            )
        elif segment.type == CommandOutputSegmentType.IMAGE and segment.file_path:
            messages.append(
                AgentMessageSegment(
                    type=AgentMessageSegmentType.IMAGE,
                    content=segment.file_path,
                )
            )
        elif segment.type == CommandOutputSegmentType.FILE and segment.file_path:
            messages.append(
                AgentMessageSegment(
                    type=AgentMessageSegmentType.FILE,
                    content=segment.file_path,
                )
            )

    return messages


def _segments_to_platform_send_segments(
    segments: list[CommandOutputSegment],
) -> list[PlatformSendSegment]:
    platform_segments: list[PlatformSendSegment] = []

    for segment in segments:
        if segment.type == CommandOutputSegmentType.TEXT:
            text = segment.text.strip()
            if not text:
                continue
            platform_segments.append(
                PlatformSendSegment(
                    type=PlatformSendSegmentType.TEXT,
                    content=text,
                )
            )
        elif segment.type == CommandOutputSegmentType.IMAGE and segment.file_path:
            platform_segments.append(
                PlatformSendSegment(
                    type=PlatformSendSegmentType.IMAGE,
                    file_path=segment.file_path,
                )
            )
        elif segment.type == CommandOutputSegmentType.FILE and segment.file_path:
            platform_segments.append(
                PlatformSendSegment(
                    type=PlatformSendSegmentType.FILE,
                    file_path=segment.file_path,
                )
            )

    return platform_segments


def build_command_output_messages(response: CommandResponse) -> list[AgentMessageSegment]:
    """将命令响应转换为增强发送使用的通用消息段列表。"""
    normalized_segments = _normalize_command_segments(response, config.AI_COMMAND_OUTPUT_PREFIX)
    return _segments_to_agent_messages(normalized_segments)


def build_command_output_platform_segments(response: CommandResponse) -> list[PlatformSendSegment]:
    """将命令响应转换为协议端发送段列表。"""
    normalized_segments = _normalize_command_segments(response, config.AI_COMMAND_OUTPUT_PREFIX)
    return _segments_to_platform_send_segments(normalized_segments)
