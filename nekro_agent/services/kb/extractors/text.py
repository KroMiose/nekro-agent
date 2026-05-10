from __future__ import annotations

from pathlib import Path

from .base import ExtractedKBText, clean_text


def extract_markdown_or_text(file_path: Path) -> ExtractedKBText:
    return ExtractedKBText(text=clean_text(file_path.read_text(encoding="utf-8", errors="replace")))
