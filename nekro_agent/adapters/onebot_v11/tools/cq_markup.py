"""OneBot V11 CQ 码兼容解析工具。"""

import re

from nekro_agent.tools.at_markup import normalize_malformed_at_markup

_USER_ID_PATTERN = r"(?P<uid>all|[A-Za-z0-9][A-Za-z0-9_.#\-]{2,127})"
_NICKNAME_SUFFIX = r"(?:\s*,\s*(?:name|card|nickname)\s*=\s*(?P<nickname>[^,\]】\n]+))?"
_TRAILING_PUNCT = r"(?=$|[\s,，。.!！？;；:：\)\]】>）])"
_PROTECTED_TEXT_PATTERN = re.compile(r"`[^`\n]*`|https?://[^\s<>'\"，。！？、]+|[\w.+\-]+@[\w.\-]+\.[A-Za-z]{2,}")
_PROTECTED_TOKEN_PREFIX = "\uE000ONEBOT_CQ_PROTECTED_"
_PROTECTED_TOKEN_SUFFIX = "\uE001"

_CQ_AT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        rf"[\[【]\s*CQ\s*:\s*at\s*,\s*qq\s*=\s*{_USER_ID_PATTERN}"
        rf"{_NICKNAME_SUFFIX}"
        r"(?:\s*,[^\]】]*)?[\]】]",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<!\w)CQ\s*:\s*at\s*,\s*qq\s*=\s*{_USER_ID_PATTERN}"
        rf"{_NICKNAME_SUFFIX}{_TRAILING_PUNCT}",
        re.IGNORECASE,
    ),
]


def _build_at_markup(uid: str, nickname: str | None = None) -> str:
    uid = uid.strip()
    nickname = nickname.strip().strip(";；") if nickname else ""
    if nickname:
        return f"[@id:{uid};nickname:{nickname}@]"
    return f"[@id:{uid}@]"


def _replace_cq_at_match(match: re.Match[str]) -> str:
    return _build_at_markup(match.group("uid"), match.groupdict().get("nickname"))


def _protect_non_cq_spans(text: str) -> tuple[str, list[str]]:
    protected_values: list[str] = []

    def replace_match(match: re.Match[str]) -> str:
        protected_values.append(match.group(0))
        return f"{_PROTECTED_TOKEN_PREFIX}{len(protected_values) - 1}{_PROTECTED_TOKEN_SUFFIX}"

    return _PROTECTED_TEXT_PATTERN.sub(replace_match, text), protected_values


def _restore_non_cq_spans(text: str, protected_values: list[str]) -> str:
    for index, value in enumerate(protected_values):
        text = text.replace(f"{_PROTECTED_TOKEN_PREFIX}{index}{_PROTECTED_TOKEN_SUFFIX}", value)
    return text


def normalize_onebot_cq_at_markup(text: str) -> str:
    """将 OneBot CQ-at 码归一化为内部 @ 标记。"""

    text, protected_values = _protect_non_cq_spans(text)
    for pattern in _CQ_AT_PATTERNS:
        text = pattern.sub(_replace_cq_at_match, text)
    text = _restore_non_cq_spans(text, protected_values)
    return normalize_malformed_at_markup(text)


def neutralize_onebot_cq_at_all_markup(text: str) -> str:
    """将 OneBot CQ-at 全体提醒转换为普通文本，不处理通用内部 @all 标记。"""

    text, protected_values = _protect_non_cq_spans(text)
    for pattern in _CQ_AT_PATTERNS:
        text = pattern.sub(
            lambda match: "@全体成员" if match.group("uid").strip().lower() == "all" else match.group(0),
            text,
        )
    return _restore_non_cq_spans(text, protected_values)
