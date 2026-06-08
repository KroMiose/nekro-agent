"""OneBot V11 CQ 码兼容解析工具。"""

import re
from collections.abc import Callable

from nekro_agent.tools.at_markup import (
    TRAILING_PUNCT,
    USER_ID_PATTERN,
    build_at_markup,
    normalize_malformed_at_markup,
    protect_non_at_spans,
    restore_non_at_spans,
)

_NICKNAME_SUFFIX = r"(?:\s*,\s*(?:name|card|nickname)\s*=\s*(?P<nickname>[^,\]】\n]+))?"
_CQ_AT_ALL_TOKEN = "\uE000ONEBOT_CQ_AT_ALL\uE001"

_CQ_AT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        rf"[\[【]\s*CQ\s*:\s*at\s*,\s*qq\s*=\s*{USER_ID_PATTERN}"
        rf"{_NICKNAME_SUFFIX}"
        r"(?:\s*,[^\]】]*)?[\]】]",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<!\w)CQ\s*:\s*at\s*,\s*qq\s*=\s*{USER_ID_PATTERN}"
        rf"{_NICKNAME_SUFFIX}{TRAILING_PUNCT}",
        re.IGNORECASE,
    ),
]


def _replace_cq_at_match(match: re.Match[str]) -> str:
    return build_at_markup(match.group("uid"), match.groupdict().get("nickname"))


def _replace_cq_at_match_for_neutralize(match: re.Match[str]) -> str:
    if match.group("uid").strip().lower() == "all":
        return _CQ_AT_ALL_TOKEN
    return _replace_cq_at_match(match)


def _apply_cq_at_patterns(text: str, replace_match: Callable[[re.Match[str]], str]) -> str:
    for pattern in _CQ_AT_PATTERNS:
        text = pattern.sub(replace_match, text)
    return text


def _normalize_cq_at_markup(text: str, replace_match: Callable[[re.Match[str]], str]) -> str:
    text, protected_values = protect_non_at_spans(text)
    text = _apply_cq_at_patterns(text, replace_match)
    return restore_non_at_spans(text, protected_values)


def normalize_onebot_cq_at_markup(text: str) -> str:
    """将 OneBot CQ-at 码归一化为内部 @ 标记。"""

    text = _normalize_cq_at_markup(text, _replace_cq_at_match)
    return normalize_malformed_at_markup(text)


def neutralize_onebot_cq_at_all_markup(text: str) -> str:
    """将 OneBot CQ-at 全体提醒转换为普通文本，不处理通用内部 @all 标记。"""

    text = _normalize_cq_at_markup(text, _replace_cq_at_match_for_neutralize)
    text = normalize_malformed_at_markup(text)
    return text.replace(_CQ_AT_ALL_TOKEN, "@全体成员")
