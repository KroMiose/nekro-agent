import re

_USER_ID_PATTERN = r"(?P<uid>all|[A-Za-z0-9][A-Za-z0-9_.#\-]{2,127})"
_NICKNAME_PATTERN = r"(?:\s*[;；]\s*nickname\s*[=:：]\s*(?P<nickname>[^@\]\)>】）\n]+?))?"

AT_MARKUP_PATTERN = re.compile(
    rf"\[@id:{_USER_ID_PATTERN}(?:;nickname:(?P<nickname>[^@\]\n]+?))?@\]",
)

_AT_MARKUP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        rf"[\[【]\s*CQ\s*:\s*at\s*,\s*qq\s*=\s*{_USER_ID_PATTERN}"
        r"(?:\s*,\s*(?:name|card|nickname)\s*=\s*(?P<nickname>[^,\]】\n]+))?"
        r"(?:\s*,[^\]】]*)?[\]】]",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<!\w)CQ\s*:\s*at\s*,\s*qq\s*=\s*{_USER_ID_PATTERN}"
        r"(?:\s*,\s*(?:name|card|nickname)\s*=\s*(?P<nickname>[^,\]】\n]+))?"
        r"(?=$|[\s,，。.!！？;；:：\)\]】>）])",
        re.IGNORECASE,
    ),
    re.compile(
        rf"[\(（]\s*@?\s*[\[【]\s*@?\s*id\s*[=:：]\s*{_USER_ID_PATTERN}"
        rf"{_NICKNAME_PATTERN}\s*[;；]?\s*@?\s*[\]】]\s*[\)）]",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<!\w)@\s*[\[【]\s*@?\s*id\s*[=:：]\s*{_USER_ID_PATTERN}"
        rf"{_NICKNAME_PATTERN}\s*[;；]?\s*@?\s*[\]】]",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:<\w{{4,12}}\s*\|\s*)?(?:<?At:\s*)?[\[【]\s*@?\s*id\s*[=:：]\s*"
        rf"{_USER_ID_PATTERN}{_NICKNAME_PATTERN}\s*[;；]?\s*@?\s*[\]】](?:>)?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:<?At:\s*)?[\(（]\s*@\s*id\s*[=:：]\s*{_USER_ID_PATTERN}"
        rf"{_NICKNAME_PATTERN}\s*[;；]?\s*@?\s*[\)）](?:>)?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<![\w\[])@\s*id\s*[=:：]\s*{_USER_ID_PATTERN}"
        rf"{_NICKNAME_PATTERN}\s*[;；]?\s*@?\s*[\]】\)）>]",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<![\w\[])@\s*id\s*[=:：]\s*{_USER_ID_PATTERN}"
        rf"{_NICKNAME_PATTERN}\s*@(?=$|[\s,，。.!！？;；:：\)\]】>）])",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<![\w\[])@\s*id\s*[=:：]\s*{_USER_ID_PATTERN}"
        r"(?=$|[\s,，。.!！？;；:：\)\]】>）])",
        re.IGNORECASE,
    ),
    re.compile(r"(?<!\w)<@!?(?P<uid>\d{4,20})>"),
    re.compile(r"(?<!\w)(?:@(?=\s*[\[【])\s*)?[\[【\(（]\s*@\s*(?P<uid>\d{4,20})\s*@?\s*[\]】\)）]"),
    re.compile(r"(?<![\w\[])@\s*(?P<uid>\d{4,20})\s*@\s*[\]】\)）>]"),
    re.compile(r"(?<![\w\[])@\s*(?P<uid>\d{5,20})\s*@?(?=$|[\s,，。.!！？;；:：\)\]】>）])"),
]


def _build_at_markup(uid: str, nickname: str | None = None) -> str:
    uid = uid.strip()
    nickname = nickname.strip().strip(";；") if nickname else ""
    if nickname:
        return f"[@id:{uid};nickname:{nickname}@]"
    return f"[@id:{uid}@]"


def _replace_at_match(match: re.Match[str]) -> str:
    return _build_at_markup(match.group("uid"), match.groupdict().get("nickname"))


def normalize_malformed_at_markup(text: str) -> str:
    """将常见的 AI 幻觉 @ 写法归一化为 `[@id:xxx@]`。"""

    normalized = text
    for _ in range(3):
        previous = normalized
        for pattern in _AT_MARKUP_PATTERNS:
            normalized = pattern.sub(_replace_at_match, normalized)
        if normalized == previous:
            break

    return normalized
