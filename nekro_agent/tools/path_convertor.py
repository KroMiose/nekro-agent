from enum import Enum
from pathlib import Path
from typing import Optional

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import SANDBOX_SHARED_HOST_DIR, USER_UPLOAD_DIR


class PathLocation(Enum):
    """路径位置枚举"""

    UPLOADS = "uploads"
    SHARED = "shared"


def detect_path_location(path: Path) -> Optional[PathLocation]:
    """
    检测路径所属位置

    Args:
        path (Path): 需要检测的路径

    Returns:
        Optional[PathLocation]: 路径位置，如果不匹配则返回 None
    """
    try:
        path_parts = path.parts

        for part in path_parts:
            if part == PathLocation.UPLOADS.value:
                return PathLocation.UPLOADS
            if part == PathLocation.SHARED.value:
                return PathLocation.SHARED
        else:
            return None
    except Exception as e:
        logger.error(f"Path location detection error: {e}")
        return None


def convert_to_host_path(
    sandbox_path: Path,
    chat_key: str,
    container_key: Optional[str] = None,
    uploads_dir: Path = Path(USER_UPLOAD_DIR),
    shared_dir: Path = Path(SANDBOX_SHARED_HOST_DIR),
) -> Path:
    """
    将沙盒内的路径转换为宿主机路径

    Args:
        sandbox_path (Path): 沙盒内的路径
        chat_key (str): 聊天标识
        container_key (Optional[str]): 容器标识，shared 路径必需
        uploads_dir (Path): 上传文件根目录，默认使用 USER_UPLOAD_DIR
        shared_dir (Path): 共享文件根目录，默认使用 SANDBOX_SHARED_HOST_DIR

    Returns:
        Optional[Path]: 转换后的宿主机路径，如果转换失败返回 None

    Raises:
        ValueError: 当 shared 路径没有提供 container_key 时

    Examples:
        >>> # 转换绝对路径
        >>> convert_to_host_path(Path("/app/uploads/test.txt"), "group_123456")
        Path("/data/uploads/group_123456/test.txt")

        >>> # 转换相对路径
        >>> convert_to_host_path(Path("./uploads/test.txt"), "group_123456")
        Path("/data/uploads/group_123456/test.txt")

        >>> # 转换 shared 路径
        >>> convert_to_host_path(
        ...     Path("/app/shared/test.txt"),
        ...     "group_123456",
        ...     container_key="container_789"
        ... )
        Path("/data/shared/container_789/test.txt")
    """

    def _validate_shared_path(key: Optional[str]) -> None:
        if not key:
            raise ValueError("Container key is required for shared paths")

    # 设置默认工作目录为 /app
    base_path = Path("/app")
    
    # 如果是相对路径，将其转换为绝对路径
    if not sandbox_path.is_absolute():
        sandbox_path = base_path / sandbox_path

    # 标准化路径
    clean_path = Path(*sandbox_path.parts)

    # 检测路径位置
    location = detect_path_location(clean_path)
    if not location:
        logger.warning(f"Unable to detect path location for: {sandbox_path}")
        raise ValueError(f"Unable to detect path location for: {sandbox_path}")

    # 获取相对路径部分
    try:
        relative_path = Path(*clean_path.parts[clean_path.parts.index(location.value) + 1 :])
        logger.debug(f"Converting path: {sandbox_path}, detected location: {location}, relative path: {relative_path}")
    except ValueError as e:
        logger.warning(f"Unable to extract relative path from: {sandbox_path}")
        raise ValueError(f"Unable to extract relative path from: {sandbox_path}") from e

    # 根据位置类型构建宿主机路径
    if location == PathLocation.UPLOADS:
        return uploads_dir / chat_key / relative_path
    if location == PathLocation.SHARED:
        _validate_shared_path(container_key)
        return shared_dir / str(container_key) / relative_path
    raise ValueError(f"Invalid path location: {location}")


def is_url_path(path: str) -> bool:
    """
    检查路径是否为URL

    Args:
        path (str): 要检查的路径

    Returns:
        bool: 是否为URL
    """
    return path.startswith(("http://", "https://"))


def convert_to_container_path(path: Path) -> Path:
    """将路径转换为容器内路径

    Args:
        path (Path): 宿主机路径

    Returns:
        Path: 容器内路径
    """
    return Path("/app/uploads") / path.name


def convert_filename_to_container_path(filename: str | Path) -> Path:
    """将文件名转换为容器内路径

    Args:
        filename (Union[str, Path]): 文件名

    Returns:
        Path: 容器内路径
    """
    return Path("/app/uploads") / Path(filename).name


def convert_filename_to_access_path(filename: str | Path, chat_key: str) -> Path:
    """将文件名转换为访问路径

    Args:
        filename (Union[str, Path]): 文件名
        chat_key (str): 聊天会话键名

    Returns:
        Path: 访问路径
    """
    return Path(USER_UPLOAD_DIR) / chat_key / Path(filename).name


def get_sandbox_path(filename: str | Path) -> Path:
    """获取文件的沙盒路径

    Args:
        filename (Union[str, Path]): 文件名

    Returns:
        Path: 沙盒内路径
    """
    return Path("/app/uploads") / Path(filename).name
