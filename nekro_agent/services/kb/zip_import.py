"""知识库 Zip 批量导入：安全解压 + 按目录结构映射导入元数据 + 导入编排。

限制（上传大小 / 解压总大小 / 文件数）由集中配置 KB_ZIP_* 控制，可在不改代码的情况下调节；
配置在模块加载时读取，修改后需重启服务生效。

内存行为说明: 上传的 zip 会一次性读入内存（受 _MAX_UPLOAD_SIZE 约束），
解压落盘后逐文件读入内存导入（解压总量受 _MAX_EXTRACT_SIZE 约束）。
若未来放宽大小上限，需同步评估内存峰值或改为流式/分块读取。
"""

import io
import posixpath
import shutil
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import UploadFile
from tortoise.exceptions import IntegrityError

from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.errors import ValidationError
from nekro_agent.schemas.kb import KBZipImportResponse

logger = get_sub_logger("kb.zip_import")

# 限制常量（模块加载时从配置读取，修改后需重启生效）
_MAX_UPLOAD_SIZE = max(1, int(config.KB_ZIP_MAX_UPLOAD_SIZE_MB)) * 1024 * 1024
_MAX_EXTRACT_SIZE = max(1, int(config.KB_ZIP_MAX_EXTRACT_SIZE_MB)) * 1024 * 1024
_MAX_FILES = max(1, int(config.KB_ZIP_MAX_FILES))


@dataclass
class ZipImportEntry:
    """解压出的单个可导入文件条目"""

    path: Path  # 磁盘绝对路径
    source_path: str  # 相对解压根目录的完整路径（正斜杠），作为知识库 source_path
    category: str  # 目录部分（带尾部斜杠），作为知识库分类；无目录时为空


def _derive_entry(rel_path: str, abs_path: Path) -> ZipImportEntry:
    parts = rel_path.split("/")
    directory_path = "/".join(parts[:-1])
    return ZipImportEntry(
        path=abs_path,
        source_path=rel_path,
        category=f"{directory_path}/" if directory_path else "",
    )


def _validate_zip_limits(members: list[zipfile.ZipInfo]) -> None:
    """校验文件条目数与解压后总大小（防 zip 炸弹）。"""
    if len(members) > _MAX_FILES:
        raise ValueError(f"zip 包文件数超出上限（最大 {_MAX_FILES} 个）")
    total_size = 0
    for member in members:
        total_size += member.file_size
        if total_size > _MAX_EXTRACT_SIZE:
            raise ValueError(
                f"zip 包解压后总大小超出上限（最大 {_MAX_EXTRACT_SIZE // 1024 // 1024} MB）"
            )


def _normalize_member_path(name: str) -> str | None:
    """规范化条目路径：统一正斜杠、解析 ./ 与 ..、去除绝对路径前导；空路径返回 None。"""
    rel_path = posixpath.normpath(name.replace("\\", "/")).lstrip("/")
    return rel_path or None


def _safe_dest_path(target_root: Path, rel_path: str, raw_name: str) -> Path:
    """校验解压目标必须落在 target_root 内（防 zip-slip 路径穿越）。"""
    dest = (target_root / rel_path).resolve()
    if not dest.is_relative_to(target_root):
        raise ValueError(f"zip 包包含非法路径: {raw_name}")
    return dest


def extract_zip_safe(content: bytes, target_dir: Path) -> list[ZipImportEntry]:
    """安全解压 zip 内容到 target_dir，返回可导入文件条目列表。

    条目映射（source_path/category）在解压阶段直接从 zip 条目名推导，避免二次文件系统遍历。
    """
    target_root = target_dir.resolve()
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        members = [member for member in zf.infolist() if not member.is_dir()]
        _validate_zip_limits(members)

        # 按条目名去重（后出现的覆盖先出现的，与解压落盘行为一致）
        entries_by_path: dict[str, ZipImportEntry] = {}
        for member in members:
            rel_path = _normalize_member_path(member.filename)
            if not rel_path:
                continue
            dest = _safe_dest_path(target_root, rel_path, member.filename)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            entries_by_path[rel_path] = _derive_entry(rel_path, dest)
    return list(entries_by_path.values())


CreateFromUploadFn = Callable[[ZipImportEntry, bytes], Awaitable[tuple[object, bool]]]
ScheduleRebuildFn = Callable[[object], Awaitable[None]]


def _friendly_entry_error(error: Exception) -> str:
    """将条目级异常清洗为用户可读消息；完整细节由调用方记录日志。"""
    if isinstance(error, FileExistsError):
        return "目标路径已存在"
    if isinstance(error, IntegrityError):
        return "目标路径或内容与现有条目冲突"
    if isinstance(error, ValueError):
        return str(error) or "文件内容无效"
    return "导入失败（详见服务端日志）"


async def _read_and_validate_zip_upload(file: UploadFile) -> bytes:
    """校验并读取 zip 上传内容。"""
    file_name = file.filename or ""
    if not file_name.lower().endswith(".zip"):
        raise ValidationError(reason="仅支持上传 zip 压缩包")
    upload_size = getattr(file, "size", None)
    if upload_size is not None and upload_size > _MAX_UPLOAD_SIZE:
        raise ValidationError(reason=f"文件大小超出限制（最大 {_MAX_UPLOAD_SIZE // 1024 // 1024} MB）")
    content = await file.read()
    if len(content) > _MAX_UPLOAD_SIZE:
        raise ValidationError(reason=f"文件大小超出限制（最大 {_MAX_UPLOAD_SIZE // 1024 // 1024} MB）")
    return content


async def _import_entries(
    entries: list[ZipImportEntry],
    allowed_exts: set[str],
    create_from_upload: CreateFromUploadFn,
    schedule_rebuild: ScheduleRebuildFn | None,
    result: KBZipImportResponse,
) -> None:
    """按扩展名过滤并逐条导入，单条失败不中断整批。"""
    allowed_exts_lower = {ext.lower() for ext in allowed_exts}
    filtered = [entry for entry in entries if Path(entry.source_path).suffix.lower() in allowed_exts_lower]
    result.skipped = len(entries) - len(filtered)

    for entry in filtered:
        try:
            obj, reused_existing = await create_from_upload(entry, entry.path.read_bytes())
            if not reused_existing and schedule_rebuild is not None:
                await schedule_rebuild(obj)
            if reused_existing:
                result.reused += 1
            else:
                result.imported += 1
        except Exception as e:
            logger.warning(f"zip 导入条目失败: {entry.source_path}, error: {e}", exc_info=True)
            result.failed += 1
            result.errors.append(f"{entry.source_path}: {_friendly_entry_error(e)}")


async def import_zip_with_upload(
    file: UploadFile,
    allowed_exts: set[str],
    create_from_upload: CreateFromUploadFn,
    schedule_rebuild: ScheduleRebuildFn | None = None,
) -> KBZipImportResponse:
    """zip 上传导入编排：校验 → 安全解压 → 扩展名过滤 → 逐条导入并统计。

    create_from_upload 接收 (entry, content_bytes) 返回 (obj, reused_existing)；
    reused 时不触发重建索引。单条导入失败不中断整批，完整异常细节记录日志，
    客户端仅收到清洗后的消息。
    """
    content = await _read_and_validate_zip_upload(file)
    result = KBZipImportResponse(
        ok=False,
        imported=0,
        reused=0,
        skipped=0,
        failed=0,
        errors=[],
    )
    with TemporaryDirectory(prefix="kb-zip-") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        try:
            entries = extract_zip_safe(content, tmp_dir)
        except (zipfile.BadZipFile, ValueError) as e:
            raise ValidationError(reason=str(e)) from e
        await _import_entries(
            entries=entries,
            allowed_exts=allowed_exts,
            create_from_upload=create_from_upload,
            schedule_rebuild=schedule_rebuild,
            result=result,
        )
    result.ok = result.imported + result.reused > 0 or result.failed == 0
    return result
