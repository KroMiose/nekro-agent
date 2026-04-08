from __future__ import annotations

import re
from html import unescape
from pathlib import Path

from pydantic import BaseModel


class ExtractedKBText(BaseModel):
    text: str


def clean_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = unescape(normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def guess_kb_format(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    return {
        ".md": "markdown",
        ".txt": "text",
        ".html": "html",
        ".htm": "html",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".csv": "csv",
        ".pdf": "pdf",
        ".docx": "docx",
    }.get(suffix, "text")
