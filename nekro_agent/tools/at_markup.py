import re
from collections.abc import Iterable

USER_ID_PATTERN = r"(?P<uid>all|[A-Za-z0-9][A-Za-z0-9_.#\-]{2,127})"
# 旧实现 `_NICKNAME_VALUE = r"[^@\]\)>】）\n]+?"` 排除了 `)` `）` `>` `】`，
# 导致含中文/全角括号的昵称（例如 `KroMiose谬锶（摆烂中）`）无法匹配任何 At 模式，
# 进而让 `<At:<At:[@id:xxx;nickname:KroMiose谬锶（摆烂中）@]>>` 这类嵌套形态整段残留。
# 这里把排除集收紧到「真正会让后续 `_BRACKET_AT_CLOSE` / `;` 字段分隔符失配」的字符，
# 与 `_CANONICAL_NICKNAME_VALUE` 保持一致；嵌套解析交给 normalize 的多轮 sub 收敛。
_NICKNAME_VALUE = r"[^@\]\n;]+?"
_CANONICAL_NICKNAME_VALUE = r"[^@\]\n]+?"
_NICKNAME_GROUP = rf"(?P<nickname>{_NICKNAME_VALUE})"
_CANONICAL_NICKNAME_GROUP = rf"(?P<nickname>{_CANONICAL_NICKNAME_VALUE})"
_NICKNAME_SUFFIX = rf"(?:\s*[;；]\s*nickname\s*[=:：]\s*{_NICKNAME_GROUP})?"
TRAILING_PUNCT = r"(?=$|[\s,，。.!！？;；:：\)\]】>）])"
_AT_BOUNDARY = r"(?<![\w\[])"
_BARE_AT_BOUNDARY = r"(?<![\w\[/])"
_ID_ASSIGN = rf"\s*id\s*[=:：]\s*{USER_ID_PATTERN}"
_BRACKET_AT_CLOSE = r"\s*[;；]?\s*@?\s*[\]】]"
_MAX_NORMALIZE_PASSES = 3
_PROTECTED_TEXT_PATTERN = re.compile(
    r"```[\s\S]*?```|`[^`\n]*`|https?://[^\s<>'\"，。！？、]+|[\w.+\-]+@[\w.\-]+\.[A-Za-z]{2,}",
)
_PROTECTED_TOKEN_PREFIX = "\uE000AT_PROTECTED_"
_PROTECTED_TOKEN_SUFFIX = "\uE001"
_PROTECTED_TOKEN_PATTERN = re.compile(
    rf"{re.escape(_PROTECTED_TOKEN_PREFIX)}(?P<index>\d+){re.escape(_PROTECTED_TOKEN_SUFFIX)}",
)
_AT_ALL_MARKUP_PATTERN = re.compile(r"\[@(?:id:)?all(?:;nickname:[^@\]\n]+)?@\]", re.IGNORECASE)

AT_MARKUP_PATTERN = re.compile(
    rf"\[@id:{USER_ID_PATTERN}(?:;nickname:{_CANONICAL_NICKNAME_GROUP})?@\]",
)

_GENERIC_AT_PATTERNS: list[re.Pattern[str]] = [
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
        rf"{_AT_BOUNDARY}@{_ID_ASSIGN}{_NICKNAME_SUFFIX}\s*@{TRAILING_PUNCT}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"{_AT_BOUNDARY}@{_ID_ASSIGN}{TRAILING_PUNCT}",
        re.IGNORECASE,
    ),
]

_DISCORD_AT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?<!\w)<@!?(?P<uid>\d{4,20})>"),
]

_BARE_NUMERIC_AT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(rf"{_BARE_AT_BOUNDARY}(?:@(?=\s*[\[【])\s*)?[\[【\(（]\s*@\s*(?P<uid>\d{{4,20}})\s*@?\s*[\]】\)）]"),
    re.compile(rf"{_BARE_AT_BOUNDARY}@\s*(?P<uid>\d{{4,20}})\s*@\s*[\]】\)）>]"),
    re.compile(rf"{_BARE_AT_BOUNDARY}@\s*(?P<uid>\d{{5,20}})\s*@?{TRAILING_PUNCT}"),
]

_ALL_AT_MARKUP_PATTERNS: tuple[re.Pattern[str], ...] = (
    *_GENERIC_AT_PATTERNS,
    *_DISCORD_AT_PATTERNS,
    *_BARE_NUMERIC_AT_PATTERNS,
)


def build_at_markup(uid: str, nickname: str | None = None) -> str:
    """将 uid/nickname 清理为标准 `[@id:...@]` 标记。"""
    uid = uid.strip()
    nickname = nickname.strip().strip(";；") if nickname else ""
    if nickname:
        return f"[@id:{uid};nickname:{nickname}@]"
    return f"[@id:{uid}@]"


def _replace_at_match(match: re.Match[str]) -> str:
    return build_at_markup(match.group("uid"), match.groupdict().get("nickname"))


def protect_spans(text: str, pattern: re.Pattern[str]) -> tuple[str, list[str]]:
    """将指定 pattern 命中的片段替换为临时 token，并返回原始片段列表。"""
    protected_values: list[str] = []

    def replace_match(match: re.Match[str]) -> str:
        protected_values.append(match.group(0))
        return f"{_PROTECTED_TOKEN_PREFIX}{len(protected_values) - 1}{_PROTECTED_TOKEN_SUFFIX}"

    return pattern.sub(replace_match, text), protected_values


def restore_spans(text: str, protected_values: list[str]) -> str:
    """恢复由 protect_spans 生成的临时 token。"""

    def replace_match(match: re.Match[str]) -> str:
        index = int(match.group("index"))
        if index >= len(protected_values):
            return match.group(0)
        return protected_values[index]

    return _PROTECTED_TOKEN_PATTERN.sub(replace_match, text)


def protect_non_at_spans(text: str) -> tuple[str, list[str]]:
    """保护 URL、邮箱、行内代码和围栏代码块，避免误改其中的 @ 文本。"""
    return protect_spans(text, _PROTECTED_TEXT_PATTERN)


def restore_non_at_spans(text: str, protected_values: list[str]) -> str:
    """恢复由 protect_non_at_spans 保护的文本片段。"""
    return restore_spans(text, protected_values)


def _apply_patterns(text: str, patterns: Iterable[re.Pattern[str]]) -> str:
    for pattern in patterns:
        text = pattern.sub(_replace_at_match, text)
    return text


def normalize_malformed_at_markup(text: str) -> str:
    """将跨平台通用的 AI 幻觉 @ 写法归一化为 `[@id:xxx@]`。"""

    normalized, protected_values = protect_non_at_spans(text)
    # 少数嵌套幻觉格式会分步变成下一轮可识别的形态，例如 `@[@id:xxx@]`。
    for _ in range(_MAX_NORMALIZE_PASSES):
        previous = normalized
        normalized = _apply_patterns(normalized, _ALL_AT_MARKUP_PATTERNS)
        if normalized == previous:
            break

    return restore_non_at_spans(normalized, protected_values)


def neutralize_at_all_markup(text: str) -> str:
    """将 @全体 标记转换为普通文本，避免未授权触发全体提醒。"""

    normalized = normalize_malformed_at_markup(text)
    return _AT_ALL_MARKUP_PATTERN.sub("@全体成员", normalized)
