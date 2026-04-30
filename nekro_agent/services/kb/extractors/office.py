from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .base import ExtractedKBText, clean_text

_WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_PDF_NO_TEXT_ERROR = "当前 PDF 未提取到可用文本，扫描版 PDF 暂不支持，请上传包含文本层的 PDF"


def extract_docx(file_path: Path) -> ExtractedKBText:
    paragraphs: list[str] = []
    with zipfile.ZipFile(file_path) as archive:
        with archive.open("word/document.xml") as handle:
            tree = ET.parse(handle)
    for paragraph in tree.findall(".//w:body/w:p", _WORD_NS):
        runs = [node.text or "" for node in paragraph.findall(".//w:t", _WORD_NS)]
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)
    return ExtractedKBText(text=clean_text("\n\n".join(paragraphs)))


def extract_pdf(file_path: Path) -> ExtractedKBText:
    reader = None
    import_error: Exception | None = None
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
        except ImportError as e:
            import_error = e
            continue
        reader = module.PdfReader(file_path)  # type: ignore[attr-defined]
        break
    if reader is None:
        raise RuntimeError("当前环境缺少 PDF 文本解析依赖 pypdf，无法抽取 PDF") from import_error

    pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"# Page {index}\n\n{text}")
    if not pages:
        raise RuntimeError(_PDF_NO_TEXT_ERROR)
    return ExtractedKBText(text=clean_text("\n\n".join(pages)))
