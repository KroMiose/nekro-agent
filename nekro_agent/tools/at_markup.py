import re

_USER_ID_PATTERN = r"(?P<uid>all|[A-Za-z0-9][A-Za-z0-9_.#\-]{2,127})"
_NICKNAME_VALUE = r"[^@\]\)>】）\n]+?"
_CANONICAL_NICKNAME_VALUE = r"[^@\]\n]+?"
_NICKNAME_GROUP = rf"(?P<nickname>{_NICKNAME_VALUE})"
_CANONICAL_NICKNAME_GROUP = rf"(?P<nickname>{_CANONICAL_NICKNAME_VALUE})"
_NICKNAME_SUFFIX = rf"(?:\s*[;；]\s*nickname\s*[=:：]\s*{_NICKNAME_GROUP})?"
_CQ_NICKNAME_SUFFIX = r"(?:\s*,\s*(?:name|card|nickname)\s*=\s*(?P<nickname>[^,\]】\n]+))?"
_TRAILING_PUNCT = r"(?=$|[\s,，。.!！？;；:：\)\]】>）])"
_AT_BOUNDARY = r"(?<![\w\[])"
_BARE_AT_BOUNDARY = r"(?<![\w\[/])"
_ID_ASSIGN = rf"\s*id\s*[=:：]\s*{_USER_ID_PATTERN}"
_BRACKET_AT_CLOSE = r"\s*[;；]?\s*@?\s*[\]】]"
_MAX_NORMALIZE_PASSES = 3
_PROTECTED_TEXT_PATTERN = re.compile(r"`[^`\n]*`|https?://[^\s<>'\"，。！？、]+|[\w.+\-]+@[\w.\-]+\.[A-Za-z]{2,}")
_PROTECTED_TOKEN_PREFIX = "\uE000AT_PROTECTED_"
_PROTECTED_TOKEN_SUFFIX = "\uE001"
_AT_ALL_MARKUP_PATTERN = re.compile(r"\[@(?:id:)?all(?:;nickname:[^@\]\n]+)?@\]", re.IGNORECASE)

AT_MARKUP_PATTERN = re.compile(
    rf"\[@id:{_USER_ID_PATTERN}(?:;nickname:{_CANONICAL_NICKNAME_GROUP})?@\]",
)

_AT_MARKUP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        rf"[\[【]\s*CQ\s*:\s*at\s*,\s*qq\s*=\s*{_USER_ID_PATTERN}"
        rf"{_CQ_NICKNAME_SUFFIX}"
        r"(?:\s*,[^\]】]*)?[\]】]",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<!\w)CQ\s*:\s*at\s*,\s*qq\s*=\s*{_USER_ID_PATTERN}"
        rf"{_CQ_NICKNAME_SUFFIX}{_TRAILING_PUNCT}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"[\(（]\s*@?\s*[\[【]\s*@?{_ID_ASSIGN}{_NICKNAME_SUFFIX}{_BRACKET_AT_CLOSE}\s*[\)）]",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<!\w)@\s*[\[【]\s*@?{_ID_ASSIGN}{_NICKNAME_SUFFIX}{_BRACKET_AT_CLOSE}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:<\w{{4,12}}\s*\|\s*)?(?:<?At:\s*)?[\[【]\s*@?{_ID_ASSIGN}"
        rf"{_NICKNAME_SUFFIX}{_BRACKET_AT_CLOSE}(?:>)?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:<?At:\s*)?[\(（]\s*@{_ID_ASSIGN}{_NICKNAME_SUFFIX}\s*[;；]?\s*@?\s*[\)）](?:>)?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"{_AT_BOUNDARY}@{_ID_ASSIGN}{_NICKNAME_SUFFIX}\s*[;；]?\s*@?\s*[\]】\)）>]",
        re.IGNORECASE,
    ),
    re.compile(
        rf"{_AT_BOUNDARY}@{_ID_ASSIGN}{_NICKNAME_SUFFIX}\s*@{_TRAILING_PUNCT}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"{_AT_BOUNDARY}@{_ID_ASSIGN}{_TRAILING_PUNCT}",
        re.IGNORECASE,
    ),
    re.compile(r"(?<!\w)<@!?(?P<uid>\d{4,20})>"),
    re.compile(rf"{_BARE_AT_BOUNDARY}(?:@(?=\s*[\[【])\s*)?[\[【\(（]\s*@\s*(?P<uid>\d{{4,20}})\s*@?\s*[\]】\)）]"),
    re.compile(rf"{_BARE_AT_BOUNDARY}@\s*(?P<uid>\d{{4,20}})\s*@\s*[\]】\)）>]"),
    re.compile(rf"{_BARE_AT_BOUNDARY}@\s*(?P<uid>\d{{5,20}})\s*@?{_TRAILING_PUNCT}"),
]


def _build_at_markup(uid: str, nickname: str | None = None) -> str:
    """将 uid/nickname 清理为标准 `[@id:...@]` 标记。"""
    uid = uid.strip()
    nickname = nickname.strip().strip(";；") if nickname else ""
    if nickname:
        return f"[@id:{uid};nickname:{nickname}@]"
    return f"[@id:{uid}@]"


def _replace_at_match(match: re.Match[str]) -> str:
    return _build_at_markup(match.group("uid"), match.groupdict().get("nickname"))


def _protect_non_at_spans(text: str) -> tuple[str, list[str]]:
    protected_values: list[str] = []

    def replace_match(match: re.Match[str]) -> str:
        protected_values.append(match.group(0))
        return f"{_PROTECTED_TOKEN_PREFIX}{len(protected_values) - 1}{_PROTECTED_TOKEN_SUFFIX}"

    return _PROTECTED_TEXT_PATTERN.sub(replace_match, text), protected_values


def _restore_non_at_spans(text: str, protected_values: list[str]) -> str:
    for index, value in enumerate(protected_values):
        text = text.replace(f"{_PROTECTED_TOKEN_PREFIX}{index}{_PROTECTED_TOKEN_SUFFIX}", value)
    return text


def normalize_malformed_at_markup(text: str) -> str:
    """将常见的 AI 幻觉 @ 写法归一化为 `[@id:xxx@]`。"""

    normalized, protected_values = _protect_non_at_spans(text)
    # 少数嵌套幻觉格式会分步变成下一轮可识别的形态，例如 `@[@id:xxx@]`。
    for _ in range(_MAX_NORMALIZE_PASSES):
        previous = normalized
        for pattern in _AT_MARKUP_PATTERNS:
            normalized = pattern.sub(_replace_at_match, normalized)
        if normalized == previous:
            break

    return _restore_non_at_spans(normalized, protected_values)


def neutralize_at_all_markup(text: str) -> str:
    """将 @全体 标记转换为普通文本，避免未授权触发全体提醒。"""

    normalized = normalize_malformed_at_markup(text)
    return _AT_ALL_MARKUP_PATTERN.sub("@全体成员", normalized)
