"""
知识库引用关系自动检测。

检测逻辑（按置信度由高到低）：
  1. Markdown 链接：[文字](filename) 精确匹配目标文件名
  2. 中文书名号：《目标标题》 精确匹配
  3. 裸文件名（含扩展名）出现在正文
  4. 标题直接提及（≥4 字，避免误判常见短词）
"""
from __future__ import annotations

import re
from pathlib import Path

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_kb_asset import DBKBAsset
from nekro_agent.models.db_kb_asset_reference import DBKBAssetReference
from nekro_agent.models.db_kb_document import DBKBDocument
from nekro_agent.models.db_kb_document_reference import DBKBDocumentReference
from nekro_agent.services.kb.document_service import read_normalized_content
from nekro_agent.services.kb.library_service import read_asset_normalized_content

logger = get_sub_logger("kb.reference_detector")

_MD_LINK_RE = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
_TITLE_QUOTE_RE_TEMPLATE = r'《{title}》'


def _stem(filename: str) -> str:
    """返回不含扩展名的文件名主体。"""
    return Path(filename).stem


def _detect_mentions(text: str, target_title: str, target_filename: str) -> str | None:
    """
    在 text 中检测是否引用了 target。
    返回引用描述字符串（非 None 即命中），None 表示未检测到。
    """
    filename_stem = _stem(target_filename)

    # 1. Markdown 链接：[文字](filename) 或 [文字](filename.ext)
    for match in _MD_LINK_RE.finditer(text):
        link_href = Path(match.group(2).strip()).name
        if link_href == target_filename or link_href == filename_stem:
            link_text = match.group(1).strip()
            return f"链接：{link_text}" if link_text else f"链接到 {target_filename}"

    # 2. 中文书名号 《title》
    if f'《{target_title}》' in text:
        return f"引用《{target_title}》"

    # 3. 裸文件名出现（含扩展名，避免短文件名误判）
    if len(target_filename) >= 6 and target_filename in text:
        return f"提及文件 {target_filename}"

    # 4. 标题直接提及（≥4 字，避免短标题带来误判）
    if len(target_title) >= 4 and target_title in text:
        return f'提及"{target_title}"'

    return None


async def detect_and_sync_document_references(workspace_id: int, document_id: int) -> int:
    """
    扫描指定工作区文档，自动检测其对同一工作区内其他文档的引用，并同步到数据库。

    - 删除该文档已有的自动引用（is_auto=True），重新检测写入
    - 手动引用（is_auto=False）不受影响
    - 返回新建的引用数量
    """
    source_doc = await DBKBDocument.get_or_none(id=document_id, workspace_id=workspace_id)
    if source_doc is None:
        return 0

    normalized_text = read_normalized_content(source_doc)
    if not normalized_text.strip():
        return 0

    all_docs = await DBKBDocument.filter(workspace_id=workspace_id, is_enabled=True).exclude(id=document_id).all()
    if not all_docs:
        return 0

    # 清除旧的自动引用
    await DBKBDocumentReference.filter(
        workspace_id=workspace_id,
        source_document_id=document_id,
        is_auto=True,
    ).delete()

    # 检测已有手动引用，不重复创建
    existing_manual = await DBKBDocumentReference.filter(
        workspace_id=workspace_id,
        source_document_id=document_id,
        is_auto=False,
    ).values_list("target_document_id", flat=True)
    manual_target_ids: set[int] = set(existing_manual)

    created = 0
    for target in all_docs:
        if target.id in manual_target_ids:
            continue
        description = _detect_mentions(normalized_text, target.title, target.file_name)
        if description is not None:
            await DBKBDocumentReference.create(
                workspace_id=workspace_id,
                source_document_id=document_id,
                target_document_id=target.id,
                description=description,
                is_auto=True,
            )
            created += 1
            logger.debug(
                f"自动引用：文档 {document_id}（{source_doc.title}）→ {target.id}（{target.title}）[{description}]"
            )

    if created:
        logger.info(f"文档 {document_id}（{source_doc.title}）自动检测到 {created} 条引用")
    return created


async def detect_and_sync_asset_references(asset_id: int) -> int:
    """
    扫描指定全局资产，自动检测其对同一全局库中其他资产的引用，并同步到数据库。
    返回新建的引用数量。
    """
    source_asset = await DBKBAsset.get_or_none(id=asset_id)
    if source_asset is None:
        return 0

    normalized_text = read_asset_normalized_content(source_asset)
    if not normalized_text.strip():
        return 0

    all_assets = await DBKBAsset.filter(is_enabled=True).exclude(id=asset_id).all()
    if not all_assets:
        return 0

    await DBKBAssetReference.filter(source_asset_id=asset_id, is_auto=True).delete()

    existing_manual = await DBKBAssetReference.filter(
        source_asset_id=asset_id,
        is_auto=False,
    ).values_list("target_asset_id", flat=True)
    manual_target_ids: set[int] = set(existing_manual)

    created = 0
    for target in all_assets:
        if target.id in manual_target_ids:
            continue
        description = _detect_mentions(normalized_text, target.title, target.file_name)
        if description is not None:
            await DBKBAssetReference.create(
                source_asset_id=asset_id,
                target_asset_id=target.id,
                description=description,
                is_auto=True,
            )
            created += 1
            logger.debug(
                f"自动引用：资产 {asset_id}（{source_asset.title}）→ {target.id}（{target.title}）[{description}]"
            )

    if created:
        logger.info(f"资产 {asset_id}（{source_asset.title}）自动检测到 {created} 条引用")
    return created


async def detect_workspace_references(workspace_id: int) -> int:
    """对工作区所有文档重新跑一遍自动检测，返回总建立的引用数。用于全量重建索引后调用。"""
    docs = await DBKBDocument.filter(workspace_id=workspace_id, sync_status="ready").all()
    total = 0
    for doc in docs:
        total += await detect_and_sync_document_references(workspace_id, doc.id)
    return total
