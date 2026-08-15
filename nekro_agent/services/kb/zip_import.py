"""知识库 Zip 批量导入：安全解压 + 按目录结构映射导入元数据 + 导入编排。

限制（上传大小 / 解压总大小 / 文件数）由集中配置 KB_ZIP_* 控制，可在不改代码的情况下调节；
配置在模块加载时读取，修改后需重启服务生效。

内存行为说明: 上传的 zip 会一次性读入内存（受 _MAX_UPLOAD_SIZE 约束），
解压落盘后逐文件经 Path.read_bytes() 读入内存导入（解压总量受 _MAX_EXTRACT_SIZE 约束）。
若未来放宽大小上限，需同步评估内存峰值或改为流式/分块读取。
"""

import io
import posixpath
import shutil
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
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


@dataclass
class ZipImportResult:
    """zip 批量导入统计结果"""

    imported: int = 0
    reused: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """整体是否成功：至少有一个条目导入/复用成功，或没有任何失败。"""
        return self.imported + self.reused > 0 or self.failed == 0


def to_zip_import_response(result: ZipImportResult) -> KBZipImportResponse:
    """将导入统计结果转换为 API 响应模型。"""
    return KBZipImportResponse(
        ok=result.ok,
        imported=result.imported,
        reused=result.reused,
        skipped=result.skipped,
        failed=result.failed,
        errors=result.errors,
    )


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
        if len(members) > _MAX_FILES:
            raise ValueError(f"zip 包文件数超出上限（最大 {_MAX_FILES} 个）")
        for member in members:
            total_size += member.file_size
            if total_size > _MAX_EXTRACT_SIZE:
                raise ValueError(
                    f"zip 包解压后总大小超出上限（最大 {_MAX_EXTRACT_SIZE // 1024 // 1024} MB）"
                )
        # 按条目名去重（后出现的覆盖先出现的，与解压落盘行为一致）
        entries_by_path: dict[str, ZipImportEntry] = {}
        for member in members:
            # 规范化条目路径：统一正斜杠、解析 ./ 与 ..、去除绝对路径前导，避免平台相关或畸形路径进入元数据
            rel_path = posixpath.normpath(member.filename.replace("\\", "/")).lstrip("/")
            if not rel_path:
                continue
            dest = (target_root / rel_path).resolve()
            if not dest.is_relative_to(target_root):
                raise ValueError(f"zip 包包含非法路径: {member.filename}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
            entries_by_path[rel_path] = _derive_entry(rel_path, dest)
    return list(entries_by_path.values())


CreateFromUploadFn = Callable[[ZipImportEntry, UploadFile], Awaitable[tuple[object, bool]]]
ScheduleRebuildFn = Callable[[object], Awaitable[None]]


def _friendly_entry_error(entry: ZipImportEntry, error: Exception) -> str:
    """将条目级异常清洗为用户可读消息；完整细节由调用方记录日志。"""
    if isinstance(error, FileExistsError):
        return "目标路径已存在"
    if isinstance(error, IntegrityError):
        return "目标路径或内容与现有条目冲突"
    if isinstance(error, ValueError):
        return str(error) or "文件内容无效"
    return "导入失败（详见服务端日志）"


async def import_zip_with_upload(
    file: UploadFile,
    allowed_exts: set[str],
    create_from_upload: CreateFromUploadFn,
    schedule_rebuild: ScheduleRebuildFn | None = None,
) -> ZipImportResult:
    """zip 上传导入编排：校验 → 安全解压 → 扩展名过滤 → 逐条导入并统计。

    create_from_upload 返回 (obj, reused_existing)：reused 时不触发重建索引。
    单条导入失败不中断整批，完整异常细节记录日志，客户端仅收到清洗后的消息。
    """
    file_name = file.filename or ""
    if not file_name.lower().endswith(".zip"):
        raise ValidationError(reason="仅支持上传 zip 压缩包")
    if file.size is not None and file.size > _MAX_UPLOAD_SIZE:
        raise ValidationError(reason=f"文件大小超出限制（最大 {_MAX_UPLOAD_SIZE // 1024 // 1024} MB）")
    content = await file.read()
    if file.size is None and len(content) > _MAX_UPLOAD_SIZE:
        raise ValidationError(reason=f"文件大小超出限制（最大 {_MAX_UPLOAD_SIZE // 1024 // 1024} MB）")

    result = ZipImportResult()
    allowed_exts_lower = {ext.lower() for ext in allowed_exts}
    with TemporaryDirectory(prefix="kb-zip-") as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        try:
            entries = extract_zip_safe(content, tmp_dir)
        except (zipfile.BadZipFile, ValueError) as e:
            raise ValidationError(reason=str(e)) from e

        filtered = [entry for entry in entries if Path(entry.source_path).suffix.lower() in allowed_exts_lower]
        result.skipped = len(entries) - len(filtered)
        for entry in filtered:
            try:
                upload_file = UploadFile(
                    filename=Path(entry.source_path).name,
                    file=io.BytesIO(entry.path.read_bytes()),
                )
                obj, reused_existing = await create_from_upload(entry, upload_file)
                if not reused_existing and schedule_rebuild is not None:
                    await schedule_rebuild(obj)
                if reused_existing:
                    result.reused += 1
                else:
                    result.imported += 1
            except Exception as e:
                logger.warning(f"zip 导入条目失败: {entry.source_path}, error: {e}", exc_info=True)
                result.failed += 1
                result.errors.append(f"{entry.source_path}: {_friendly_entry_error(entry, e)}")
    return result
