from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from nekro_agent.adapters.interface.schemas.extra import PlatformMessageExt
from nekro_agent.adapters.interface.schemas.platform import PlatformChannel, PlatformMessage, PlatformUser
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)

from .config import QQBotOpenClawConfig
from .group_policy import GroupPolicyResolver
from .ref_index_store import RefIndexEntry, RefIndexStore
from .schemas import QQBotAttachment, QQBotC2CMessageEvent, QQBotGroupMessageEvent

logger = get_sub_logger("adapter.qqbot_openclaw.processor")

MSG_TYPE_QUOTE = 103
FACE_TAG_RE = re.compile(r"<faceType=(?P<face_type>[^,>]+),faceId=(?P<face_id>[^>]+)>")


@dataclass(slots=True)
class ParsedQQBotMessage:
    channel: PlatformChannel
    user: PlatformUser
    message: PlatformMessage
    msg_idx: str
    reply_msg_id: str


class QQBotOpenClawMessageProcessor:
    def __init__(
        self,
        *,
        config: QQBotOpenClawConfig,
        adapter_key: str,
        ref_store: RefIndexStore,
        group_policy: GroupPolicyResolver,
        self_user_id: str = "",
    ) -> None:
        self.config = config
        self.adapter_key = adapter_key
        self.ref_store = ref_store
        self.group_policy = group_policy
        self.self_user_id = self_user_id

    def set_self_user_id(self, self_user_id: str) -> None:
        self.self_user_id = self_user_id
        self.group_policy.set_self_user_id(self_user_id)

    async def parse_event(self, event_type: str, raw: dict[str, Any]) -> ParsedQQBotMessage | None:
        if event_type == "C2C_MESSAGE_CREATE":
            return await self._parse_c2c(QQBotC2CMessageEvent.model_validate(raw))
        if event_type in {"GROUP_AT_MESSAGE_CREATE", "GROUP_MESSAGE_CREATE"}:
            return await self._parse_group(event_type, QQBotGroupMessageEvent.model_validate(raw))
        logger.warning(f"OpenClaw QQBot 收到未实现事件: {event_type}")
        return None

    async def _parse_c2c(self, event: QQBotC2CMessageEvent) -> ParsedQQBotMessage | None:
        user_openid = event.author.user_openid or event.author.id or event.author.union_openid
        if not user_openid:
            return None
        channel_id = f"c2c:{user_openid}"
        chat_key = self._build_chat_key(channel_id)
        msg_idx, ref_msg_idx = self._parse_ref_indices(event)
        ref_entry = await self.ref_store.get(ref_msg_idx) if ref_msg_idx else None
        content_text, segments, attachment_summaries = await self._build_content(event, chat_key, ref_entry)
        sender_name = self._pick_display_name(event.author, fallback=user_openid)

        message = PlatformMessage(
            message_id=event.id or msg_idx,
            sender_id=user_openid,
            sender_name=sender_name,
            sender_nickname=sender_name,
            content_data=segments,
            content_text=content_text,
            is_tome=True,
            is_self=bool(ref_entry and ref_entry.is_bot and msg_idx == ref_entry.ref_idx),
            timestamp=self._parse_timestamp(event.timestamp),
            ext_data=PlatformMessageExt(ref_chat_key=chat_key if ref_msg_idx else "", ref_msg_id=ref_msg_idx),
        )
        await self._save_inbound_ref(msg_idx, chat_key, message, attachment_summaries)
        return ParsedQQBotMessage(
            channel=PlatformChannel(
                channel_id=channel_id,
                channel_name=self._format_private_channel_name(sender_name, user_openid),
                channel_type=ChatType.PRIVATE,
            ),
            user=PlatformUser(platform_name=self.adapter_key, user_id=user_openid, user_name=sender_name),
            message=message,
            msg_idx=msg_idx,
            reply_msg_id=event.id,
        )

    async def _parse_group(self, event_type: str, event: QQBotGroupMessageEvent) -> ParsedQQBotMessage | None:
        group_openid = event.group_openid or event.group_id
        member_openid = event.author.member_openid or event.author.id
        if not group_openid or not member_openid:
            return None
        channel_id = f"group:{group_openid}"
        chat_key = self._build_chat_key(channel_id)
        msg_idx, ref_msg_idx = self._parse_ref_indices(event)
        ref_entry = await self.ref_store.get(ref_msg_idx) if ref_msg_idx else None
        decision = self.group_policy.decide(event_type=event_type, event=event, ref_entry=ref_entry)
        if not decision.collect:
            logger.info(f"OpenClaw QQBot 群消息跳过: group={group_openid}, reason={decision.reason}")
            return None

        content_text, segments, attachment_summaries = await self._build_content(event, chat_key, ref_entry)
        sender_name = self._pick_display_name(event.author, fallback=member_openid)
        channel_name = self._pick_group_channel_name(event, fallback=group_openid)
        message = PlatformMessage(
            message_id=event.id or msg_idx,
            sender_id=member_openid,
            sender_name=sender_name,
            sender_nickname=sender_name,
            content_data=segments,
            content_text=content_text,
            is_tome=decision.trigger,
            is_self=event.author.bot or member_openid == self.self_user_id,
            timestamp=self._parse_timestamp(event.timestamp),
            ext_data=PlatformMessageExt(ref_chat_key=chat_key if ref_msg_idx else "", ref_msg_id=ref_msg_idx),
        )
        await self._save_inbound_ref(msg_idx, chat_key, message, attachment_summaries)
        return ParsedQQBotMessage(
            channel=PlatformChannel(channel_id=channel_id, channel_name=channel_name, channel_type=ChatType.GROUP),
            user=PlatformUser(platform_name=self.adapter_key, user_id=member_openid, user_name=sender_name),
            message=message,
            msg_idx=msg_idx,
            reply_msg_id=event.id,
        )

    async def _build_content(
        self,
        event: QQBotC2CMessageEvent | QQBotGroupMessageEvent,
        chat_key: str,
        ref_entry: RefIndexEntry | None,
    ) -> tuple[str, list[ChatMessageSegment], list[str]]:
        text = self._parse_face_tags(event.content or "").strip()
        segments: list[ChatMessageSegment] = []
        if text:
            segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=text))

        attachment_summaries: list[str] = []
        for attachment in event.attachments:
            segment, summary = await self._build_attachment_segment(attachment, chat_key)
            if segment:
                segments.append(segment)
            if summary:
                attachment_summaries.append(summary)

        content_parts: list[str] = []
        if ref_entry:
            content_parts.append(self.ref_store.format_for_context(ref_entry))
        if text:
            content_parts.append(text)
        content_parts.extend(attachment_summaries)
        if not content_parts:
            content_parts.append("[非文本消息]")
        return "\n".join(content_parts), segments, attachment_summaries

    async def _build_attachment_segment(
        self,
        attachment: QQBotAttachment,
        chat_key: str,
    ) -> tuple[ChatMessageSegment | None, str]:
        url = attachment.url or attachment.voice_wav_url
        filename = attachment.filename or PurePosixPath(url).name or "qqbot-attachment"
        content_type = attachment.content_type.lower()
        if attachment.asr_refer_text:
            summary = f"[语音消息(ASR兜底，可能不准确): {attachment.asr_refer_text}]"
        else:
            size = f", {attachment.size} bytes" if attachment.size else ""
            summary = f"[附件: {filename}{size}]"

        if not url:
            return None, summary
        try:
            if content_type.startswith("image/") or filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                return await ChatMessageSegmentImage.create_from_url(url, chat_key, file_name=filename), summary
            segment_type = ChatMessageSegmentType.FILE
            if content_type.startswith("audio/") or attachment.voice_wav_url:
                segment_type = ChatMessageSegmentType.VOICE
            elif content_type.startswith("video/"):
                segment_type = ChatMessageSegmentType.VIDEO
            segment = await ChatMessageSegmentFile.create_from_url(url, chat_key, file_name=filename)
            segment.type = segment_type
            segment.text = summary
            return segment, summary
        except Exception as e:
            logger.warning(f"OpenClaw QQBot 附件下载失败，保留摘要: {filename}, {e}")
            return None, summary

    def _parse_ref_indices(self, event: QQBotC2CMessageEvent | QQBotGroupMessageEvent) -> tuple[str, str]:
        ext = event.message_scene.ext if event.message_scene else None
        ext_values = self._parse_ext_values(ext)
        msg_idx = ""
        ref_msg_idx = ""
        if ext_values:
            msg_idx = str(ext_values.get("msg_idx") or ext_values.get("msgIdx") or "")
            ref_msg_idx = str(
                ext_values.get("ref_msg_idx")
                or ext_values.get("refMsgIdx")
                or ext_values.get("ref_idx")
                or ext_values.get("refIdx")
                or "",
            )
        if event.message_type == MSG_TYPE_QUOTE and event.msg_elements:
            ref_msg_idx = str(event.msg_elements[0].msg_idx or ref_msg_idx)
        if not msg_idx and event.msg_elements:
            msg_idx = str(event.msg_elements[0].msg_idx or "")
        if not msg_idx:
            msg_idx = event.id or f"qqoc-{int(time.time() * 1000)}"
        return msg_idx, ref_msg_idx

    def _parse_ext_values(self, ext: Any) -> dict[str, Any]:
        if isinstance(ext, dict):
            return ext

        values: dict[str, str] = {}
        items: list[Any]
        if isinstance(ext, list):
            items = ext
        elif isinstance(ext, str):
            items = [ext]
        else:
            return values

        for item in items:
            if not isinstance(item, str):
                continue
            for chunk in re.split(r"[&;\n]", item):
                key, separator, value = chunk.partition("=")
                if separator and key:
                    values[key.strip()] = value.strip()
        return values

    async def _save_inbound_ref(
        self,
        msg_idx: str,
        chat_key: str,
        message: PlatformMessage,
        attachment_summaries: list[str],
    ) -> None:
        if not msg_idx:
            return
        await self.ref_store.put(
            RefIndexEntry(
                ref_idx=msg_idx,
                chat_key=chat_key,
                message_id=message.message_id,
                sender_id=message.sender_id,
                sender_name=message.sender_name,
                content_text=message.content_text,
                attachments=attachment_summaries,
                is_bot=message.is_self,
            ),
        )

    def _parse_face_tags(self, text: str) -> str:
        return FACE_TAG_RE.sub(lambda m: f"[表情:{m.group('face_type')}/{m.group('face_id')}]", text)

    def _parse_timestamp(self, value: str | int | float | None) -> int:
        if value is None:
            return int(time.time())
        if isinstance(value, (int, float)):
            if value > 100000000000:
                return int(value / 1000)
            return int(value)
        text = str(value)
        with_time = text.replace("Z", "+00:00")
        try:
            from datetime import datetime

            return int(datetime.fromisoformat(with_time).timestamp())
        except Exception:
            return int(time.time())

    def _build_chat_key(self, channel_id: str) -> str:
        return f"qqoc-{channel_id}"

    def _pick_display_name(self, source: Any, fallback: str) -> str:
        for key in ("username", "nickname", "nick", "name", "display_name", "displayName", "global_name", "globalName"):
            value = self._get_extra_value(source, key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return fallback

    def _pick_group_channel_name(self, event: QQBotGroupMessageEvent, fallback: str) -> str:
        for key in ("group_name", "group_nick", "group_title", "name", "title"):
            value = self._get_extra_value(event, key)
            if isinstance(value, str) and value.strip():
                return self._limit_channel_name(value.strip())
        return self._limit_channel_name(f"QQ群 {fallback}")

    def _format_private_channel_name(self, sender_name: str, user_openid: str) -> str:
        if sender_name and sender_name != user_openid:
            return self._limit_channel_name(sender_name)
        return self._limit_channel_name(f"QQ 私聊 {user_openid}")

    def _limit_channel_name(self, value: str) -> str:
        return value[:64]

    def _get_extra_value(self, source: Any, key: str) -> Any:
        value = getattr(source, key, None)
        if value:
            return value
        extra = getattr(source, "model_extra", None)
        if isinstance(extra, dict):
            return extra.get(key)
        if isinstance(source, dict):
            return source.get(key)
        return None
