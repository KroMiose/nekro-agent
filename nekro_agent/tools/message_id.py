import re

_MSG_ID_METADATA_PATTERN = re.compile(
    r"\b(?:msg_id|message_id)\s*[:=：]\s*(?P<quote>[\"'`])?(?P<message_id>[^,\"'`\s\)\]】>]+)(?P=quote)?",
    re.IGNORECASE,
)

_NESTED_MSG_ID_PREFIX = re.compile(r"^(?:msg_id|message_id)\s*[:=：]\s*", re.IGNORECASE)


def _strip_nested_msg_id_prefix(value: str) -> str:
    """去除嵌套的 msg_id/message_id 前缀及多余括号，只保留原始 ID。

    Examples:
        'msg_id:123'            -> '123'
        'message_id="msg_id:123"' -> '123'  (外层由正则处理后传入)
        '(msg_id:123)'          -> '123'
    """
    if not value:
        return value

    while True:
        before = value
        # 去除外层括号
        if len(value) >= 2 and value[0] == "(" and value[-1] == ")":
            value = value[1:-1].strip()
        # 去除前缀
        value = _NESTED_MSG_ID_PREFIX.sub("", value, count=1).strip()
        if value == before:
            break

    return value


def normalize_ref_msg_id(ref_msg_id: str | None) -> str | None:
    """从历史元信息或模型常见误写中提取可直接传给平台的消息 ID。"""

    if ref_msg_id is None:
        return None

    normalized = str(ref_msg_id).strip()
    if not normalized:
        return None

    metadata_match = _MSG_ID_METADATA_PATTERN.search(normalized)
    if metadata_match:
        normalized = _strip_nested_msg_id_prefix(metadata_match.group("message_id"))

    return normalized or None
