import hashlib
import random
import re
from pathlib import Path
from typing import Tuple

import httpx
import toml
from PIL import Image

from nekro_agent.core.config import config
from nekro_agent.core.os_env import USER_UPLOAD_DIR


def get_app_version() -> str:
    """获取当前应用版本号

    Returns:
        str: 应用版本号
    """
    pyproject = toml.loads(Path("pyproject.toml").read_text())
    try:
        return pyproject["tool"]["poetry"]["version"]
    except KeyError:
        return "unknown"


async def download_file(
    url: str,
    file_path: str = "",
    file_name: str = "",
    use_suffix: str = "",
    retry_count: int = 3,
    from_chat_key: str = "",
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
                if from_chat_key:
                    save_path = Path(USER_UPLOAD_DIR) / from_chat_key / Path(file_name)
                else:
                    save_path = Path(USER_UPLOAD_DIR) / Path(file_name)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                file_path = str(save_path)
            Path(file_path).write_bytes(response.content)
            Path(file_path).chmod(0o755)
    except Exception:
        if retry_count > 0:
            return await download_file(url, file_path, file_name, use_suffix, retry_count=retry_count - 1)
        raise
    else:
        return file_path, file_name


async def download_file_from_bytes(
    bytes_data: bytes,
    file_path: str = "",
    file_name: str = "",
    use_suffix: str = "",
    from_chat_key: str = "",
) -> Tuple[str, str]:
    """下载文件

    Args:
        url (str): 下载链接
        file_path (str): 保存路径

    Returns:
        Tuple[str, str]: 文件路径, 文件名
    """

    if not file_path:
        file_name = file_name or f"{hashlib.md5(bytes_data).hexdigest()}{use_suffix}"
        if from_chat_key:
            save_path = Path(USER_UPLOAD_DIR) / from_chat_key / Path(file_name)
        else:
            save_path = Path(USER_UPLOAD_DIR) / Path(file_name)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        file_path = str(save_path)
    Path(file_path).write_bytes(bytes_data)
    Path(file_path).chmod(0o755)
    return file_path, file_name


async def download_file_from_base64(
    base64_str: str,
    file_path: str = "",
    file_name: str = "",
    use_suffix: str = "",
    from_chat_key: str = "",
) -> Tuple[str, str]:
    """下载文件(从base64字符串)

    Args:
        base64_str (str): base64字符串
        file_path (str): 保存路径

    Returns:
        Tuple[str, str]: 文件路径, 文件名
    """

    if not file_path:
        file_name = file_name or f"{hashlib.md5(base64_str.encode()).hexdigest()}{use_suffix}"
        if from_chat_key:
            save_path = Path(USER_UPLOAD_DIR) / from_chat_key / Path(file_name)
        else:
            save_path = Path(USER_UPLOAD_DIR) / Path(file_name)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        file_path = str(save_path)
    Path(file_path).write_bytes(base64_str.encode())
    Path(file_path).chmod(0o755)
    return file_path, file_name


async def move_to_upload_dir(
    file_path: str,
    file_name: str = "",
    use_suffix: str = "",
    from_chat_key: str = "",
) -> Tuple[str, str]:
    """复制文件到上传目录

    Args:
        file_path (str): 文件路径
        file_name (str): 文件名

    Returns:
        Tuple[str, str]: 文件路径, 文件名
    """
    if not file_name:
        file_name = f"{hashlib.md5(Path(file_path).read_bytes()).hexdigest()}{use_suffix}"
    if from_chat_key:
        save_path = Path(USER_UPLOAD_DIR) / from_chat_key / Path(file_name)
    else:
        save_path = Path(USER_UPLOAD_DIR) / Path(file_name)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    Path(save_path).write_bytes(Path(file_path).read_bytes())
    Path(save_path).chmod(0o755)
    return str(save_path), file_name


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


def convert_file_name_to_access_path(file_name: str, from_chat_key: str) -> Path:
    """将文件名转换为访问路径

    Args:
        file_name (str): 文件名
        from_chat_key (str): 聊天会话键名

    Returns:
        Path: 访问路径
    """

    return Path(USER_UPLOAD_DIR) / from_chat_key / Path(file_name)


def get_downloaded_prompt_file_path(file_name: str) -> Path:
    """获取已下载文件路径

    Args:
        file_name (str): 文件名

    Returns:
        Path: 文件路径
    """

    return "app/uploads" / Path(file_name)


def random_chat_check() -> bool:
    """随机聊天检测

    Returns:
        bool: 是否随机聊天
    """

    return random.random() < config.AI_CHAT_RANDOM_REPLY_PROBABILITY


def check_content_trigger(content: str) -> bool:
    """内容触发检测

    Args:
        content (str): 内容

    Returns:
        bool: 是否触发
    """

    for reg_text in config.AI_CHAT_TRIGGER_REGEX:
        reg = re.compile(reg_text)
        if reg.search(content):
            return True
    return False


def compress_image(image_path: Path, size_limit_kb: int) -> Path:
    """压缩图片到指定大小以下，仅通过降低分辨率实现

    Args:
        image_path: 原图片路径
        size_limit_kb: 目标大小（KB）

    Returns:
        压缩后的图片路径
    """
    compressed_suffix = "_compressed"
    # 检查是否已经有压缩版本
    compressed_path = image_path.parent / f"{image_path.stem}{compressed_suffix}{image_path.suffix}"
    if compressed_path.exists():
        return compressed_path

    # 打开图片
    img = Image.open(image_path)

    # 确保图片在 RGB 模式
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 初始缩放比例
    scale = 1.0
    output_path = compressed_path

    while True:
        # 计算新的尺寸
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 保存压缩后的图片（使用最高质量）
        resized_img.save(output_path, quality=100)

        # 检查文件大小
        if output_path.stat().st_size <= size_limit_kb * 1024 or scale < 0.1:
            break

        # 降低分辨率继续尝试
        scale *= 0.8

    return output_path
