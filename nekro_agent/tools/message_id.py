import re

_MSG_ID_KEY_PATTERN = (
    r"(?:"
    r"ref\s*[_-]?\s*msg\s*[_-]?\s*id|"
    r"reply\s*[_-]?\s*msg\s*[_-]?\s*id|"
    r"msg\s*[_-]?\s*id|"
    r"message\s*[_-]?\s*id|"
    r"引用消息\s*(?:id|编号)|"
    r"消息\s*(?:id|编号)"
    r")"
)
_MSG_ID_VALUE_PATTERN = (
    r"(?:(?P<quote>[\"'`])(?P<quoted_message_id>[^\"'`\n]+)(?P=quote)|"
    r"(?P<message_id>[^,，;；\"'`\s\)\]】）>}]+))"
)
_MSG_ID_METADATA_PATTERN = re.compile(
    rf"(?<![\w-])[\"'`]?{_MSG_ID_KEY_PATTERN}[\"'`]?\s*[:=：]\s*{_MSG_ID_VALUE_PATTERN}",
    re.IGNORECASE,
)
_CQ_REPLY_PATTERN = re.compile(
    rf"\[?\s*CQ\s*:\s*reply\s*,[^\]\n]*?\bid\s*=\s*{_MSG_ID_VALUE_PATTERN}",
    re.IGNORECASE,
)
_ID_ASSIGNMENT_PATTERN = re.compile(
    rf"^[\"'`]?(?:id|reply\s*[_-]?\s*id)[\"'`]?\s*[:=：]\s*{_MSG_ID_VALUE_PATTERN}\s*$",
    re.IGNORECASE,
)
_WRAPPED_NUMERIC_ID_PATTERN = re.compile(r"^[\(（\[【<]\s*(?P<message_id>\d+)\s*[\)）\]】>]$")
_NESTED_MSG_ID_PREFIX = re.compile(rf"^(?:{_MSG_ID_KEY_PATTERN}|id|reply\s*[_-]?\s*id)\s*[:=：]\s*", re.IGNORECASE)
_WRAPPER_PAIRS = (("(", ")"), ("（", "）"), ("[", "]"), ("【", "】"), ("<", ">"), ("{", "}"))
_QUOTE_CHARS = "\"'`"


def _extract_message_id(match: re.Match[str]) -> str:
    return match.groupdict().get("quoted_message_id") or match.group("message_id")


def _strip_outer_wrapper(value: str) -> str:
    if len(value) < 2:
        return value

    first = value[0]
    last = value[-1]
    if first in _QUOTE_CHARS and first == last:
        return value[1:-1].strip()

    for left, right in _WRAPPER_PAIRS:
        if first == left and last == right:
            return value[1:-1].strip()

    return value


def _strip_nested_msg_id_prefix(value: str) -> str:
    """去除嵌套的 msg_id/message_id 前缀及多余括号，只保留原始 ID。

    Examples:
        'msg_id:123'            -> '123'
        'message_id="msg_id:123"' -> '123'  (外层由正则处理后传入)
        '(msg_id:123)'          -> '123'
    """
    if not value:
        return value

    value = value.strip()
    while True:
        before = value
        value = _strip_outer_wrapper(value)
        value = _NESTED_MSG_ID_PREFIX.sub("", value, count=1).strip()
        if value == before:
            break

    return value


def normalize_ref_msg_id(ref_msg_id: object | None) -> str | None:
    """从历史元信息或模型常见误写中提取可直接传给平台的消息 ID。"""

    if ref_msg_id is None:
        return None

    normalized = str(ref_msg_id).strip()
    if not normalized:
        return None

    cq_reply_match = _CQ_REPLY_PATTERN.search(normalized)
    if cq_reply_match:
        normalized = _strip_nested_msg_id_prefix(_extract_message_id(cq_reply_match))
        return normalized or None

    metadata_match = _MSG_ID_METADATA_PATTERN.search(normalized)
    if metadata_match:
        normalized = _strip_nested_msg_id_prefix(_extract_message_id(metadata_match))
        return normalized or None

    id_assignment_match = _ID_ASSIGNMENT_PATTERN.match(normalized)
    if id_assignment_match:
        normalized = _strip_nested_msg_id_prefix(_extract_message_id(id_assignment_match))
        return normalized or None

    wrapped_numeric_id_match = _WRAPPED_NUMERIC_ID_PATTERN.match(normalized)
    if wrapped_numeric_id_match:
        return wrapped_numeric_id_match.group("message_id")

    return normalized or None
