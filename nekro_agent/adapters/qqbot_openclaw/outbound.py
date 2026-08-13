from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegment,
    PlatformSendSegmentType,
)
from nekro_agent.core.logger import get_sub_logger

from .client import QQBotOpenClawClient
from .config import QQBOT_TEXT_CHUNK_LIMIT, QQBotOpenClawConfig
from .media import validate_media_file
from .ref_index_store import RefIndexEntry, RefIndexStore

logger = get_sub_logger("adapter.qqbot_openclaw.outbound")


@dataclass(slots=True)
class RecentInbound:
    message_id: str
    msg_idx: str
    timestamp: float


class QQBotOpenClawOutbound:
    def __init__(
        self,
        *,
        config: QQBotOpenClawConfig,
        client: QQBotOpenClawClient,
        ref_store: RefIndexStore,
        recent_inbound: dict[str, RecentInbound],
    ) -> None:
        self.config = config
        self.client = client
        self.ref_store = ref_store
        self.recent_inbound = recent_inbound

    async def send(self, request: PlatformSendRequest) -> PlatformSendResponse:
        target_type, target_id = self.parse_chat_key(request.chat_key)
        msg_id = self._resolve_reply_msg_id(request)
        if not msg_id and not self.config.PROACTIVE_SEND_ENABLED:
            return PlatformSendResponse(success=False, error_message="OpenClaw QQBot 主动发送已关闭，且没有可用被动回复消息")

        message_ids: list[str] = []
        try:
            for segment in self._coalesce_text_segments(request.segments):
                if segment.type in {PlatformSendSegmentType.TEXT, PlatformSendSegmentType.AT}:
                    for chunk in split_markdown_text(segment.content, QQBOT_TEXT_CHUNK_LIMIT):
                        response = await self.client.send_text(
                            target_type=target_type,
                            target_id=target_id,
                            content=chunk,
                            msg_id=msg_id,
                        )
                        self._record_response(message_ids, request.chat_key, response.response_message_id, response.ref_idx, chunk)
                elif segment.type in {PlatformSendSegmentType.IMAGE, PlatformSendSegmentType.FILE} and segment.file_path:
                    media = validate_media_file(segment.file_path, segment.type, self.config)
                    upload_response = await self.client.upload_media(target_type=target_type, target_id=target_id, media=media)
                    if not upload_response.file_info:
                        raise RuntimeError(f"OpenClaw QQBot 媒体上传成功但缺少 file_info: {upload_response.model_dump()}")
                    response = await self.client.send_media_message(
                        target_type=target_type,
                        target_id=target_id,
                        file_info=upload_response.file_info,
                        content=segment.content,
                        msg_id=msg_id,
                    )
                    self._record_response(
                        message_ids,
                        request.chat_key,
                        response.response_message_id,
                        response.ref_idx,
                        f"[{media.kind}: {media.file_name}]",
                    )
            return PlatformSendResponse(success=True, message_id=",".join(message_ids) or "empty")
        except Exception as e:
            logger.error(f"OpenClaw QQBot 发送失败: chat_key={request.chat_key}, proactive={not msg_id}, error={e}")
            return PlatformSendResponse(success=False, error_message=f"OpenClaw QQBot 发送失败: {e}")

    def parse_chat_key(self, chat_key: str) -> tuple[Literal["c2c", "group"], str]:
        if not chat_key.startswith("qqoc-"):
            raise ValueError(f"无效的 OpenClaw QQBot chat_key: {chat_key}")
        channel_id = chat_key.removeprefix("qqoc-")
        target_type, target_id = channel_id.split(":", 1)
        if target_type not in {"c2c", "group"}:
            raise ValueError(f"不支持的 OpenClaw QQBot channel_id: {channel_id}")
        return target_type, target_id

    def _resolve_reply_msg_id(self, request: PlatformSendRequest) -> str | None:
        if request.ref_msg_id:
            return request.ref_msg_id
        recent = self.recent_inbound.get(request.chat_key)
        return recent.message_id if recent else None

    def _coalesce_text_segments(self, segments: list[PlatformSendSegment]) -> list[PlatformSendSegment]:
        result: list[PlatformSendSegment] = []
        text_buffer: list[str] = []
        for segment in segments:
            if segment.type == PlatformSendSegmentType.TEXT and segment.content:
                text_buffer.append(segment.content)
                continue
            if segment.type == PlatformSendSegmentType.AT and segment.at_info:
                text_buffer.append(f"@{segment.at_info.nickname or segment.at_info.platform_user_id}")
                continue
            self._flush_text_buffer(result, text_buffer)
            result.append(segment)
        self._flush_text_buffer(result, text_buffer)
        return result

    def _flush_text_buffer(self, result: list[PlatformSendSegment], text_buffer: list[str]) -> None:
        if not text_buffer:
            return
        content = "".join(text_buffer).strip()
        text_buffer.clear()
        if content:
            result.append(PlatformSendSegment(type=PlatformSendSegmentType.TEXT, content=content))

    def _record_response(
        self,
        message_ids: list[str],
        chat_key: str,
        message_id: str,
        ref_idx: str,
        content_text: str,
    ) -> None:
        if message_id:
            message_ids.append(message_id)
        if ref_idx:
            import asyncio

            asyncio.create_task(
                self.ref_store.put(
                    RefIndexEntry(
                        ref_idx=ref_idx,
                        chat_key=chat_key,
                        message_id=message_id,
                        sender_id=self.config.APP_ID,
                        sender_name="NekroAgent",
                        content_text=content_text,
                        is_bot=True,
                    ),
                ),
            )


def split_markdown_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    code_fence_open = False
    fence_lang = ""

    for line in text.splitlines(keepends=True):
        line_len = len(line)
        if current and current_len + line_len > limit:
            chunk = "".join(current)
            if code_fence_open:
                chunk += "\n```"
            chunks.append(chunk)
            current = []
            current_len = 0
            if code_fence_open:
                opener = f"```{fence_lang}\n"
                current.append(opener)
                current_len += len(opener)

        current.append(line)
        current_len += line_len
        stripped = line.strip()
        if stripped.startswith("```"):
            if code_fence_open:
                code_fence_open = False
                fence_lang = ""
            else:
                code_fence_open = True
                fence_lang = stripped[3:].strip()

        while current_len > limit:
            raw = "".join(current)
            piece = raw[:limit]
            chunks.append(piece)
            remainder = raw[limit:]
            current = [remainder]
            current_len = len(remainder)

    if current:
        chunk = "".join(current)
        if code_fence_open:
            chunk += "\n```"
        chunks.append(chunk)
    return [chunk for chunk in chunks if chunk]
