import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformMessage,
    PlatformUser,
)
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)

logger = get_sub_logger("adapter.wechat_ilink_multi")

TEXT_KEYS = ("text", "content", "content_text")
GROUP_ID_KEYS = ("group_id", "room_id", "chatroom_id")
MESSAGE_ID_KEYS = ("message_id", "msg_id", "id")
MEDIA_TYPE_KEYS = ("type", "msg_type", "message_type")
DEDUP_MAX_SIZE = 2000


@dataclass(slots=True)
class ParsedOpenILinkMessage:
    channel: PlatformChannel
    user: PlatformUser
    message: PlatformMessage


class OpenILinkMultiMessageProcessor:
    """OpenILink 多实例消息处理器

    将 OpenILink 入站消息映射为 Nekro Agent 平台 schema。
    支持多实例作用域，通过 instance_id 隔离不同微信实例的消息。
    """

    def __init__(
        self,
        *,
        instance_id: str,
        adapter_key: str,
        dedup_window_seconds: int = 120,
        self_user_id: str = "",
        build_chat_key: Callable[[str], str] | None = None,
    ):
        self.instance_id = instance_id
        self.adapter_key = adapter_key
        self.dedup_window_seconds = max(dedup_window_seconds, 1)
        self.self_user_id = self_user_id
        # 用于将作用域 channel_id 还原为完整 chat_key（媒体落盘目录需与 DBChatChannel.chat_key 一致）
        self._build_chat_key = build_chat_key
        self._recent_keys: Dict[tuple[str, str, str], float] = {}
        self._last_gc_ts = 0.0

    def _resolve_chat_key(self, channel_id: str) -> str:
        """将作用域 channel_id 还原为完整 chat_key，确保媒体落盘目录与频道 chat_key 一致。"""
        if self._build_chat_key is not None:
            return self._build_chat_key(channel_id)
        return f"{self.adapter_key}-{channel_id}"

    def set_self_user_id(self, user_id: str) -> None:
        self.self_user_id = user_id

    async def parse(self, raw_message: Any) -> Optional[ParsedOpenILinkMessage]:
        """解析入站消息

        Args:
            raw_message: OpenILink 原始消息对象或字典

        Returns:
            解析后的平台消息，如果是重复消息则返回 None
        """
        sender_id = self._extract_sender_id(raw_message)
        if not sender_id:
            logger.warning("无法提取 sender_id，跳过消息")
            return None

        group_id = self._extract_group_id(raw_message)
        channel = self._build_channel(sender_id, group_id)
        user = self._build_user(sender_id, raw_message)

        # 解析消息内容（异步，可能涉及媒体下载）
        # 媒体落盘使用完整 chat_key（而非裸 channel_id），与 DBChatChannel.chat_key 及沙盒挂载目录一致
        try:
            content_data, content_text = await self._build_content(
                raw_message=raw_message,
                sender_id=sender_id,
                chat_key=self._resolve_chat_key(channel.channel_id),
            )
        except Exception:
            logger.exception("解析消息内容失败")
            return None

        if not content_data:
            logger.debug("消息内容为空，跳过")
            return None

        message = self._build_platform_message(
            raw_message=raw_message,
            sender_id=sender_id,
            content_data=content_data,
            content_text=content_text,
            is_group=bool(group_id),
        )
        parsed = ParsedOpenILinkMessage(channel=channel, user=user, message=message)

        if self._is_duplicate(parsed):
            logger.debug(f"重复消息已过滤: {message.message_id}")
            return None
        return parsed

    def _extract_sender_id(self, raw_message: Any) -> str:
        return self._first_non_empty(raw_message, ("user_id", "sender_id", "from_user"))

    def _extract_group_id(self, raw_message: Any) -> str:
        return self._first_non_empty(raw_message, GROUP_ID_KEYS)

    def _build_channel(self, sender_id: str, group_id: str) -> PlatformChannel:
        """构建平台频道

        私聊: {instance_id}:private:{sender_id_or_peer_id}
        群聊: {instance_id}:group:{group_id}
        """
        is_group = bool(group_id)
        if is_group:
            channel_id = f"{self.instance_id}:group:{group_id}"
        else:
            channel_id = f"{self.instance_id}:private:{sender_id}"

        return PlatformChannel(
            channel_id=channel_id,
            channel_name=channel_id,
            channel_type=ChatType.GROUP if is_group else ChatType.PRIVATE,
        )

    def _build_user(self, sender_id: str, raw_message: Any) -> PlatformUser:
        """构建平台用户"""
        # 尝试获取发送者昵称
        sender_name = (
            self._first_non_empty(raw_message, ("sender_name", "nickname", "user_name"))
            or sender_id
        )

        return PlatformUser(
            platform_name=self.adapter_key,
            user_id=sender_id,
            user_name=sender_name,
        )

    async def _build_content(
        self,
        *,
        raw_message: Any,
        sender_id: str,
        chat_key: str,
    ) -> tuple[List[ChatMessageSegment], str]:
        """构建消息内容（支持文本+媒体混合）"""
        segments: List[ChatMessageSegment] = []
        texts: List[str] = []

        # 提取文本
        text = self._extract_text(raw_message)
        if text:
            segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=text))
            texts.append(text)

        # 检测并处理媒体
        msg_type = self._detect_message_type(raw_message)
        if msg_type == "image":
            media_segments, media_text = await self._build_image_content(raw_message, chat_key)
            segments.extend(media_segments)
            if media_text:
                texts.append(media_text)
        elif msg_type == "voice":
            media_segments, media_text = await self._build_voice_content(raw_message, chat_key)
            segments.extend(media_segments)
            if media_text:
                texts.append(media_text)
        elif msg_type == "file":
            media_segments, media_text = await self._build_file_content(raw_message, chat_key)
            segments.extend(media_segments)
            if media_text:
                texts.append(media_text)

        return segments, " ".join(texts) if texts else ""

    def _detect_message_type(self, raw_message: Any) -> str:
        """检测消息类型"""
        # 检查显式类型字段
        type_value = self._first_non_empty(raw_message, MEDIA_TYPE_KEYS)
        if type_value:
            type_lower = type_value.lower()
            if type_lower in ("image", "img", "picture", "photo"):
                return "image"
            if type_lower in ("voice", "audio", "sound"):
                return "voice"
            if type_lower in ("file", "document", "attachment"):
                return "file"
            if type_lower in ("text", "plain", "string"):
                return "text"

        # 通过内容字段推断
        if self._has_image_fields(raw_message):
            return "image"

        if self._has_voice_fields(raw_message):
            return "voice"

        if self._has_file_fields(raw_message):
            return "file"

        return "text"

    def _has_image_fields(self, raw_message: Any) -> bool:
        """检查是否有图片相关字段（含 wechatbot-sdk item_list）"""
        raw = self._get_raw_dict(raw_message)
        if not raw:
            return False
        image_keys = ("image_url", "img_url", "pic_url", "image_data", "image")
        for key in image_keys:
            if raw.get(key):
                return True
        for item in raw.get("item_list", []):
            if "image_item" in item:
                return True
        return False

    def _has_voice_fields(self, raw_message: Any) -> bool:
        """检查是否有语音相关字段（含 wechatbot-sdk item_list）"""
        raw = self._get_raw_dict(raw_message)
        if not raw:
            return False
        voice_keys = ("voice_url", "audio_url", "voice_data", "audio_data", "voice", "audio")
        for key in voice_keys:
            if raw.get(key):
                return True
        for item in raw.get("item_list", []):
            if "voice_item" in item:
                return True
        return False

    def _has_file_fields(self, raw_message: Any) -> bool:
        """检查是否有文件相关字段（含 wechatbot-sdk item_list）"""
        raw = self._get_raw_dict(raw_message)
        if not raw:
            return False
        file_keys = ("file_url", "file_data", "file_name", "file", "attachment_url")
        for key in file_keys:
            if raw.get(key):
                return True
        for item in raw.get("item_list", []):
            if "file_item" in item:
                return True
        return False

    async def _build_image_content(
        self,
        raw_message: Any,
        chat_key: str,
    ) -> tuple[List[ChatMessageSegment], str]:
        """构建图片内容（从 wechatbot-sdk item_list 提取 URL）"""
        raw = self._get_raw_dict(raw_message)
        if raw:
            for item in raw.get("item_list", []):
                if "image_item" in item:
                    ii = item["image_item"]
                    url = ii.get("url") or (ii.get("media") or {}).get("full_url")
                    if url:
                        file_name = ii.get("file_name") or "image.jpg"
                        try:
                            segment = await ChatMessageSegmentImage.create_from_url(
                                url=url,
                                from_chat_key=chat_key,
                                file_name=file_name,
                                use_suffix=".jpg",
                            )
                            return [segment], segment.text
                        except Exception:
                            logger.exception("下载图片失败")
                            error_text = "[图片下载失败]"
                            return [ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=error_text)], error_text
        # fallback: 从 URL 读取
        image_url = raw.get("image_url") if raw else None
        if image_url:
            try:
                segment = await ChatMessageSegmentImage.create_from_url(
                    url=image_url,
                    from_chat_key=chat_key,
                    file_name="image.jpg",
                    use_suffix=".jpg",
                )
                return [segment], segment.text
            except Exception:
                logger.exception("下载图片失败")
                error_text = "[图片下载失败]"
                return [ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=error_text)], error_text
        # fallback: 从已下载的字节数据读取（无直链时由 BotConnection 下载后注入 image_data）
        image_data = raw.get("image_data") if raw else None
        if image_data:
            try:
                segment = await ChatMessageSegmentImage.create_from_bytes(
                    image_data,
                    from_chat_key=chat_key,
                    file_name="image.jpg",
                    use_suffix=".jpg",
                )
                return [segment], segment.text
            except Exception:
                logger.exception("从字节数据构建图片失败")
                error_text = "[图片下载失败]"
                return [ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=error_text)], error_text
        return [], ""

    async def _build_voice_content(
        self,
        raw_message: Any,
        chat_key: str,
    ) -> tuple[List[ChatMessageSegment], str]:
        raw = self._get_raw_dict(raw_message)
        if raw:
            for item in raw.get("item_list", []):
                if "voice_item" in item:
                    vi = item["voice_item"]
                    url = (vi.get("media") or {}).get("full_url")
                    if url:
                        file_name = vi.get("file_name") or "voice.mp3"
                        use_suffix = ".amr" if file_name.lower().endswith(".amr") else ".mp3"
                        try:
                            segment = await ChatMessageSegmentFile.create_from_url(
                                url=url,
                                from_chat_key=chat_key,
                                file_name=file_name,
                                use_suffix=use_suffix,
                            )
                            segment.text = f"[Voice: {segment.file_name}]"
                            return [segment], segment.text
                        except Exception:
                            logger.exception("下载语音失败")
                            error_text = "[语音下载失败]"
                            return [ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=error_text)], error_text
        voice_url = raw.get("voice_url") if raw else None
        if voice_url:
            try:
                segment = await ChatMessageSegmentFile.create_from_url(
                    url=voice_url,
                    from_chat_key=chat_key,
                    file_name="voice.mp3",
                    use_suffix=".mp3",
                )
                segment.text = f"[Voice: {segment.file_name}]"
                return [segment], segment.text
            except Exception:
                logger.exception("下载语音失败")
                error_text = "[语音下载失败]"
                return [ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=error_text)], error_text
        # fallback: 从已下载的字节数据读取（无直链时由 BotConnection 下载后注入 voice_data）
        voice_data = raw.get("voice_data") if raw else None
        if voice_data:
            try:
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    voice_data,
                    from_chat_key=chat_key,
                    file_name="voice.mp3",
                    use_suffix=".mp3",
                )
                segment.text = f"[Voice: {segment.file_name}]"
                return [segment], segment.text
            except Exception:
                logger.exception("从字节数据构建语音失败")
                error_text = "[语音下载失败]"
                return [ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=error_text)], error_text
        return [], ""

    async def _build_file_content(
        self,
        raw_message: Any,
        chat_key: str,
    ) -> tuple[List[ChatMessageSegment], str]:
        raw = self._get_raw_dict(raw_message)
        if raw:
            for item in raw.get("item_list", []):
                if "file_item" in item:
                    fi = item["file_item"]
                    url = (fi.get("media") or {}).get("full_url")
                    if url:
                        file_name = fi.get("file_name") or "file"
                        try:
                            segment = await ChatMessageSegmentFile.create_from_url(
                                url=url,
                                from_chat_key=chat_key,
                                file_name=file_name,
                            )
                            return [segment], segment.text
                        except Exception:
                            logger.exception("下载文件失败")
                            error_text = "[文件下载失败]"
                            return [ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=error_text)], error_text
        file_url = raw.get("file_url") if raw else None
        if file_url:
            try:
                segment = await ChatMessageSegmentFile.create_from_url(
                    url=file_url,
                    from_chat_key=chat_key,
                    file_name="file",
                )
                return [segment], segment.text
            except Exception:
                logger.exception("下载文件失败")
                error_text = "[文件下载失败]"
                return [ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=error_text)], error_text
        # fallback: 从已下载的字节数据读取（无直链时由 BotConnection 下载后注入 file_data）
        file_data = raw.get("file_data") if raw else None
        if file_data:
            try:
                segment = await ChatMessageSegmentFile.create_from_bytes(
                    file_data,
                    from_chat_key=chat_key,
                    file_name="file",
                )
                return [segment], segment.text
            except Exception:
                logger.exception("从字节数据构建文件失败")
                error_text = "[文件下载失败]"
                return [ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=error_text)], error_text
        return [], ""

    def _extract_text(self, raw_message: Any) -> str:
        return self._first_non_empty(raw_message, TEXT_KEYS)

    def _build_platform_message(
        self,
        *,
        raw_message: Any,
        sender_id: str,
        content_data: List[ChatMessageSegment],
        content_text: str,
        is_group: bool,
    ) -> PlatformMessage:
        """构建平台消息"""
        is_self = bool(self.self_user_id and sender_id == self.self_user_id)

        return PlatformMessage(
            message_id=self._build_message_id(raw_message),
            sender_id=sender_id,
            sender_name=sender_id,
            sender_nickname=sender_id,
            content_data=content_data,
            content_text=content_text,
            is_tome=self._is_tome(raw_message=raw_message, text=content_text, is_group=is_group),
            is_self=is_self,
            timestamp=self._extract_timestamp(raw_message),
        )

    def _build_message_id(self, raw_message: Any) -> str:
        """构建消息 ID: {instance_id}:{remote_message_id}"""
        msg_id = self._first_non_empty(raw_message, MESSAGE_ID_KEYS)
        if msg_id:
            return f"{self.instance_id}:{msg_id}"
        return f"{self.instance_id}:{int(time.time() * 1000)}"

    def _extract_timestamp(self, raw_message: Any) -> int:
        ts = getattr(raw_message, "timestamp", None)
        if ts is not None:
            try:
                return int(ts.timestamp())
            except Exception:
                pass
        raw_ts = self._get_raw_field(raw_message, "timestamp")
        if raw_ts is not None:
            try:
                return int(raw_ts)
            except Exception:
                pass
        return int(time.time())

    def _is_tome(self, *, raw_message: Any, text: str, is_group: bool) -> bool:
        if not is_group:
            return True

        mention_flag = bool(self._get_raw_field(raw_message, "is_mention_bot"))
        if mention_flag:
            return True

        self_id = self.self_user_id.strip() if self.self_user_id else ""
        if not self_id:
            return False

        return f"@{self_id}" in text

    def _first_non_empty(self, raw_message: Any, keys: tuple[str, ...]) -> str:
        raw = self._get_raw_dict(raw_message)
        for key in keys:
            value = str(getattr(raw_message, key, "") or "").strip()
            if value:
                return value
            if raw is not None:
                raw_value = str(raw.get(key, "") or "").strip()
                if raw_value:
                    return raw_value
        return ""

    def _get_raw_dict(self, raw_message: Any) -> Optional[Dict[str, Any]]:
        """获取原始字典数据"""
        if isinstance(raw_message, dict):
            return raw_message
        raw = getattr(raw_message, "raw", None)
        if isinstance(raw, dict):
            return raw
        return None

    def _get_raw_field(self, raw_message: Any, key: str) -> Any:
        raw = self._get_raw_dict(raw_message)
        if raw is None:
            return None
        return raw.get(key)

    def _is_duplicate(self, parsed: ParsedOpenILinkMessage) -> bool:
        """检查消息是否重复"""
        now = time.time()
        ttl = self.dedup_window_seconds
        cutoff = now - ttl
        gc_interval = max(min(ttl // 4, 30), 5)

        self._gc_recent_keys(now, cutoff, gc_interval)

        dedup_key = (parsed.channel.channel_id, parsed.message.message_id, parsed.user.user_id)
        if dedup_key in self._recent_keys:
            return True

        self._recent_keys[dedup_key] = now
        if len(self._recent_keys) > DEDUP_MAX_SIZE:
            self._trim_recent_keys()
        return False

    def _gc_recent_keys(self, now: float, cutoff: float, gc_interval: int) -> None:
        if now - self._last_gc_ts < gc_interval:
            return
        self._recent_keys = {k: ts for k, ts in self._recent_keys.items() if ts >= cutoff}
        self._last_gc_ts = now

    def _trim_recent_keys(self) -> None:
        overflow_count = len(self._recent_keys) - DEDUP_MAX_SIZE
        if overflow_count <= 0:
            return
        oldest_keys = sorted(self._recent_keys, key=self._recent_keys.__getitem__)[:overflow_count]
        for key in oldest_keys:
            self._recent_keys.pop(key, None)
