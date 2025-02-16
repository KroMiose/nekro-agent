"""扩展管理器

负责扩展文件的管理功能。
"""

from pathlib import Path
from typing import List

from nekro_agent.core.os_env import OsEnv

from .loader import BUILTIN_EXT_META_DATA, WORKDIR_EXT_META_DATA, ext_workdir
from .models import ExtMetaData


def get_all_ext_meta_data() -> List[ExtMetaData]:
    """获取所有扩展的元数据

    Returns:
        List[ExtMetaData]: 扩展元数据列表
    """
    return BUILTIN_EXT_META_DATA + WORKDIR_EXT_META_DATA


def get_ext_workdir_files() -> List[str]:
    """获取工作目录下的所有扩展文件

    Returns:
        List[str]: 扩展文件路径列表
    """
    if not ext_workdir.exists():
        return []

    # 获取所有 .py 文件
    py_files = list(ext_workdir.glob("**/*.py"))
    # 转换为相对路径
    return [str(f.relative_to(ext_workdir)) for f in py_files]


def delete_ext_file(file_path: str) -> None:
    """删除扩展文件

    Args:
        file_path (str): 文件路径

    Raises:
        ValueError: 文件路径不在工作目录内
        FileNotFoundError: 文件不存在
    """
    full_path = ext_workdir / file_path

    # 安全检查：确保文件在工作目录内
    if not full_path.is_relative_to(ext_workdir):
        raise ValueError("文件路径必须在工作目录内")

    if not full_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 删除文件
    full_path.unlink()


def read_ext_file(file_path: str) -> str:
    """读取扩展文件内容

    Args:
        file_path (str): 文件路径

    Returns:
        str: 文件内容

    Raises:
        ValueError: 文件路径不在工作目录内
        FileNotFoundError: 文件不存在
    """
    full_path = ext_workdir / file_path

    # 安全检查：确保文件在工作目录内
    if not full_path.is_relative_to(ext_workdir):
        raise ValueError("文件路径必须在工作目录内")

    if not full_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    return full_path.read_text(encoding="utf-8")


def save_ext_file(file_path: str, content: str) -> None:
    """保存扩展文件内容

    Args:
        file_path (str): 文件路径
        content (str): 文件内容

    Raises:
        ValueError: 文件路径不在工作目录内
    """
    full_path = ext_workdir / file_path

    # 安全检查：确保文件在工作目录内
    if not full_path.is_relative_to(ext_workdir):
        raise ValueError("文件路径必须在工作目录内")

    # 确保父目录存在
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # 保存文件
    full_path.write_text(content, encoding="utf-8") 