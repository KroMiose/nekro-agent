import hashlib
from typing import Any, List, Optional, Type

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

from nekro_agent.adapters.wxwork.corp_app import WxWorkCorpAppClient
from nekro_agent.adapters.wxwork.crypto import WxWorkCorpAppCrypt
from nekro_agent.adapters.wxwork.parser import parse_corp_app_xml_message
from nekro_agent.adapters.wxwork.tools import SegAt, parse_at_from_text

from .config import WxWorkCorpAppConfig


logger = get_sub_logger("adapter.wxwork_corp_app")


class WxWorkCorpAppAdapter(BaseAdapter[WxWorkCorpAppConfig]):
    corp_app_client: Optional[WxWorkCorpAppClient]
    crypto: Optional[WxWorkCorpAppCrypt]

    def __init__(self, config_cls: Type[WxWorkCorpAppConfig] = WxWorkCorpAppConfig):
        super().__init__(config_cls)
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
            author="liugu",
            homepage="https://github.com/KroMiose/nekro-agent",
            tags=["wxwork", "wecom", "企业微信", "corp_app"],
        )

    @property
    def chat_key_rules(self) -> List[str]:
        return [
            "群聊: wxwork_corp_app-group_{chatid}",
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
            content, _mentioned_list = self._build_text_payload(request)
            if not content:
                return PlatformSendResponse(success=False, error_message="没有可发送的文本内容")

            response = await self.corp_app_client.send_text_message(channel_id=channel_id, content=content)
            message_id = self._normalize_message_id(response)
            return PlatformSendResponse(success=True, message_id=message_id)
        except Exception as e:
            logger.exception(f"发送企业微信自建应用消息失败 {request.chat_key}: {e}")
            return PlatformSendResponse(success=False, error_message=str(e))

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
