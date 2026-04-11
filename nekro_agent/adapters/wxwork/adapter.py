import hashlib
from pathlib import Path
from typing import Any, List, Optional, Type

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

from .client import WxWorkLongConnectionClient
from .config import WxWorkConfig
from .parser import dump_frame_for_log, parse_message_frame
from .tools import SegAt, parse_at_from_text


logger = get_sub_logger("adapter.wxwork")
WXWORK_MAX_TEXT_LINES_PER_MESSAGE = 2000


class WxWorkAdapter(BaseAdapter[WxWorkConfig]):
    client: Optional[WxWorkLongConnectionClient]

    def __init__(self, config_cls: Type[WxWorkConfig] = WxWorkConfig):
        super().__init__(config_cls)
        if self.config.BOT_ID and self.config.BOT_SECRET:
            self.client = WxWorkLongConnectionClient(
                bot_id=self.config.BOT_ID,
                secret=self.config.BOT_SECRET,
                adapter=self,
            )
        else:
            logger.warning("企业微信 AI Bot 模式未完全配置，需要设置 BOT_ID 和 BOT_SECRET")
            self.client = None

    @property
    def key(self) -> str:
        return "wxwork"

    @property
    def metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="企业微信智能机器人",
            description="企业微信 AI Bot 长连接适配器，使用 Bot ID + Secret 建立 WebSocket 长连接。",
            version="1.0.0",
            author="NekroAI",
            homepage="https://github.com/KroMiose/nekro-agent",
            tags=["wxwork", "wecom", "企业微信", "智能机器人", "aibot"],
        )

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "群聊: wxwork-group_{chatid}",
            "单聊: wxwork-private_{userid}",
        ]

    @property
    def supports_webui_send(self) -> bool:
        return True

    async def init(self) -> None:
        if self.client is None:
            logger.warning("企业微信 AI Bot 长连接未配置，跳过初始化")
            return
        await self.client.start()
        logger.info("企业微信 AI Bot 长连接客户端已启动")

    async def cleanup(self) -> None:
        if self.client is not None:
            await self.client.stop()
        logger.info("企业微信 AI Bot 适配器已清理")

    async def handle_message_callback(self, frame: dict[str, Any]) -> None:
        parsed = parse_message_frame(
            frame,
            treat_all_as_tome=self.config.TREAT_ALL_RECEIVED_MESSAGES_AS_TOME,
        )
        if parsed is None:
            logger.info("收到企业微信 AI Bot 消息回调，但当前消息类型暂未接入统一收集器")
            return

        if not self.config.ENABLE_TEXT_MESSAGE_COLLECTION:
            return

        await collect_message(
            self,
            parsed.channel,
            parsed.user,
            parsed.message,
        )

    async def handle_event_callback(self, frame: dict[str, Any]) -> None:
        if not self.config.ENABLE_EVENT_LOGGING:
            return
        logger.info(f"收到企业微信 AI Bot 事件回调:\n{self._truncate_for_log(dump_frame_for_log(frame))}")

    def log_raw_frame(self, frame: dict[str, Any]) -> None:
        logger.info(f"企业微信 AI Bot 原始 WebSocket 帧:\n{self._truncate_for_log(dump_frame_for_log(frame))}")

    def _truncate_for_log(self, text: str) -> str:
        max_length = max(self.config.RAW_LOG_MAX_LENGTH, 200)
        if len(text) <= max_length:
            return text
        return f"{text[:max_length]}\n...<truncated, total={len(text)} chars>"

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        if self.client is None:
            return PlatformSendResponse(success=False, error_message="企业微信 AI Bot 客户端未初始化")

        try:
            _, channel_id = self.parse_chat_key(request.chat_key)
            chatid = self._extract_chatid(channel_id)
            response = await self._send_request_segments(chatid=chatid, request=request)
            if response is None:
                return PlatformSendResponse(success=False, error_message="没有可发送的内容")
            message_id = self._normalize_message_id(response)
            return PlatformSendResponse(success=True, message_id=str(message_id))
        except Exception as e:
            logger.exception(f"发送企业微信 AI Bot 消息失败 {request.chat_key}: {e}")
            return PlatformSendResponse(success=False, error_message=str(e))

    async def get_self_info(self) -> PlatformUser:
        return PlatformUser(
            platform_name="wxwork",
            user_id=self.config.BOT_ID,
            user_name="企业微信智能机器人",
            user_avatar="",
        )

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:  # noqa: ARG002
        return PlatformUser(
            platform_name="wxwork",
            user_id=user_id,
            user_name=user_id,
            user_avatar="",
        )

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        chat_type = ChatType.GROUP if channel_id.startswith("group_") else ChatType.PRIVATE
        channel_name = self._extract_chatid(channel_id)
        return PlatformChannel(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_type=chat_type,
        )

    def _extract_chatid(self, channel_id: str) -> str:
        if channel_id.startswith("group_"):
            return channel_id[len("group_") :]
        if channel_id.startswith("private_"):
            return channel_id[len("private_") :]
        return channel_id

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
                normalized = f"wxwork-{digest}"
                logger.warning(
                    f"企业微信 AI Bot 返回的 message_id 过长，已归一化为短 ID: original_len={len(candidate_str)}, normalized={normalized}"
                )
                return normalized

        return ""

    async def _send_request_segments(
        self,
        *,
        chatid: str,
        request: PlatformSendRequest,
    ) -> dict[str, Any] | None:
        if self.client is None:
            return None

        text_parts: list[str] = []
        mentioned_list: list[str] = []
        last_response: dict[str, Any] | None = None

        async def flush_text() -> None:
            nonlocal last_response, text_parts, mentioned_list
            content = "".join(text_parts).strip()
            if not content:
                text_parts = []
                mentioned_list = []
                return

            for chunk in self._split_text_message_chunks(content):
                last_response = await self.client.send_text_message(
                    chatid=chatid,
                    content=chunk,
                    mentioned_list=mentioned_list,
                )
            text_parts = []
            mentioned_list = []

        for seg in request.segments:
            if seg.type == PlatformSendSegmentType.TEXT:
                parsed_segments = parse_at_from_text(seg.content)
                for parsed_seg in parsed_segments:
                    if isinstance(parsed_seg, str):
                        text_parts.append(parsed_seg)
                    elif isinstance(parsed_seg, SegAt):
                        display_name = parsed_seg.nickname or parsed_seg.platform_user_id
                        text_parts.append(f"@{display_name}")
                        if parsed_seg.platform_user_id not in mentioned_list:
                            mentioned_list.append(parsed_seg.platform_user_id)
            elif seg.type == PlatformSendSegmentType.AT and seg.at_info:
                nickname = seg.at_info.nickname or seg.at_info.platform_user_id
                text_parts.append(f"@{nickname}")
                if seg.at_info.platform_user_id not in mentioned_list:
                    mentioned_list.append(seg.at_info.platform_user_id)
            elif seg.type == PlatformSendSegmentType.IMAGE:
                await flush_text()
                if not seg.file_path:
                    raise ValueError("企业微信 AI Bot 图片消息缺少 file_path")
                try:
                    last_response = await self.client.send_media_message(
                        chatid=chatid,
                        media_type="image",
                        file_path=seg.file_path,
                    )
                except Exception as exc:
                    error_text = str(exc)
                    if "暂不支持发送" not in error_text:
                        raise
                    file_name = Path(seg.file_path).name
                    logger.info(f"企业微信 AI Bot 跳过不支持的图片格式: path={seg.file_path}, error={error_text}")
                    last_response = await self.client.send_text_message(
                        chatid=chatid,
                        content=f"[图片未发送：{file_name} 格式不受支持，当前仅支持 jpg/jpeg/png]",
                    )
            elif seg.type == PlatformSendSegmentType.FILE:
                await flush_text()
                if not seg.file_path:
                    raise ValueError("企业微信 AI Bot 文件消息缺少 file_path")
                last_response = await self.client.send_media_message(
                    chatid=chatid,
                    media_type="file",
                    file_path=seg.file_path,
                )

        await flush_text()
        return last_response

    def _split_text_message_chunks(self, content: str) -> list[str]:
        if not content:
            return []

        lines = content.splitlines()
        if not lines or len(lines) <= WXWORK_MAX_TEXT_LINES_PER_MESSAGE:
            return [content]

        chunks: list[str] = []
        for start in range(0, len(lines), WXWORK_MAX_TEXT_LINES_PER_MESSAGE):
            chunk = "\n".join(lines[start : start + WXWORK_MAX_TEXT_LINES_PER_MESSAGE]).strip("\n")
            if chunk:
                chunks.append(chunk)
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
