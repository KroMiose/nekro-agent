import json
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Mapping

from nekro_agent.adapters.interface.schemas.extra import PlatformMessageExt
from nekro_agent.adapters.interface.schemas.platform import PlatformChannel, PlatformMessage, PlatformUser
from nekro_agent.schemas.chat_message import ChatMessageSegment, ChatMessageSegmentType, ChatType


@dataclass(slots=True)
class ParsedWxWorkMessage:
    channel: PlatformChannel
    user: PlatformUser
    message: PlatformMessage


def parse_message_frame(frame: Mapping[str, Any], *, treat_all_as_tome: bool = True) -> ParsedWxWorkMessage | None:
    """将企业微信长连接消息帧转换为统一消息结构。"""
    body = frame.get("body")
    if not isinstance(body, Mapping) and _get_str(frame, "msgtype"):
        body = frame
    if not isinstance(body, Mapping):
        return None

    msg_type = _get_str(body, "msgtype")
    if msg_type == "event":
        return None

    content_text = _extract_content_text(body)
    if not content_text:
        return None

    chat_type_value = _get_str(body, "chattype") or "single"
    chat_type = ChatType.GROUP if chat_type_value == "group" else ChatType.PRIVATE

    sender = body.get("from")
    sender_id = _get_str(sender, "userid") if isinstance(sender, Mapping) else ""
    if not sender_id:
        return None

    if chat_type == ChatType.GROUP:
        chat_id = _get_str(body, "chatid")
        if not chat_id:
            return None
        channel_id = f"group_{chat_id}"
    else:
        channel_id = f"private_{sender_id}"

    sender_name = _get_str(sender, "name") if isinstance(sender, Mapping) else ""
    sender_name = sender_name or sender_id

    quote = body.get("quote")
    ext_data = PlatformMessageExt(
        ref_msg_id=_get_str(quote, "msgid") if isinstance(quote, Mapping) else "",
        ref_sender_id=_get_str(_safe_mapping(quote, "from"), "userid") if isinstance(quote, Mapping) else "",
    )

    return ParsedWxWorkMessage(
        channel=PlatformChannel(
            channel_id=channel_id,
            channel_name=_get_str(body, "chatid") or channel_id,
            channel_type=chat_type,
        ),
        user=PlatformUser(
            platform_name="wxwork",
            user_id=sender_id,
            user_name=sender_name,
        ),
        message=PlatformMessage(
            message_id=_get_str(body, "msgid") or f"wxwork-{int(time.time() * 1000)}",
            sender_id=sender_id,
            sender_name=sender_name,
            sender_nickname=sender_name,
            content_data=[
                ChatMessageSegment(
                    type=ChatMessageSegmentType.TEXT,
                    text=content_text,
                )
            ],
            content_text=content_text,
            is_tome=treat_all_as_tome or chat_type == ChatType.PRIVATE,
            timestamp=_get_int(body, "create_time") or int(time.time()),
            ext_data=ext_data,
        ),
    )


def dump_frame_for_log(frame: Mapping[str, Any]) -> str:
    return json.dumps(frame, ensure_ascii=False, separators=(",", ":"), default=str)


def parse_corp_app_xml_message(xml_text: str, *, treat_all_as_tome: bool = True) -> ParsedWxWorkMessage | None:
    root = ET.fromstring(xml_text)

    msg_type = _xml_text(root, "MsgType")
    if not msg_type:
        return None

    if msg_type == "event":
        return None

    if msg_type != "text":
        return None

    sender_id = _xml_text(root, "FromUserName")
    if not sender_id:
        return None

    content_text = _xml_text(root, "Content")
    if not content_text:
        return None

    chat_id = _xml_text(root, "ChatId")
    chat_type = ChatType.GROUP if chat_id else ChatType.PRIVATE
    channel_id = f"group_{chat_id}" if chat_id else f"private_{sender_id}"

    ext_data = PlatformMessageExt(
        ref_msg_id=_xml_text(root, "MsgId"),
    )

    return ParsedWxWorkMessage(
        channel=PlatformChannel(
            channel_id=channel_id,
            channel_name=chat_id or sender_id,
            channel_type=chat_type,
        ),
        user=PlatformUser(
            platform_name="wxwork",
            user_id=sender_id,
            user_name=sender_id,
        ),
        message=PlatformMessage(
            message_id=_xml_text(root, "MsgId") or f"wxwork-corp-app-{int(time.time() * 1000)}",
            sender_id=sender_id,
            sender_name=sender_id,
            sender_nickname=sender_id,
            content_data=[
                ChatMessageSegment(
                    type=ChatMessageSegmentType.TEXT,
                    text=content_text,
                )
            ],
            content_text=content_text,
            is_tome=treat_all_as_tome or chat_type == ChatType.PRIVATE,
            timestamp=_xml_int(root, "CreateTime") or int(time.time()),
            ext_data=ext_data,
        ),
    )


def _extract_content_text(body: Mapping[str, Any]) -> str:
    msg_type = _get_str(body, "msgtype")
    if msg_type == "text":
        return _get_str(_safe_mapping(body, "text"), "content")
    if msg_type == "voice":
        voice = _safe_mapping(body, "voice")
        return _get_str(voice, "recognition") or _get_str(voice, "text")
    if msg_type == "mixed":
        mixed = _safe_mapping(body, "mixed")
        items = mixed.get("msg_item") or mixed.get("items") or mixed.get("msgItems")
        if isinstance(items, list):
            texts: list[str] = []
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                if _get_str(item, "msgtype") == "text":
                    text = _get_str(_safe_mapping(item, "text"), "content")
                    if text:
                        texts.append(text)
            return "\n".join(texts).strip()
    return ""


def _safe_mapping(data: Mapping[str, Any] | Any, key: str) -> Mapping[str, Any]:
    value = data.get(key) if isinstance(data, Mapping) else None
    return value if isinstance(value, Mapping) else {}


def _get_str(data: Mapping[str, Any] | Any, key: str) -> str:
    if not isinstance(data, Mapping):
        return ""
    value = data.get(key)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, int):
        return str(value)
    return ""


def _get_int(data: Mapping[str, Any] | Any, key: str) -> int:
    if not isinstance(data, Mapping):
        return 0
    value = data.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _xml_text(root: ET.Element, tag: str) -> str:
    element = root.find(tag)
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _xml_int(root: ET.Element, tag: str) -> int:
    value = _xml_text(root, tag)
    return int(value) if value.isdigit() else 0
