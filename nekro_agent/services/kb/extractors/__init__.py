from __future__ import annotations

from pathlib import Path

from .base import ExtractedKBText, guess_kb_format
from .html import extract_html
from .office import extract_docx, extract_pdf
from .tabular import extract_csv, extract_json_like, extract_yaml_like
from .text import extract_markdown_or_text

__all__ = [
    "ExtractedKBText",
    "extract_source_file",
    "guess_kb_format",
]


def extract_source_file(file_path: Path, file_name: str) -> ExtractedKBText:
    detected_format = guess_kb_format(file_name)
    if detected_format in {"markdown", "text"}:
        return extract_markdown_or_text(file_path)
    if detected_format == "html":
        return extract_html(file_path)
    if detected_format == "json":
        return extract_json_like(file_path)
    if detected_format == "yaml":
        return extract_yaml_like(file_path)
    if detected_format == "csv":
        return extract_csv(file_path)
    if detected_format == "docx":
        return extract_docx(file_path)
    if detected_format == "pdf":
        return extract_pdf(file_path)
    return extract_markdown_or_text(file_path)
