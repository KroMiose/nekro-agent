import re

_MSG_ID_METADATA_PATTERN = re.compile(
    r"\b(?:msg_id|message_id)\s*[:=：]\s*(?P<quote>[\"'`])?(?P<message_id>[^,\"'`\s\)\]】>]+)(?P=quote)?",
    re.IGNORECASE,
)


def normalize_ref_msg_id(ref_msg_id: str | None) -> str | None:
    """从历史元信息或模型常见误写中提取可直接传给平台的消息 ID。"""

    if ref_msg_id is None:
        return None

    normalized = str(ref_msg_id).strip()
    if not normalized:
        return None

    metadata_match = _MSG_ID_METADATA_PATTERN.search(normalized)
    if metadata_match:
        normalized = metadata_match.group("message_id").strip()

    return normalized or None
