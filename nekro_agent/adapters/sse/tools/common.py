import base64
from pathlib import Path

import aiofiles
import magic


async def get_file_url(file_path: str) -> str:
    """上传并获取文件 URL"""
    path = Path(file_path)

    # 检查文件是否存在
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 读取文件内容
    async with aiofiles.open(path, "rb") as f:
        file_bytes = await f.read()
        # 获取MIME类型
        mime_type = magic.from_buffer(file_bytes, mime=True)

    # 转换为base64
    base64_encoded = base64.b64encode(file_bytes).decode("utf-8")

    # 生成data URL
    return f"data:{mime_type};base64,{base64_encoded}"
