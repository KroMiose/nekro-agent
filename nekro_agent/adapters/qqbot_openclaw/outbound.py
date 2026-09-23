from __future__ import annotations

import re
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
from .config import QQBOT_MARKDOWN_ENABLED, QQBOT_TEXT_CHUNK_LIMIT, QQBotOpenClawConfig
from .media import validate_media_file
from .ref_index_store import RefIndexEntry, RefIndexStore

logger = get_sub_logger("adapter.qqbot_openclaw.outbound")

# QQBot OpenClaw 在 Markdown 模式下 (`QQBOT_MARKDOWN_ENABLED=True`) 仅识别
# `<@user_id>` 与 `<@everyone>` 两种 AT 形式；平台内部约定的
# `[@id:xxx@]` / `[@id:xxx;nickname:yyy@]`（参见 nekro_agent/tools/at_markup.py
# 中的 build_at_markup）在 markdown.content 体内会被原样当作纯文本展示。
# 本模块仅做"渲染前的转写"，不修改 Core 抽象层 (`PlatformSendSegment` /
# `PlatformAtSegment`) 的结构，也不影响 OneBot 等其它适配器。
_OPENCLAW_MD_AT_USER_RE = re.compile(
    r"\[@id:(?P<uid>all|[A-Za-z0-9][A-Za-z0-9_.#\-]{2,127})(?:;nickname:[^@\]\n]+)?@\]"
)

# AT 转写前需要保护代码块 / 行内代码 / URL / 邮箱 等非 AT 上下文，
# 避免把字面量 `[@id:xxx]` 误改成 `<@xxx>`。复刻 at_markup.py 中的
# _PROTECTED_TEXT_PATTERN 思路，但不依赖其内部实现。
_PROTECTED_SPANS_RE = re.compile(
    r"```[\s\S]*?```|`[^`\n]*`|https?://[^\s<>'\"，。！？、]+|[\w.+\-]+@[\w.\-]+\.[A-Za-z]{2,}",
)
_PLACEHOLDER_PREFIX = "\uE000OPENCLAW_PROTECTED_"
_PLACEHOLDER_SUFFIX = "\uE001"


def _render_at_segment_for_markdown(segment: PlatformSendSegment) -> str:
    """将 AT 段渲染为 OpenClaw Markdown 识别的 `<@user_id>`。"""
    at_info = segment.at_info
    if not at_info or not at_info.platform_user_id:
        return ""
    return f"<@{at_info.platform_user_id}>"


def _normalize_text_for_openclaw_markdown(text: str) -> str:
    """将文本中残留的内部 `[@id:xxx@]` 形式转换为 Markdown `<@xxx>` 形式。

    代码块 / 行内代码 / URL / 邮箱 内的字面量不会被改写。
    """
    if not text:
        return text

    stash: list[str] = []

    def _protect(match: re.Match[str]) -> str:
        stash.append(match.group(0))
        return f"{_PLACEHOLDER_PREFIX}{len(stash) - 1}{_PLACEHOLDER_SUFFIX}"

    protected = _PROTECTED_SPANS_RE.sub(_protect, text)
    converted = _OPENCLAW_MD_AT_USER_RE.sub(
        lambda m: "<@everyone>" if m.group("uid") == "all" else f"<@{m.group('uid')}>",
        protected,
    )
    if not stash:
        return converted

    def _restore(match: re.Match[str]) -> str:
        index = int(match.group(1))
        return stash[index] if 0 <= index < len(stash) else match.group(0)

    placeholder_pattern = re.compile(
        rf"{re.escape(_PLACEHOLDER_PREFIX)}(\d+){re.escape(_PLACEHOLDER_SUFFIX)}",
    )
    return placeholder_pattern.sub(_restore, converted)


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
        """合并相邻 TEXT / AT 段。

        - Markdown 模式下 (`QQBOT_MARKDOWN_ENABLED=True`): AT 段渲染为
          `<@user_id>`；TEXT 段中残留的内部 `[@id:xxx@]` 标记一并转写为
          `<@xxx>`，确保 OpenClaw Markdown 渲染器能识别。
        - 非 Markdown 模式下: 保持原行为 (AT 段 → `@昵称`)，不破坏现有
          纯文本消息体。
        """
        result: list[PlatformSendSegment] = []
        text_buffer: list[str] = []
        for segment in segments:
            if segment.type == PlatformSendSegmentType.TEXT and segment.content:
                content = segment.content
                if QQBOT_MARKDOWN_ENABLED:
                    content = _normalize_text_for_openclaw_markdown(content)
                text_buffer.append(content)
                continue
            if segment.type == PlatformSendSegmentType.AT and segment.at_info:
                if QQBOT_MARKDOWN_ENABLED:
                    text_buffer.append(_render_at_segment_for_markdown(segment))
                else:
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
