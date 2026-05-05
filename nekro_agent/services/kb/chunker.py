from __future__ import annotations

import re
from dataclasses import dataclass

CHUNK_MAX_CHARS = 1200
CHUNK_MIN_CHARS = 200

_BREAK_TOKENS = (
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    ". ",
    "! ",
    "? ",
    "; ",
    "；",
    ",",
    "，",
    "、",
    " ",
    "\t",
)


@dataclass
class ChunkDraft:
    heading_path: str
    content: str
    char_start: int
    char_end: int


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _iter_paragraph_spans(content: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    for match in re.finditer(r"\n\s*\n", content):
        start, end = _trim_span(content, cursor, match.start())
        if start < end:
            spans.append((start, end))
        cursor = match.end()
    start, end = _trim_span(content, cursor, len(content))
    if start < end:
        spans.append((start, end))
    return spans


def _find_split_index(text: str, start: int, hard_end: int) -> int:
    window = text[start:hard_end]
    lower_bound = min(CHUNK_MIN_CHARS, len(window))
    for token in _BREAK_TOKENS:
        position = window.rfind(token, lower_bound)
        if position != -1:
            return start + position + len(token)
    return hard_end


def _merge_tail_span(content: str, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if len(spans) < 2:
        return spans
    prev_start, prev_end = spans[-2]
    last_start, last_end = spans[-1]
    if (last_end - last_start) >= CHUNK_MIN_CHARS:
        return spans
    merged_start, merged_end = _trim_span(content, prev_start, last_end)
    if merged_end - merged_start <= CHUNK_MAX_CHARS:
        spans[-2] = (merged_start, merged_end)
        spans.pop()
    return spans


def _split_oversized_span(content: str, start: int, end: int) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = start

    while cursor < end:
        cursor, _ = _trim_span(content, cursor, end)
        if cursor >= end:
            break
        remaining = end - cursor
        if remaining <= CHUNK_MAX_CHARS:
            spans.append((cursor, end))
            break
        split_index = _find_split_index(content, cursor, min(end, cursor + CHUNK_MAX_CHARS))
        if split_index <= cursor:
            split_index = min(end, cursor + CHUNK_MAX_CHARS)
        chunk_start, chunk_end = _trim_span(content, cursor, split_index)
        if chunk_start < chunk_end:
            spans.append((chunk_start, chunk_end))
        cursor = split_index

    return _merge_tail_span(content, spans)


def _split_long_text(content: str, heading_path: str, base_start: int) -> list[ChunkDraft]:
    paragraph_spans = _iter_paragraph_spans(content)
    if not paragraph_spans:
        return []

    chunk_spans: list[tuple[int, int]] = []
    current_start: int | None = None
    current_end: int | None = None

    for paragraph_start, paragraph_end in paragraph_spans:
        paragraph_length = paragraph_end - paragraph_start
        if paragraph_length > CHUNK_MAX_CHARS:
            if current_start is not None and current_end is not None:
                start, end = _trim_span(content, current_start, current_end)
                if start < end:
                    chunk_spans.append((start, end))
                current_start = None
                current_end = None
            chunk_spans.extend(_split_oversized_span(content, paragraph_start, paragraph_end))
            continue

        if current_start is None or current_end is None:
            current_start = paragraph_start
            current_end = paragraph_end
            continue

        candidate_start, candidate_end = _trim_span(content, current_start, paragraph_end)
        if (candidate_end - candidate_start) > CHUNK_MAX_CHARS:
            start, end = _trim_span(content, current_start, current_end)
            if start < end:
                chunk_spans.append((start, end))
            current_start = paragraph_start
            current_end = paragraph_end
        else:
            current_end = paragraph_end

    if current_start is not None and current_end is not None:
        start, end = _trim_span(content, current_start, current_end)
        if start < end:
            chunk_spans.append((start, end))

    chunk_spans = _merge_tail_span(content, chunk_spans)
    return [
        ChunkDraft(
            heading_path=heading_path,
            content=content[start:end],
            char_start=base_start + start,
            char_end=base_start + end,
        )
        for start, end in chunk_spans
        if content[start:end].strip()
    ]


def split_text_into_chunks(text: str) -> list[ChunkDraft]:
    lines = text.splitlines()
    sections: list[tuple[str, str, int]] = []
    heading_stack: list[str] = []
    current_lines: list[str] = []
    current_heading = ""
    current_start = 0
    cursor = 0

    def flush_section() -> None:
        nonlocal current_lines
        if not current_lines:
            return
        section_text = "\n".join(current_lines)
        start, end = _trim_span(section_text, 0, len(section_text))
        if start < end:
            sections.append((current_heading, section_text[start:end], current_start + start))
        current_lines = []

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if heading_match:
            flush_section()
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            heading_stack[:] = heading_stack[: level - 1]
            heading_stack.append(title)
            current_heading = " > ".join(heading_stack)
            current_start = cursor
            current_lines.append(line)
        else:
            if not current_lines:
                current_start = cursor
            current_lines.append(line)
        cursor += len(line) + 1
    flush_section()

    if not sections:
        start, end = _trim_span(text, 0, len(text))
        sections = [("", text[start:end], start)] if start < end else []

    chunks: list[ChunkDraft] = []
    for heading_path, section_text, start in sections:
        chunks.extend(_split_long_text(section_text, heading_path, start))
    return [chunk for chunk in chunks if chunk.content.strip()]
