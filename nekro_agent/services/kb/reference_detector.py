"""
知识库引用关系自动检测。

检测逻辑（按置信度由高到低）：
  1. Markdown 链接：[文字](filename) 精确匹配目标文件名
  2. 中文书名号：《目标标题》 精确匹配
  3. 裸文件名（含扩展名）出现在正文
  4. 标题直接提及（≥4 字，避免误判常见短词）

范围策略：
  - 同分组（category 相同）内互相检测。
  - 文件无分组（category 为空）时，与所有同样无分组的文件互相检测。
  - 新文件索引完成后，额外反向扫描同组内已有文件，建立"其他文件 → 新文件"的引用。
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


def _stem(filename: str) -> str:
    return Path(filename).stem


def _detect_mentions(text: str, target_title: str, target_filename: str) -> str | None:
    """在 text 中检测是否引用了 target，返回引用描述字符串，未检测到返回 None。"""
    filename_stem = _stem(target_filename)

    # 1. Markdown 链接
    for match in _MD_LINK_RE.finditer(text):
        link_href = Path(match.group(2).strip()).name
        if link_href == target_filename or link_href == filename_stem:
            link_text = match.group(1).strip()
            return f"链接：{link_text}" if link_text else f"链接到 {target_filename}"

    # 2. 中文书名号
    if f'《{target_title}》' in text:
        return f"引用《{target_title}》"

    # 3. 裸文件名（>=6 字符避免误判短名）
    if len(target_filename) >= 6 and target_filename in text:
        return f"提及文件 {target_filename}"

    # 4. 标题直接提及（>=4 字避免误判短词）
    if len(target_title) >= 4 and target_title in text:
        return f'提及"{target_title}"'

    return None


async def detect_and_sync_document_references(workspace_id: int, document_id: int) -> int:
    """
    扫描指定文档，检测它对同一工作区同分组内其他文档的引用（出向），并同步到数据库。
    同时反向扫描同组内其他文档，建立它们对本文档的引用（入向）。

    - 自动引用（is_auto=True）在每次调用时先清空重建
    - 手动引用（is_auto=False）不受影响
    - 返回本次新建的引用总数
    """
    source_doc = await DBKBDocument.get_or_none(id=document_id, workspace_id=workspace_id)
    if source_doc is None:
        return 0

    # 同分组过滤
    same_group_filter = {"workspace_id": workspace_id, "is_enabled": True}
    if source_doc.category:
        same_group_filter["category"] = source_doc.category

    peers = await DBKBDocument.filter(**same_group_filter).exclude(id=document_id).all()
    if not peers:
        return 0

    total_created = 0

    # ── 出向检测：source_doc 引用了哪些 peer ──────────────────────────────
    source_text = read_normalized_content(source_doc)
    if source_text.strip():
        await DBKBDocumentReference.filter(
            workspace_id=workspace_id,
            source_document_id=document_id,
            is_auto=True,
        ).delete()

        existing_manual_out = set(
            await DBKBDocumentReference.filter(
                workspace_id=workspace_id,
                source_document_id=document_id,
                is_auto=False,
            ).values_list("target_document_id", flat=True)
        )

        for target in peers:
            if target.id in existing_manual_out:
                continue
            description = _detect_mentions(source_text, target.title, target.file_name)
            if description is not None:
                await DBKBDocumentReference.create(
                    workspace_id=workspace_id,
                    source_document_id=document_id,
                    target_document_id=target.id,
                    description=description,
                    is_auto=True,
                )
                total_created += 1
                logger.debug(f"自动引用（出）：{document_id}→{target.id} [{description}]")

    # ── 入向检测：哪些 peer 引用了 source_doc ────────────────────────────
    # 仅更新已存在 peer 中对本文档的自动引用，避免全量重跑 peer 自己的全部引用
    await DBKBDocumentReference.filter(
        workspace_id=workspace_id,
        target_document_id=document_id,
        is_auto=True,
    ).delete()

    existing_manual_in = set(
        await DBKBDocumentReference.filter(
            workspace_id=workspace_id,
            target_document_id=document_id,
            is_auto=False,
        ).values_list("source_document_id", flat=True)
    )

    for peer in peers:
        if peer.id in existing_manual_in:
            continue
        peer_text = read_normalized_content(peer)
        if not peer_text.strip():
            continue
        description = _detect_mentions(peer_text, source_doc.title, source_doc.file_name)
        if description is not None:
            await DBKBDocumentReference.create(
                workspace_id=workspace_id,
                source_document_id=peer.id,
                target_document_id=document_id,
                description=description,
                is_auto=True,
            )
            total_created += 1
            logger.debug(f"自动引用（入）：{peer.id}→{document_id} [{description}]")

    if total_created:
        logger.info(f"文档 {document_id}（{source_doc.title}）检测完成，共建立 {total_created} 条引用")
    return total_created


async def detect_and_sync_asset_references(asset_id: int) -> int:
    """
    扫描指定全局资产，检测它对同分组内其他资产的引用（出向），
    同时反向扫描同组内其他资产，建立它们对本资产的引用（入向）。
    返回本次新建的引用总数。
    """
    source_asset = await DBKBAsset.get_or_none(id=asset_id)
    if source_asset is None:
        return 0

    same_group_filter = {"is_enabled": True}
    if source_asset.category:
        same_group_filter["category"] = source_asset.category

    peers = await DBKBAsset.filter(**same_group_filter).exclude(id=asset_id).all()
    if not peers:
        return 0

    total_created = 0

    # ── 出向检测 ──────────────────────────────────────────────────────────
    source_text = read_asset_normalized_content(source_asset)
    if source_text.strip():
        await DBKBAssetReference.filter(source_asset_id=asset_id, is_auto=True).delete()

        existing_manual_out = set(
            await DBKBAssetReference.filter(
                source_asset_id=asset_id,
                is_auto=False,
            ).values_list("target_asset_id", flat=True)
        )

        for target in peers:
            if target.id in existing_manual_out:
                continue
            description = _detect_mentions(source_text, target.title, target.file_name)
            if description is not None:
                await DBKBAssetReference.create(
                    source_asset_id=asset_id,
                    target_asset_id=target.id,
                    description=description,
                    is_auto=True,
                )
                total_created += 1
                logger.debug(f"自动引用（出）：资产 {asset_id}→{target.id} [{description}]")

    # ── 入向检测 ──────────────────────────────────────────────────────────
    await DBKBAssetReference.filter(target_asset_id=asset_id, is_auto=True).delete()

    existing_manual_in = set(
        await DBKBAssetReference.filter(
            target_asset_id=asset_id,
            is_auto=False,
        ).values_list("source_asset_id", flat=True)
    )

    for peer in peers:
        if peer.id in existing_manual_in:
            continue
        peer_text = read_asset_normalized_content(peer)
        if not peer_text.strip():
            continue
        description = _detect_mentions(peer_text, source_asset.title, source_asset.file_name)
        if description is not None:
            await DBKBAssetReference.create(
                source_asset_id=peer.id,
                target_asset_id=asset_id,
                description=description,
                is_auto=True,
            )
            total_created += 1
            logger.debug(f"自动引用（入）：资产 {peer.id}→{asset_id} [{description}]")

    if total_created:
        logger.info(f"资产 {asset_id}（{source_asset.title}）检测完成，共建立 {total_created} 条引用")
    return total_created


async def detect_workspace_references(workspace_id: int) -> int:
    """对工作区所有 ready 文档重跑一遍出向检测，返回总建立的引用数。"""
    docs = await DBKBDocument.filter(workspace_id=workspace_id, sync_status="ready").all()
    total = 0
    for doc in docs:
        # 全量重建时只做出向，避免 N² 重复写入
        source_text = read_normalized_content(doc)
        if not source_text.strip():
            continue
        await DBKBDocumentReference.filter(
            workspace_id=workspace_id,
            source_document_id=doc.id,
            is_auto=True,
        ).delete()
        same_group_filter = {"workspace_id": workspace_id, "is_enabled": True}
        if doc.category:
            same_group_filter["category"] = doc.category
        peers = await DBKBDocument.filter(**same_group_filter).exclude(id=doc.id).all()
        existing_manual_out = set(
            await DBKBDocumentReference.filter(
                workspace_id=workspace_id,
                source_document_id=doc.id,
                is_auto=False,
            ).values_list("target_document_id", flat=True)
        )
        for target in peers:
            if target.id in existing_manual_out:
                continue
            description = _detect_mentions(source_text, target.title, target.file_name)
            if description is not None:
                await DBKBDocumentReference.create(
                    workspace_id=workspace_id,
                    source_document_id=doc.id,
                    target_document_id=target.id,
                    description=description,
                    is_auto=True,
                )
                total += 1
    return total
