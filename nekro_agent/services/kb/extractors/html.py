import re
from pathlib import Path

from .base import ExtractedKBText, clean_text

_HTML_BLOCK_MAP = [
    (re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL), r"# \1\n\n"),
    (re.compile(r"<h2[^>]*>(.*?)</h2>", re.IGNORECASE | re.DOTALL), r"## \1\n\n"),
    (re.compile(r"<h3[^>]*>(.*?)</h3>", re.IGNORECASE | re.DOTALL), r"### \1\n\n"),
    (re.compile(r"<h4[^>]*>(.*?)</h4>", re.IGNORECASE | re.DOTALL), r"#### \1\n\n"),
    (re.compile(r"<li[^>]*>(.*?)</li>", re.IGNORECASE | re.DOTALL), r"- \1\n"),
    (re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL), r"\1\n\n"),
    (re.compile(r"<br\s*/?>", re.IGNORECASE), "\n"),
]


def extract_html(file_path: Path) -> ExtractedKBText:
    raw = file_path.read_text(encoding="utf-8", errors="replace")
    text = raw
    for pattern, replacement in _HTML_BLOCK_MAP:
        text = pattern.sub(replacement, text)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return ExtractedKBText(text=clean_text(text))
