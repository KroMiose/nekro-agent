import base64
import mimetypes
from pathlib import Path
from typing import Optional, Tuple

import aiofiles
import magic


async def get_file_info(file_path: str) -> Tuple[bytes, str, str]:
    """获取文件信息

    Args:
        file_path: 文件路径

    Returns:
        Tuple[bytes, str, str]: 文件字节数据、MIME类型、文件名
    """
    path = Path(file_path)

    # 检查文件是否存在
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 读取文件内容
    async with aiofiles.open(path, "rb") as f:
        file_bytes = await f.read()

    # 获取MIME类型
    mime_type = magic.from_buffer(file_bytes, mime=True)
    file_name = path.name

    return file_bytes, mime_type, file_name


async def get_file_url(file_path: str) -> str:
    """上传并获取文件 URL（使用data URL格式）

    Args:
        file_path: 文件路径

    Returns:
        str: data URL格式的文件链接
    """
    file_bytes, mime_type, _ = await get_file_info(file_path)

    # 转换为base64
    base64_encoded = base64.b64encode(file_bytes).decode("utf-8")

    # 生成data URL
    return f"data:{mime_type};base64,{base64_encoded}"


async def get_file_base64(file_path: str) -> Tuple[str, str, str]:
    """获取文件的base64编码

    Args:
        file_path: 文件路径

    Returns:
        Tuple[str, str, str]: base64编码url、MIME类型、文件名
    """
    file_bytes, mime_type, file_name = await get_file_info(file_path)

    # 转换为base64
    base64_encoded = base64.b64encode(file_bytes).decode("utf-8")

    return f"data:{mime_type};base64,{base64_encoded}", mime_type, file_name


def parse_data_url(data_url: str) -> Tuple[str, str]:
    """解析data URL

    Args:
        data_url: data URL字符串

    Returns:
        Tuple[str, str]: MIME类型, base64编码数据
    """
    if not data_url.startswith("data:"):
        raise ValueError("无效的data URL格式")

    # 解析格式：data:mimetype;base64,DATA
    metadata, base64_data = data_url.split(",", 1)
    mime_type = metadata.split(";")[0].split(":")[1]

    return mime_type, base64_data


def get_extension_from_mime(mime_type: str) -> str:
    """从MIME类型获取文件扩展名

    Args:
        mime_type: MIME类型

    Returns:
        str: 文件扩展名（包含点号）
    """
    ext = mimetypes.guess_extension(mime_type)
    return ext or ""


async def bytes_to_file(
    file_bytes: bytes,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    save_dir: Optional[Path] = None,
) -> Tuple[str, str]:
    """将字节数据保存为文件

    Args:
        file_bytes: 文件字节数据
        file_name: 文件名（可选）
        mime_type: MIME类型（可选）
        save_dir: 保存目录（可选）

    Returns:
        Tuple[str, str]: 文件路径, 文件名
    """
    import hashlib

    from nekro_agent.core.os_env import USER_UPLOAD_DIR

    # 如果未提供mime_type，尝试检测
    if not mime_type:
        mime_type = magic.from_buffer(file_bytes, mime=True)

    # 处理文件名
    if not file_name:
        extension = get_extension_from_mime(mime_type)
        file_name = f"{hashlib.md5(file_bytes).hexdigest()}{extension}"

    # 确定保存目录
    if not save_dir:
        save_dir = Path(USER_UPLOAD_DIR)

    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / file_name

    # 写入文件
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)

    file_path.chmod(0o755)
    return str(file_path), file_name


async def base64_to_file(
    base64_data: str,
    file_name: Optional[str] = None,
    mime_type: Optional[str] = None,
    save_dir: Optional[Path] = None,
) -> Tuple[str, str]:
    """将base64数据保存为文件

    Args:
        base64_data: base64编码的数据
        file_name: 文件名（可选）
        mime_type: MIME类型（可选）
        save_dir: 保存目录（可选）

    Returns:
        Tuple[str, str]: 文件路径, 文件名
    """
    # 解码base64
    file_bytes = base64.b64decode(base64_data)

    return await bytes_to_file(file_bytes, file_name, mime_type, save_dir)
