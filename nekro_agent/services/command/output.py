"""命令输出辅助工具

提供命令富媒体输出的标准化处理：
1. 将命令输出段中的文件复制到 uploads 目录并生成 WebUI 可访问 URL
2. 将命令响应归一化为统一输出段
3. 将输出段映射为增强消息段或平台发送段
"""

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar
from urllib.parse import quote

from nekro_agent.adapters.interface.schemas.platform import PlatformSendSegment, PlatformSendSegmentType
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.agent_message import AgentMessageSegment, AgentMessageSegmentType
from nekro_agent.services.command.schemas import (
    CommandOutputSegment,
    CommandOutputSegmentType,
    CommandResponse,
)
from nekro_agent.tools.common_util import copy_to_upload_dir

logger = get_sub_logger("command.output")
MappedSegment = TypeVar("MappedSegment")


def _build_upload_web_url(chat_key: str, file_name: str) -> str:
    return f"/api/common/uploads/{quote(chat_key, safe='')}/{quote(file_name, safe='')}"


def _normalized_text(text: str | None) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    return stripped or None


def _build_header_text(message: str, prefix: str) -> str | None:
    summary = _normalized_text(message)
    normalized_prefix = _normalized_text(prefix)
    if summary:
        return f"{normalized_prefix or ''} {summary}".strip()
    return normalized_prefix


def _is_materialized_upload_segment(chat_key: str, segment: CommandOutputSegment) -> bool:
    if not segment.web_url:
        return False
    upload_prefix = f"/api/common/uploads/{quote(chat_key, safe='')}/"
    return segment.web_url.startswith(upload_prefix)


async def materialize_command_output_segment(
    chat_key: str,
    segment: CommandOutputSegment,
) -> CommandOutputSegment:
    """为命令输出段补全 WebUI 可访问字段。

    对 `image/file` 段会将源文件复制到 uploads 目录，并返回可直接给浏览器使用的 `web_url`。
    """
    if segment.type == CommandOutputSegmentType.TEXT:
        return segment

    if _is_materialized_upload_segment(chat_key, segment):
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
    header_text = _build_header_text(response.message, prefix)
    if not header_text:
        return segments

    first_is_text = (
        bool(segments)
        and segments[0].type == CommandOutputSegmentType.TEXT
        and _normalized_text(segments[0].text) is not None
    )

    if _normalized_text(response.message) is not None:
        return [
            CommandOutputSegment(
                type=CommandOutputSegmentType.TEXT,
                text=header_text,
            ),
            *segments,
        ]

    if first_is_text:
        segments[0] = segments[0].model_copy(
            update={"text": f"{header_text} {segments[0].text}".strip()},
            deep=True,
        )
        return segments

    return [
        CommandOutputSegment(
            type=CommandOutputSegmentType.TEXT,
            text=header_text,
        ),
        *segments,
    ]


def _map_segments(
    segments: list[CommandOutputSegment],
    *,
    make_text: Callable[[str], MappedSegment],
    make_image: Callable[[str], MappedSegment],
    make_file: Callable[[str], MappedSegment],
) -> list[MappedSegment]:
    mapped_segments: list[MappedSegment] = []

    for segment in segments:
        if segment.type == CommandOutputSegmentType.TEXT:
            text = _normalized_text(segment.text)
            if not text:
                continue
            mapped_segments.append(make_text(text))
        elif segment.type == CommandOutputSegmentType.IMAGE and segment.file_path:
            mapped_segments.append(make_image(segment.file_path))
        elif segment.type == CommandOutputSegmentType.FILE and segment.file_path:
            mapped_segments.append(make_file(segment.file_path))

    return mapped_segments


def _segments_to_agent_messages(
    segments: list[CommandOutputSegment],
) -> list[AgentMessageSegment]:
    return _map_segments(
        segments,
        make_text=lambda text: AgentMessageSegment(
            type=AgentMessageSegmentType.TEXT,
            content=text,
        ),
        make_image=lambda path: AgentMessageSegment(
            type=AgentMessageSegmentType.IMAGE,
            content=path,
        ),
        make_file=lambda path: AgentMessageSegment(
            type=AgentMessageSegmentType.FILE,
            content=path,
        ),
    )


def _segments_to_platform_send_segments(
    segments: list[CommandOutputSegment],
) -> list[PlatformSendSegment]:
    return _map_segments(
        segments,
        make_text=lambda text: PlatformSendSegment(
            type=PlatformSendSegmentType.TEXT,
            content=text,
        ),
        make_image=lambda path: PlatformSendSegment(
            type=PlatformSendSegmentType.IMAGE,
            file_path=path,
        ),
        make_file=lambda path: PlatformSendSegment(
            type=PlatformSendSegmentType.FILE,
            file_path=path,
        ),
    )


async def build_command_output_messages(response: CommandResponse, chat_key: str) -> list[AgentMessageSegment]:
    """将命令响应转换为增强发送使用的通用消息段列表。"""
    from nekro_agent.services.config_resolver import config_resolver

    effective_config = await config_resolver.get_effective_config(chat_key)
    normalized_segments = _normalize_command_segments(response, effective_config.AI_COMMAND_OUTPUT_PREFIX)
    return _segments_to_agent_messages(normalized_segments)


async def build_command_output_platform_segments(response: CommandResponse, chat_key: str) -> list[PlatformSendSegment]:
    """将命令响应转换为协议端发送段列表。"""
    from nekro_agent.services.config_resolver import config_resolver

    effective_config = await config_resolver.get_effective_config(chat_key)
    normalized_segments = _normalize_command_segments(response, effective_config.AI_COMMAND_OUTPUT_PREFIX)
    return _segments_to_platform_send_segments(normalized_segments)
