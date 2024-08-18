import hashlib
from pathlib import Path
from typing import Tuple

import httpx

from nekro_agent.core.os_env import USER_UPLOAD_DIR


async def download_file(
    url: str,
    file_path: str = "",
    file_name: str = "",
    use_suffix: str = "",
    retry_count: int = 3,
) -> Tuple[str, str]:
    """下载文件

    Args:
        url (str): 下载链接
        file_path (str): 保存路径

    Returns:
        Tuple[str, str]: 文件路径, 文件名
    """

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            if not file_path:
                file_name = file_name or f"{hashlib.md5(response.content).hexdigest()}{use_suffix}"
                save_path = Path(USER_UPLOAD_DIR) / Path(file_name)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                file_path = str(save_path)
            Path(file_path).write_bytes(response.content)
    except Exception:
        if retry_count > 0:
            return await download_file(url, file_path, file_name, use_suffix, retry_count=retry_count - 1)
        raise
    else:
        return file_path, file_name


def convert_path_to_container_path(path: str) -> Path:
    """将路径转换为容器内路径

    Args:
        path (str): 路径

    Returns:
        Path: 容器内路径
    """

    return Path("/app/uploads") / Path(path).name


def convert_file_name_to_container_path(file_name: str) -> Path:
    """将文件名转换为容器内路径

    Args:
        file_name (str): 文件名

    Returns:
        Path: 容器内路径
    """

    return Path("/app/uploads") / Path(file_name)


def get_downloaded_prompt_file_path(file_name: str) -> Path:
    """获取已下载文件路径

    Args:
        file_name (str): 文件名

    Returns:
        Path: 文件路径
    """

    return "app/uploads" / Path(file_name)
