from __future__ import annotations

import csv
import json
from pathlib import Path

import json5

from .base import ExtractedKBText, clean_text


def extract_json_like(file_path: Path) -> ExtractedKBText:
    raw = file_path.read_text(encoding="utf-8", errors="replace")
    try:
        parsed = json5.loads(raw)
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
        return ExtractedKBText(text=clean_text(pretty))
    except Exception:
        return ExtractedKBText(text=clean_text(raw))


def extract_yaml_like(file_path: Path) -> ExtractedKBText:
    return ExtractedKBText(text=clean_text(file_path.read_text(encoding="utf-8", errors="replace")))


def extract_csv(file_path: Path) -> ExtractedKBText:
    rows_text: list[str] = []
    with file_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        return ExtractedKBText(text="")
    header = rows[0]
    rows_text.append("# CSV Table")
    rows_text.append("")
    rows_text.append("## Header")
    rows_text.append(", ".join(header))
    for index, row in enumerate(rows[1:], start=1):
        rows_text.append("")
        rows_text.append(f"## Row {index}")
        for key, value in zip(header, row, strict=False):
            rows_text.append(f"- {key}: {value}")
    return ExtractedKBText(text=clean_text("\n".join(rows_text)))
