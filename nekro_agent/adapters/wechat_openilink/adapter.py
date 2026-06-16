import time
from dataclasses import dataclass
from typing import Any, Literal, Optional, Type

from fastapi import APIRouter

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import ChatType

from .client import WeChatOpenILinkClient
from .config import WeChatOpenILinkConfig
from .message_processor import OpenILinkMessageProcessor, ParsedOpenILinkMessage, decode_private_user_id

logger = get_sub_logger("adapter.wechat_openilink")


@dataclass(slots=True)
class StoredInboundMessage:
    channel_id: str
    user_id: str
    message_id: str
    ts: float
    raw: object


class WeChatOpenILinkAdapter(BaseAdapter[WeChatOpenILinkConfig]):
    client: Optional[WeChatOpenILinkClient]

    def __init__(self, config_cls: Type[WeChatOpenILinkConfig] = WeChatOpenILinkConfig):
        super().__init__(config_cls)
        self.client = WeChatOpenILinkClient(self.config)
        self.message_processor = OpenILinkMessageProcessor(
            config=self.config,
            adapter_key=self.key,
        )
        self._recent_inbound_messages: dict[tuple[str, str], StoredInboundMessage] = {}

    @property
    def key(self) -> str:
        return "wechat_openilink"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="WeChat OpenILink",
            description="基于 wechatbot-sdk 的微信适配器（MVP: 文本收发）",
            version="1.1.0",
            author="NekroAI",
            homepage="https://github.com/corespeed-io/wechatbot",
            tags=["wechat", "openilink", "im"],
        )

    @property
    def chat_key_rules(self) -> list[str]:
        return [
            "群聊: `wechat_openilink-group_{group_id}`",
            "私聊: `wechat_openilink-private_{user_id}`",
        ]

    def get_adapter_router(self) -> APIRouter:
        from .routers import create_router

        return create_router(lambda: self.client.get_login_status() if self.client is not None else {
            "state": "unavailable",
            "logged_in": False,
        })

    async def init(self) -> None:
        if self.client is None:
            return

        try:
            await self.client.start(self._handle_inbound_message)
            self.message_processor.set_self_user_id(self.client.self_user_id)
            logger.info("WeChat OpenILink 适配器已启动")
        except Exception as e:
            logger.exception(f"WeChat OpenILink 启动失败: {e}")
            raise

    async def cleanup(self) -> None:
        if self.client is not None:
            await self.client.stop()
        logger.info("WeChat OpenILink 适配器已关闭")

    async def _handle_inbound_message(self, raw_message: object) -> None:
        parsed = self.message_processor.parse(raw_message)
        if parsed is None:
            return

        self._remember_inbound_message(parsed, raw_message, time.time())

        await collect_message(
            adapter=self,
            platform_channel=parsed.channel,
            platform_user=parsed.user,
            platform_message=parsed.message,
        )

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        if self.client is None:
            return PlatformSendResponse(success=False, error_message="WeChatBot client not initialized")

        try:
            _, channel_id = self.parse_chat_key(request.chat_key)
            target_id = self._extract_target_user_id(channel_id)
            ref_msg = self._resolve_ref_message(request, channel_id)

            text_parts: list[str] = []
            message_ids: list[str] = []
            failed_segments: list[str] = []
            attempted_count = 0
            success_count = 0

            for seg in request.segments:
                if seg.type == PlatformSendSegmentType.TEXT:
                    if seg.content:
                        text_parts.append(seg.content)
                    continue

                if seg.type == PlatformSendSegmentType.AT:
                    if seg.at_info:
                        text_parts.append(f"@{seg.at_info.nickname or seg.at_info.platform_user_id}")
                    continue

                if seg.type == PlatformSendSegmentType.IMAGE:
                    attempted_delta, success_delta = await self._flush_and_record_text(
                        target_id=target_id,
                        ref_msg=ref_msg,
                        text_parts=text_parts,
                        message_ids=message_ids,
                        failed_segments=failed_segments,
                    )
                    attempted_count += attempted_delta
                    success_count += success_delta

                    media_success, media_err = await self._send_media_segment(
                        media_kind="image",
                        file_path=seg.file_path,
                        target_id=target_id,
                        ref_msg=ref_msg,
                        message_ids=message_ids,
                    )
                    attempted_delta, success_delta = self._record_segment_result(
                        success=media_success,
                        error_message=media_err,
                        segment_label="image",
                        failed_segments=failed_segments,
                    )
                    attempted_count += attempted_delta
                    success_count += success_delta
                    continue

                if seg.type == PlatformSendSegmentType.FILE:
                    attempted_delta, success_delta = await self._flush_and_record_text(
                        target_id=target_id,
                        ref_msg=ref_msg,
                        text_parts=text_parts,
                        message_ids=message_ids,
                        failed_segments=failed_segments,
                    )
                    attempted_count += attempted_delta
                    success_count += success_delta

                    media_success, media_err = await self._send_media_segment(
                        media_kind="file",
                        file_path=seg.file_path,
                        target_id=target_id,
                        ref_msg=ref_msg,
                        message_ids=message_ids,
                    )
                    attempted_delta, success_delta = self._record_segment_result(
                        success=media_success,
                        error_message=media_err,
                        segment_label="file",
                        failed_segments=failed_segments,
                    )
                    attempted_count += attempted_delta
                    success_count += success_delta
                    continue

                failed_segments.append(f"{seg.type.value}:暂不支持")

            attempted_delta, success_delta = await self._flush_and_record_text(
                target_id=target_id,
                ref_msg=ref_msg,
                text_parts=text_parts,
                message_ids=message_ids,
                failed_segments=failed_segments,
            )
            attempted_count += attempted_delta
            success_count += success_delta

            if attempted_count == 0:
                return PlatformSendResponse(success=True, message_id="")

            if success_count == 0:
                return PlatformSendResponse(success=False, error_message=self._format_failed_segments(failed_segments))

            error_message = None
            if failed_segments:
                error_message = f"部分消息发送失败: {self._format_failed_segments(failed_segments)}"

            message_id = ",".join(message_ids) if message_ids else ""
            return PlatformSendResponse(success=True, message_id=message_id, error_message=error_message)
        except Exception as e:
            logger.exception(f"WeChat OpenILink 发送消息失败: {e}")
            return PlatformSendResponse(success=False, error_message=str(e))

    async def get_self_info(self) -> PlatformUser:
        if self.client is None:
            return PlatformUser(platform_name=self.key, user_id="", user_name="")

        user_id = self.client.self_user_id or "wechatbot"
        user_name = self.client.self_user_name or user_id
        return PlatformUser(
            platform_name=self.key,
            user_id=user_id,
            user_name=user_name,
            user_avatar="",
        )

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:  # noqa: ARG002
        return PlatformUser(
            platform_name=self.key,
            user_id=user_id,
            user_name=user_id,
            user_avatar="",
        )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        channel_type = ChatType.GROUP if channel_id.startswith("group_") else ChatType.PRIVATE
        channel_name = channel_id.split("_", 1)[1] if "_" in channel_id else channel_id
        return PlatformChannel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_type=channel_type,
            channel_avatar="",
        )

    def _extract_target_user_id(self, channel_id: str) -> str:
        if channel_id.startswith("private_"):
            encoded = channel_id.removeprefix("private_")
            return decode_private_user_id(encoded)

        return channel_id.split("_", 1)[1] if "_" in channel_id else channel_id

    def _remember_inbound_message(self, parsed: ParsedOpenILinkMessage, raw_message: object, now: float) -> None:
        msg_key = (parsed.channel.channel_id, parsed.message.message_id)
        self._recent_inbound_messages[msg_key] = StoredInboundMessage(
            channel_id=parsed.channel.channel_id,
            user_id=parsed.user.user_id,
            message_id=parsed.message.message_id,
            ts=now,
            raw=raw_message,
        )
        self._cleanup_recent_inbound_messages(now)

    def _resolve_ref_message(self, request: PlatformSendRequest, channel_id: str) -> object | None:
        if not request.ref_msg_id:
            return None

        self._cleanup_recent_inbound_messages(time.time())
        item = self._recent_inbound_messages.get((channel_id, request.ref_msg_id))
        return item.raw if item is not None else None

    def _cleanup_recent_inbound_messages(self, now: float) -> None:
        ttl = max(self.config.DEDUP_WINDOW_SECONDS, 1)
        cutoff = now - ttl

        expired_keys = [k for k, item in self._recent_inbound_messages.items() if item.ts < cutoff]
        for key in expired_keys:
            self._recent_inbound_messages.pop(key, None)

        max_size = max(self.config.DEDUP_WINDOW_SECONDS * 5, 200)
        if len(self._recent_inbound_messages) <= max_size:
            return

        overflow_count = len(self._recent_inbound_messages) - max_size
        oldest_items = sorted(self._recent_inbound_messages.items(), key=lambda item: item[1].ts)[:overflow_count]
        for key, _ in oldest_items:
            self._recent_inbound_messages.pop(key, None)

    async def _flush_and_record_text(
        self,
        *,
        target_id: str,
        ref_msg: object | None,
        text_parts: list[str],
        message_ids: list[str],
        failed_segments: list[str],
    ) -> tuple[int, int]:
        success, err = await self._flush_text_buffer(
            target_id=target_id,
            ref_msg=ref_msg,
            text_parts=text_parts,
            message_ids=message_ids,
        )
        return self._record_segment_result(
            success=success,
            error_message=err,
            segment_label="text",
            failed_segments=failed_segments,
        )

    def _record_segment_result(
        self,
        *,
        success: bool,
        error_message: str | None,
        segment_label: str,
        failed_segments: list[str],
    ) -> tuple[int, int]:
        if error_message:
            failed_segments.append(f"{segment_label}:{error_message}")
        return (1 if success or error_message else 0, 1 if success else 0)

    async def _send_media_segment(
        self,
        *,
        media_kind: Literal["image", "file"],
        file_path: str | None,
        target_id: str,
        ref_msg: object | None,
        message_ids: list[str],
    ) -> tuple[bool, str | None]:
        if self.client is None:
            return False, "WeChatBot client not initialized"
        if not file_path:
            return False, "file_path 为空"

        try:
            if media_kind == "image":
                msg_id = await self.client.send_image(
                    to_user_id=target_id,
                    file_path=file_path,
                    ref_msg=ref_msg,
                )
            elif self._is_voice_file(file_path):
                msg_id = await self.client.send_voice(
                    to_user_id=target_id,
                    file_path=file_path,
                    ref_msg=ref_msg,
                )
            else:
                msg_id = await self.client.send_file(
                    to_user_id=target_id,
                    file_path=file_path,
                    ref_msg=ref_msg,
                )
            if msg_id:
                message_ids.append(msg_id)
            return True, None
        except Exception as e:
            return False, str(e)

    async def _flush_text_buffer(
        self,
        *,
        target_id: str,
        ref_msg: object | None,
        text_parts: list[str],
        message_ids: list[str],
    ) -> tuple[bool, str | None]:
        if self.client is None:
            return False, "WeChatBot client not initialized"

        final_text = "".join(text_parts).strip()
        if not final_text:
            text_parts.clear()
            return False, None

        text_parts.clear()
        try:
            msg_id = await self.client.send_text(
                to_user_id=target_id,
                text=final_text,
                ref_msg=ref_msg,
            )
            if msg_id:
                message_ids.append(msg_id)
            return True, None
        except Exception as e:
            return False, str(e)

    def _is_voice_file(self, file_path: str) -> bool:
        normalized = file_path.lower()
        voice_exts = (".wav", ".mp3", ".amr", ".ogg", ".silk", ".m4a")
        return normalized.endswith(voice_exts)

    def _format_failed_segments(self, failed_segments: list[str]) -> str:
        if not failed_segments:
            return ""
        return "; ".join(failed_segments)
