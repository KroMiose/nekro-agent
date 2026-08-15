"""知识库 Zip 批量导入：安全解压 + 按目录结构映射导入元数据。"""

import io
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from nekro_agent.core.logger import get_sub_logger

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


def extract_zip_safe(content: bytes, target_dir: Path) -> list[ZipImportEntry]:
    """安全解压 zip 内容到 target_dir，返回可导入文件条目列表。

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
        for member in members:
            rel_path = member.filename
            dest = (target_root / rel_path).resolve()
            if not dest.is_relative_to(target_root):
                raise ValueError(f"zip 包包含非法路径: {rel_path}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)

    entries: list[ZipImportEntry] = []
    for file_path in sorted(target_root.rglob("*")):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(target_root).as_posix()
        parts = rel.split("/")
        directory_path = "/".join(parts[:-1])
        entries.append(
            ZipImportEntry(
                path=file_path,
                source_path=rel,
                category=f"{directory_path}/" if directory_path else "",
            )
        )
    return entries
