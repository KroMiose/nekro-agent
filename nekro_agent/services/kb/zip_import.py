"""知识库 Zip 批量导入：安全解压 + 按目录结构映射导入元数据 + 导入编排。"""

import io
import shutil
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import UploadFile

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.errors import ValidationError

logger = get_sub_logger("kb.zip_import")

# 上传 zip 单包大小上限
KB_ZIP_MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
# 解压后文件总大小上限（防 zip 炸弹）
KB_ZIP_MAX_EXTRACT_SIZE = 500 * 1024 * 1024  # 500 MB
# 单个 zip 允许的最大文件条目数
KB_ZIP_MAX_FILES = 500


@dataclass
class ZipImportEntry:
    """解压出的单个可导入文件条目"""

    path: Path  # 磁盘绝对路径
    source_path: str  # 相对解压根目录的完整路径（正斜杠），作为知识库 source_path
    category: str  # 目录部分（带尾部斜杠），作为知识库分类；无目录时为空


@dataclass
class ZipImportResult:
    """zip 批量导入统计结果"""

    imported: int = 0
    reused: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def _derive_entry(rel_path: str, abs_path: Path) -> ZipImportEntry:
    parts = rel_path.split("/")
    directory_path = "/".join(parts[:-1])
    return ZipImportEntry(
        path=abs_path,
        source_path=rel_path,
        category=f"{directory_path}/" if directory_path else "",
    )


def extract_zip_safe(content: bytes, target_dir: Path) -> list[ZipImportEntry]:
    """安全解压 zip 内容到 target_dir，返回可导入文件条目列表。

    条目映射（source_path/category）在解压阶段直接从 zip 条目名推导，避免二次文件系统遍历。

    防护:
    - zip-slip 路径穿越: 逐条目校验解压目标必须落在 target_dir 内
    - zip 炸弹: 限制文件条目数与解压后总大小
    """
    target_root = target_dir.resolve()
    total_size = 0
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        members = [member for member in zf.infolist() if not member.is_dir()]
        if len(members) > KB_ZIP_MAX_FILES:
            raise ValueError(f"zip 包文件数超出上限（最大 {KB_ZIP_MAX_FILES} 个）")
        for member in members:
            total_size += member.file_size
            if total_size > KB_ZIP_MAX_EXTRACT_SIZE:
                raise ValueError(
                    f"zip 包解压后总大小超出上限（最大 {KB_ZIP_MAX_EXTRACT_SIZE // 1024 // 1024} MB）"
                )
        # 按条目名去重（后出现的覆盖先出现的，与解压落盘行为一致）
        entries_by_path: dict[str, ZipImportEntry] = {}
        for member in members:
            rel_path = member.filename
            dest = (target_root / rel_path).resolve()
            if not dest.is_relative_to(target_root):
                raise ValueError(f"zip 包包含非法路径: {rel_path}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            entries_by_path[rel_path] = _derive_entry(rel_path, dest)
    return list(entries_by_path.values())


async def process_zip_upload(
    file: UploadFile,
    allowed_exts: set[str],
    handle_entry: Callable[[ZipImportEntry], Awaitable[tuple[bool, bool, str | None]]],
) -> ZipImportResult:
    """zip 上传导入编排：校验 → 安全解压 → 扩展名过滤 → 逐条导入并统计。

    handle_entry 返回 (success, reused_existing, error)：error 非空记失败，否则按 success/reused 计数。
    """
    file_name = file.filename or ""
    if not file_name.lower().endswith(".zip"):
        raise ValidationError(reason="仅支持上传 zip 压缩包")
    if file.size is not None and file.size > KB_ZIP_MAX_UPLOAD_SIZE:
        raise ValidationError(reason=f"文件大小超出限制（最大 {KB_ZIP_MAX_UPLOAD_SIZE // 1024 // 1024} MB）")
    content = await file.read()
    if file.size is None and len(content) > KB_ZIP_MAX_UPLOAD_SIZE:
        raise ValidationError(reason=f"文件大小超出限制（最大 {KB_ZIP_MAX_UPLOAD_SIZE // 1024 // 1024} MB）")

    result = ZipImportResult()
    with TemporaryDirectory(prefix="kb-zip-") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        try:
            entries = extract_zip_safe(content, tmp_dir)
        except (zipfile.BadZipFile, ValueError) as e:
            raise ValidationError(reason=str(e)) from e

        filtered = [entry for entry in entries if Path(entry.source_path).suffix.lower() in allowed_exts]
        result.skipped = len(entries) - len(filtered)
        for entry in filtered:
            success, reused_existing, error = await handle_entry(entry)
            if error is not None:
                result.failed += 1
                result.errors.append(f"{entry.source_path}: {error}")
            elif reused_existing:
                result.reused += 1
            elif success:
                result.imported += 1
    return result
