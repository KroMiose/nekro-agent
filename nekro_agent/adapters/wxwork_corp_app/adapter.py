import asyncio
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any, List, Optional, Type

from fastapi import APIRouter

from nekro_agent.adapters.interface.base import AdapterMetadata, BaseAdapter
from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegment,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.config import config as system_config
from nekro_agent.schemas.chat_message import ChatType

from nekro_agent.adapters.wxwork.corp_app import WxWorkCorpAppClient
from nekro_agent.adapters.wxwork.crypto import WxWorkCorpAppCrypt
from nekro_agent.adapters.wxwork.parser import (
    ParsedWxWorkMessage,
    parse_corp_app_kf_event,
    parse_corp_app_kf_message,
    parse_corp_app_xml_message,
)
from nekro_agent.adapters.wxwork.tools import SegAt, parse_at_from_text
from nekro_agent.schemas.agent_message import AgentMessageSegmentType
from nekro_agent.models.db_chat_channel import DBChatChannel

from .config import WxWorkCorpAppConfig

if TYPE_CHECKING:
    from nekro_agent.schemas.agent_message import AgentMessageSegment
    from nekro_agent.services.command.schemas import CommandResponse


logger = get_sub_logger("adapter.wxwork_corp_app")
WXWORK_CORP_APP_SEND_INTERVAL_SECONDS = 0.35
WXWORK_CORP_APP_TEXT_MAX_LENGTH = 2048
WXWORK_CORP_APP_KF_COMMAND_MAX_MESSAGES = 5


class WxWorkCorpAppAdapter(BaseAdapter[WxWorkCorpAppConfig]):
    corp_app_client: Optional[WxWorkCorpAppClient]
    crypto: Optional[WxWorkCorpAppCrypt]

    def __init__(self, config_cls: Type[WxWorkCorpAppConfig] = WxWorkCorpAppConfig):
        super().__init__(config_cls)
        self._send_lock = asyncio.Lock()
        self._recent_kf_message_ids: list[str] = []
        self.corp_app_client = WxWorkCorpAppClient(self)
        if not self.corp_app_client.is_configured():
            logger.warning("企业微信自建应用模式未完全配置，需要设置 CORP_ID / CORP_APP_SECRET / CORP_APP_AGENT_ID")

        if self.config.CALLBACK_TOKEN and self.config.CALLBACK_ENCODING_AES_KEY and self.config.CORP_ID:
            self.crypto = WxWorkCorpAppCrypt(
                token=self.config.CALLBACK_TOKEN,
                encoding_aes_key=self.config.CALLBACK_ENCODING_AES_KEY,
                receive_id=self.config.CORP_ID,
            )
        else:
            logger.warning("企业微信自建应用回调未完全配置，需要设置 CALLBACK_TOKEN / CALLBACK_ENCODING_AES_KEY / CORP_ID")
            self.crypto = None

    @property
    def key(self) -> str:
        return "wxwork_corp_app"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="企业微信自建应用",
            description="企业微信自建应用适配器，通过回调接收消息并通过应用 API 发送消息。",
            version="1.0.0",
            author="NekroAI",
            homepage="https://github.com/KroMiose/nekro-agent",
            tags=["wxwork", "wecom", "企业微信", "corp_app"],
        )

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "单聊: wxwork_corp_app-private_{userid}",
        ]

    @property
    def supports_webui_send(self) -> bool:
        return True

    def get_adapter_router(self) -> APIRouter:
        from .routers import router, set_adapter

        set_adapter(self)
        return router

    async def init(self) -> None:
        logger.info("企业微信自建应用模式已初始化")
        logger.info(f"请在企业微信后台配置回调 URL: /api/adapters/{self.key}/callback")

    async def cleanup(self) -> None:
        logger.info("企业微信自建应用适配器已清理")

    async def handle_corp_app_callback(
        self,
        *,
        decrypted_xml: str,
        raw_body: str,
        msg_signature: str,
        timestamp: str,
        nonce: str,
    ) -> None:
        logger.info(
            "收到企业微信自建应用回调: "
            f"msg_signature={msg_signature}, timestamp={timestamp}, nonce={nonce}, raw_length={len(raw_body)}"
        )
        logger.info(f"企业微信自建应用解密后 XML:\n{self._truncate_for_log(decrypted_xml)}")

        parsed = parse_corp_app_xml_message(
            decrypted_xml,
            treat_all_as_tome=self.config.TREAT_ALL_RECEIVED_MESSAGES_AS_TOME,
        )
        if parsed is None:
            kf_event = parse_corp_app_kf_event(decrypted_xml)
            if kf_event is not None:
                await self._handle_kf_event(token=kf_event.token, open_kfid=kf_event.open_kfid)
                return
            logger.info("收到企业微信自建应用回调，但当前消息类型暂未接入统一收集器")
            return

        if not self.config.ENABLE_TEXT_MESSAGE_COLLECTION:
            return

        await collect_message(
            self,
            parsed.channel,
            parsed.user,
            parsed.message,
        )

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        if not self.corp_app_client or not self.corp_app_client.is_configured():
            return PlatformSendResponse(success=False, error_message="企业微信自建应用发送未配置完整")

        try:
            _, channel_id = self.parse_chat_key(request.chat_key)
            async with self._send_lock:
                response = await self._send_request_segments(
                    chat_key=request.chat_key,
                    channel_id=channel_id,
                    request=request,
                )
            if response is None:
                return PlatformSendResponse(success=False, error_message="没有可发送的内容")
            message_id = self._normalize_message_id(response)
            return PlatformSendResponse(success=True, message_id=message_id)
        except Exception as e:
            logger.exception(f"发送企业微信自建应用消息失败 {request.chat_key}: {e}")
            return PlatformSendResponse(success=False, error_message=str(e))

    async def _try_send_enhanced_command_message(self, chat_key: str, message: str) -> bool:  # noqa: ARG002
        return False

    async def _try_send_enhanced_command_response(
        self,
        chat_key: str,
        response: "CommandResponse",
        messages: list["AgentMessageSegment"],
    ) -> bool:
        return False

    async def _send_command_message(self, chat_key: str, message: str) -> None:
        if self._is_kf_chat_key(chat_key):
            estimated_count = len(self._split_text_message_chunks(message))
            if estimated_count > WXWORK_CORP_APP_KF_COMMAND_MAX_MESSAGES:
                await self._send_kf_command_limit_error(chat_key, estimated_count)
                return
        await super()._send_command_message(chat_key, message)

    async def _send_command_response(
        self,
        chat_key: str,
        response: "CommandResponse",
    ) -> None:
        if self._is_kf_chat_key(chat_key):
            from nekro_agent.services.command.output import build_command_output_platform_segments

            if response.output_segments:
                estimated_count = self._estimate_message_count(
                    build_command_output_platform_segments(response)
                )
                if estimated_count > WXWORK_CORP_APP_KF_COMMAND_MAX_MESSAGES:
                    await self._send_kf_command_limit_error(chat_key, estimated_count)
                    return
        await super()._send_command_response(chat_key, response)

    async def get_self_info(self) -> PlatformUser:
        return PlatformUser(
            platform_name="wxwork_corp_app",
            user_id=f"corp_app_{self.config.CORP_APP_AGENT_ID}".strip("_"),
            user_name=f"企业微信自建应用 {self.config.CORP_APP_AGENT_ID}".strip(),
            user_avatar="",
        )

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:  # noqa: ARG002
        return PlatformUser(
            platform_name="wxwork_corp_app",
            user_id=user_id,
            user_name=user_id,
            user_avatar="",
        )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        if channel_id.startswith("group_"):
            raise ValueError("企业微信自建应用当前暂不支持群聊频道")
        chat_type = ChatType.PRIVATE
        channel_name = self._extract_chatid(channel_id)
        return PlatformChannel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_type=chat_type,
        )

    def _extract_chatid(self, channel_id: str) -> str:
        if channel_id.startswith("private_kf_"):
            return channel_id[len("private_kf_") :]
        if channel_id.startswith("group_"):
            return channel_id[len("group_") :]
        if channel_id.startswith("private_"):
            return channel_id[len("private_") :]
        return channel_id

    async def _send_request_segments(
        self,
        *,
        chat_key: str,
        channel_id: str,
        request: PlatformSendRequest,
    ) -> dict[str, Any] | None:
        if self.corp_app_client is None:
            return None

        text_parts: list[str] = []
        last_response: dict[str, Any] | None = None
        kf_open_kfid, kf_external_userid = await self._get_kf_channel_meta(chat_key, channel_id)

        def append_text_piece(piece: str) -> None:
            if not piece:
                return
            if text_parts and not text_parts[-1].endswith("\n"):
                text_parts.append("\n")
            text_parts.append(piece)

        async def flush_text() -> None:
            nonlocal last_response, text_parts
            content = "".join(text_parts).strip()
            if not content:
                text_parts = []
                return

            for chunk in self._split_text_message_chunks(content):
                if kf_open_kfid:
                    last_response = await self.corp_app_client.send_kf_text_message(
                        open_kfid=kf_open_kfid,
                        external_userid=kf_external_userid,
                        content=chunk,
                    )
                else:
                    last_response = await self.corp_app_client.send_text_message(channel_id=channel_id, content=chunk)
                await asyncio.sleep(WXWORK_CORP_APP_SEND_INTERVAL_SECONDS)
            text_parts = []

        for seg in request.segments:
            if seg.type == PlatformSendSegmentType.TEXT:
                parsed_segments = parse_at_from_text(seg.content)
                segment_parts: list[str] = []
                for parsed_seg in parsed_segments:
                    if isinstance(parsed_seg, str):
                        segment_parts.append(parsed_seg)
                    elif isinstance(parsed_seg, SegAt):
                        display_name = parsed_seg.nickname or parsed_seg.platform_user_id
                        segment_parts.append(f"@{display_name}")
                append_text_piece("".join(segment_parts).strip())
            elif seg.type == PlatformSendSegmentType.AT and seg.at_info:
                nickname = seg.at_info.nickname or seg.at_info.platform_user_id
                append_text_piece(f"@{nickname}")
            elif seg.type == PlatformSendSegmentType.IMAGE:
                await flush_text()
                if not seg.file_path:
                    raise ValueError("企业微信自建应用图片消息缺少 file_path")
                if kf_open_kfid:
                    last_response = await self.corp_app_client.send_kf_media_message(
                        open_kfid=kf_open_kfid,
                        external_userid=kf_external_userid,
                        media_type="image",
                        file_path=seg.file_path,
                    )
                else:
                    last_response = await self.corp_app_client.send_media_message(
                        channel_id=channel_id,
                        media_type="image",
                        file_path=seg.file_path,
                    )
                await asyncio.sleep(WXWORK_CORP_APP_SEND_INTERVAL_SECONDS)
            elif seg.type == PlatformSendSegmentType.FILE:
                await flush_text()
                if not seg.file_path:
                    raise ValueError("企业微信自建应用文件消息缺少 file_path")
                if kf_open_kfid:
                    last_response = await self.corp_app_client.send_kf_media_message(
                        open_kfid=kf_open_kfid,
                        external_userid=kf_external_userid,
                        media_type="file",
                        file_path=seg.file_path,
                    )
                else:
                    last_response = await self.corp_app_client.send_media_message(
                        channel_id=channel_id,
                        media_type="file",
                        file_path=seg.file_path,
                    )
                await asyncio.sleep(WXWORK_CORP_APP_SEND_INTERVAL_SECONDS)

        await flush_text()
        return last_response

    def _is_kf_chat_key(self, chat_key: str) -> bool:
        try:
            _, channel_id = self.parse_chat_key(chat_key)
        except ValueError:
            return False
        return channel_id.startswith("private_kf_")

    def _estimate_message_count(self, segments: list[PlatformSendSegment]) -> int:
        count = 0
        text_parts: list[str] = []

        def flush_text() -> None:
            nonlocal count, text_parts
            content = "".join(text_parts).strip()
            if content:
                count += len(self._split_text_message_chunks(content))
            text_parts = []

        def append_text_piece(piece: str) -> None:
            if not piece:
                return
            if text_parts and not text_parts[-1].endswith("\n"):
                text_parts.append("\n")
            text_parts.append(piece)

        for seg in segments:
            if seg.type == PlatformSendSegmentType.TEXT:
                parsed_segments = parse_at_from_text(seg.content)
                segment_parts: list[str] = []
                for parsed_seg in parsed_segments:
                    if isinstance(parsed_seg, str):
                        segment_parts.append(parsed_seg)
                    elif isinstance(parsed_seg, SegAt):
                        display_name = parsed_seg.nickname or parsed_seg.platform_user_id
                        segment_parts.append(f"@{display_name}")
                append_text_piece("".join(segment_parts).strip())
            elif seg.type == PlatformSendSegmentType.AT and seg.at_info:
                nickname = seg.at_info.nickname or seg.at_info.platform_user_id
                append_text_piece(f"@{nickname}")
            elif seg.type in {PlatformSendSegmentType.IMAGE, PlatformSendSegmentType.FILE}:
                flush_text()
                count += 1

        flush_text()
        return count

    async def _send_kf_command_limit_error(self, chat_key: str, estimated_count: int) -> None:
        _, channel_id = self.parse_chat_key(chat_key)
        error_message = (
            f"{system_config.AI_COMMAND_OUTPUT_PREFIX} 当前命令输出预计发送 {estimated_count} 条消息，"
            f"超过企业微信客服单次最多 {WXWORK_CORP_APP_KF_COMMAND_MAX_MESSAGES} 条的限制，请缩小范围后重试"
        ).strip()
        async with self._send_lock:
            await self._send_request_segments(
                chat_key=chat_key,
                channel_id=channel_id,
                request=PlatformSendRequest(
                    chat_key=chat_key,
                    segments=[PlatformSendSegment(type=PlatformSendSegmentType.TEXT, content=error_message)],
                ),
            )

    async def _handle_kf_event(self, *, token: str, open_kfid: str) -> None:
        if not self.corp_app_client:
            return

        cursor = ""
        latest_item: dict[str, Any] | None = None
        while True:
            response = await self.corp_app_client.sync_kf_messages(token=token, open_kfid=open_kfid, cursor=cursor)
            msg_list = response.get("msg_list") or []
            for item in msg_list:
                if isinstance(item, dict):
                    latest_item = item

            has_more = bool(response.get("has_more"))
            cursor = str(response.get("next_cursor") or "").strip()
            if not has_more or not cursor:
                break

        if latest_item is None:
            return

        parsed = parse_corp_app_kf_message(
            latest_item,
            treat_all_as_tome=self.config.TREAT_ALL_RECEIVED_MESSAGES_AS_TOME,
        )
        if parsed is None:
            return
        if self._is_duplicate_kf_message(parsed.message.message_id):
            return
        await self._bind_kf_channel(parsed, open_kfid=open_kfid)
        if self.config.ENABLE_TEXT_MESSAGE_COLLECTION:
            await collect_message(
                self,
                parsed.channel,
                parsed.user,
                parsed.message,
            )

    async def _bind_kf_channel(self, parsed: ParsedWxWorkMessage, *, open_kfid: str) -> None:
        db_chat_channel = await DBChatChannel.get_or_create(
            adapter_key=self.key,
            channel_id=parsed.channel.channel_id,
            channel_type=parsed.channel.channel_type,
            channel_name=parsed.channel.channel_name,
        )
        channel_data = json.loads(db_chat_channel.data or "{}")
        channel_data["kf_open_kfid"] = open_kfid
        channel_data["kf_external_userid"] = parsed.user.user_id
        db_chat_channel.data = json.dumps(channel_data, ensure_ascii=False)
        await db_chat_channel.save()

    async def _get_kf_channel_meta(self, chat_key: str, channel_id: str) -> tuple[str, str]:
        if not channel_id.startswith("private_kf_"):
            return "", ""
        db_chat_channel = await DBChatChannel.get_channel(chat_key=chat_key)
        channel_data = json.loads(db_chat_channel.data or "{}")
        return (
            str(channel_data.get("kf_open_kfid") or "").strip(),
            str(channel_data.get("kf_external_userid") or "").strip(),
        )

    def _is_duplicate_kf_message(self, message_id: str) -> bool:
        if not message_id:
            return False
        if message_id in self._recent_kf_message_ids:
            return True
        self._recent_kf_message_ids.append(message_id)
        self._recent_kf_message_ids = self._recent_kf_message_ids[-256:]
        return False

    async def _send_text_content(self, *, channel_id: str, content: str) -> None:
        for chunk in self._split_text_message_chunks(content):
            await self.corp_app_client.send_text_message(channel_id=channel_id, content=chunk)
            await asyncio.sleep(WXWORK_CORP_APP_SEND_INTERVAL_SECONDS)

    def _split_text_message_chunks(self, content: str) -> list[str]:
        if len(content) <= WXWORK_CORP_APP_TEXT_MAX_LENGTH:
            return [content]

        chunks: list[str] = []
        start = 0
        content_len = len(content)
        while start < content_len:
            end = min(start + WXWORK_CORP_APP_TEXT_MAX_LENGTH, content_len)
            if end < content_len:
                cut_position = end
                for i in range(end, start, -1):
                    if content[i - 1] in {"。", "！", "？", ".", "!", "?", "\n", ";", "；"}:
                        cut_position = i
                        break
                end = cut_position
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = max(end, start + 1)
        return chunks or [content]

    def _build_text_payload(self, request: PlatformSendRequest) -> tuple[str, list[str]]:
        parts: list[str] = []
        mentioned_list: list[str] = []

        for seg in request.segments:
            if seg.type == PlatformSendSegmentType.TEXT:
                parsed_segments = parse_at_from_text(seg.content)
                for parsed_seg in parsed_segments:
                    if isinstance(parsed_seg, str):
                        parts.append(parsed_seg)
                    elif isinstance(parsed_seg, SegAt):
                        display_name = parsed_seg.nickname or parsed_seg.platform_user_id
                        parts.append(f"@{display_name}")
                        if parsed_seg.platform_user_id not in mentioned_list:
                            mentioned_list.append(parsed_seg.platform_user_id)
            elif seg.type == PlatformSendSegmentType.AT and seg.at_info:
                nickname = seg.at_info.nickname or seg.at_info.platform_user_id
                parts.append(f"@{nickname}")
                if seg.at_info.platform_user_id not in mentioned_list:
                    mentioned_list.append(seg.at_info.platform_user_id)
            elif seg.type == PlatformSendSegmentType.IMAGE:
                file_path = seg.file_path or ""
                if parts and not parts[-1].endswith("\n"):
                    parts.append("\n")
                parts.append(f"[图片消息暂未直传，原始文件: {file_path}]")
            elif seg.type == PlatformSendSegmentType.FILE:
                file_path = seg.file_path or ""
                if parts and not parts[-1].endswith("\n"):
                    parts.append("\n")
                parts.append(f"[文件消息暂未直传，原始文件: {file_path}]")

        content = "".join(parts).strip()
        return content, mentioned_list

    def _normalize_message_id(self, response: dict[str, Any]) -> str:
        candidates = [
            (response.get("body") or {}).get("msgid"),
            response.get("msgid"),
            (response.get("headers") or {}).get("req_id"),
        ]

        for candidate in candidates:
            candidate_str = str(candidate or "").strip()
            if candidate_str and len(candidate_str) <= 64:
                return candidate_str

        for candidate in candidates:
            candidate_str = str(candidate or "").strip()
            if candidate_str:
                digest = hashlib.sha1(candidate_str.encode("utf-8")).hexdigest()
                normalized = f"wxwork_corp_app-{digest}"
                logger.warning(
                    f"企业微信自建应用返回的 message_id 过长，已归一化为短 ID: original_len={len(candidate_str)}, normalized={normalized}"
                )
                return normalized

        return ""

    def _truncate_for_log(self, text: str) -> str:
        max_length = max(self.config.RAW_LOG_MAX_LENGTH, 200)
        if len(text) <= max_length:
            return text
        return f"{text[:max_length]}\n...<truncated, total={len(text)} chars>"
