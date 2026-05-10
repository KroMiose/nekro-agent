import time
from dataclasses import dataclass
from typing import Any


def _encode_private_user_id(user_id: str) -> str:
    encoded: list[str] = []
    for ch in user_id:
        if ch.isalnum() or ch in ".-":
            encoded.append(ch)
        elif ch == "_":
            encoded.append("__")
        elif ch == "@":
            encoded.append("_a")
        else:
            encoded.append(f"_x{ord(ch):02x}")
    return "".join(encoded)


def decode_private_user_id(encoded_user_id: str) -> str:
    decoded: list[str] = []
    i = 0
    n = len(encoded_user_id)
    while i < n:
        ch = encoded_user_id[i]
        if ch != "_":
            decoded.append(ch)
            i += 1
            continue

        if i + 1 >= n:
            decoded.append("_")
            break

        marker = encoded_user_id[i + 1]
        if marker == "_":
            decoded.append("_")
            i += 2
            continue
        if marker == "a":
            decoded.append("@")
            i += 2
            continue
        if marker == "x" and i + 3 < n:
            hex_code = encoded_user_id[i + 2 : i + 4]
            try:
                decoded.append(chr(int(hex_code, 16)))
                i += 4
                continue
            except ValueError:
                pass

        decoded.append("_")
        i += 1

    return "".join(decoded)

from nekro_agent.adapters.interface.schemas.platform import PlatformChannel, PlatformMessage, PlatformUser
from nekro_agent.schemas.chat_message import ChatMessageSegment, ChatMessageSegmentType, ChatType

from .config import WeChatOpenILinkConfig


@dataclass(slots=True)
class ParsedOpenILinkMessage:
    channel: PlatformChannel
    user: PlatformUser
    message: PlatformMessage


class OpenILinkMessageProcessor:
    def __init__(
        self,
        *,
        config: WeChatOpenILinkConfig,
        adapter_key: str,
        self_user_id: str = "",
    ):
        self.config = config
        self.adapter_key = adapter_key
        self.self_user_id = self_user_id
        self._recent_keys: dict[str, float] = {}
        self._last_gc_ts = 0.0

    def set_self_user_id(self, user_id: str) -> None:
        self.self_user_id = user_id

    def parse(self, raw_message: Any) -> ParsedOpenILinkMessage | None:
        sender_id = str(getattr(raw_message, "user_id", "") or "").strip()
        if not sender_id:
            sender_id = str(self._get_raw_field(raw_message, "user_id") or "").strip()
        if not sender_id:
            return None

        text = self._extract_text(raw_message)
        if not text:
            return None

        group_id = self._extract_group_id(raw_message)
        is_group = bool(group_id)

        channel_id = f"group_{group_id}" if is_group else f"private_{_encode_private_user_id(sender_id)}"
        channel_type = ChatType.GROUP if is_group else ChatType.PRIVATE

        message_id = self._build_message_id(raw_message)
        sender_name = sender_id
        is_self = bool(self.self_user_id and sender_id == self.self_user_id)
        is_tome = self._is_tome(raw_message=raw_message, text=text, is_group=is_group)

        parsed = ParsedOpenILinkMessage(
            channel=PlatformChannel(
                channel_id=channel_id,
                channel_name=channel_id,
                channel_type=channel_type,
            ),
            user=PlatformUser(
                platform_name=self.adapter_key,
                user_id=sender_id,
                user_name=sender_name,
            ),
            message=PlatformMessage(
                message_id=message_id,
                sender_id=sender_id,
                sender_name=sender_name,
                sender_nickname=sender_name,
                content_data=[
                    ChatMessageSegment(
                        type=ChatMessageSegmentType.TEXT,
                        text=text,
                    ),
                ],
                content_text=text,
                is_tome=is_tome,
                is_self=is_self,
                timestamp=self._extract_timestamp(raw_message),
            ),
        )

        if self._is_duplicate(parsed):
            return None
        return parsed

    def _extract_text(self, raw_message: Any) -> str:
        text = str(getattr(raw_message, "text", "") or "").strip()
        if text:
            return text

        for key in ("content", "content_text", "text"):
            value = str(self._get_raw_field(raw_message, key) or "").strip()
            if value:
                return value

        return ""

    def _extract_group_id(self, raw_message: Any) -> str:
        raw = self._get_raw(raw_message)
        for key in ("group_id", "room_id", "chatroom_id", "conversation_id"):
            value = str(getattr(raw_message, key, "") or "").strip()
            if value:
                return value
            if isinstance(raw, dict):
                rv = str(raw.get(key, "") or "").strip()
                if rv:
                    return rv
        return ""

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

        self_id = self.self_user_id.strip()
        if not self_id:
            return False

        return f"@{self_id}" in text

    def _build_message_id(self, raw_message: Any) -> str:
        for key in ("message_id", "msg_id", "id"):
            value = str(getattr(raw_message, key, "") or "").strip()
            if value:
                return value
            raw_val = str(self._get_raw_field(raw_message, key) or "").strip()
            if raw_val:
                return raw_val
        return f"wechat_openilink-{int(time.time() * 1000)}"

    def _get_raw(self, raw_message: Any) -> dict[str, Any] | None:
        raw = getattr(raw_message, "raw", None)
        if isinstance(raw, dict):
            return raw
        return None

    def _get_raw_field(self, raw_message: Any, key: str) -> Any:
        raw = self._get_raw(raw_message)
        if raw is None:
            return None
        return raw.get(key)

    def _is_duplicate(self, parsed: ParsedOpenILinkMessage) -> bool:
        now = time.time()
        ttl = max(self.config.DEDUP_WINDOW_SECONDS, 1)
        cutoff = now - ttl

        gc_interval = max(min(ttl // 4, 30), 5)
        if now - self._last_gc_ts >= gc_interval:
            stale_keys = [k for k, ts in self._recent_keys.items() if ts < cutoff]
            for key in stale_keys:
                self._recent_keys.pop(key, None)
            self._last_gc_ts = now

        dedup_key = f"{parsed.channel.channel_id}:{parsed.message.message_id}:{parsed.user.user_id}"
        if dedup_key in self._recent_keys:
            return True

        self._recent_keys[dedup_key] = now
        return False
