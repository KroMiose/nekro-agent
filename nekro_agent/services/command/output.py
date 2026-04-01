"""命令输出辅助工具

提供命令富媒体输出的标准化处理：
1. 将命令输出段中的文件复制到 uploads 目录并生成 WebUI 可访问 URL
2. 将命令输出段转换为通用消息段，以复用现有跨平台消息发送链路
"""

from pathlib import Path
from urllib.parse import quote

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


def build_command_output_messages(response: CommandResponse) -> list[AgentMessageSegment]:
    """将命令响应转换为通用消息段列表。"""
    response_segments = list(response.output_segments or [])
    messages: list[AgentMessageSegment] = []
    summary = response.message.strip()
    prefix = config.AI_COMMAND_OUTPUT_PREFIX.strip()

    if summary:
        messages.append(
            AgentMessageSegment(
                type=AgentMessageSegmentType.TEXT,
                content=f"{prefix} {summary}".strip(),
            )
        )
    elif response_segments and response_segments[0].type == CommandOutputSegmentType.TEXT and response_segments[0].text:
        if prefix:
            response_segments[0] = response_segments[0].model_copy(
                update={"text": f"{prefix} {response_segments[0].text}".strip()},
                deep=True,
            )
    elif prefix:
        messages.append(AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=prefix))

    for segment in response_segments:
        if segment.type == CommandOutputSegmentType.TEXT:
            if segment.text.strip():
                messages.append(
                    AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=segment.text.strip()),
                )
        elif segment.type == CommandOutputSegmentType.IMAGE:
            if segment.file_path:
                messages.append(
                    AgentMessageSegment(type=AgentMessageSegmentType.IMAGE, content=segment.file_path),
                )
        elif segment.type == CommandOutputSegmentType.FILE:
            if segment.file_path:
                messages.append(
                    AgentMessageSegment(type=AgentMessageSegmentType.FILE, content=segment.file_path),
                )

    return messages
