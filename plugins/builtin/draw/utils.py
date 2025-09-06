import re

from nekro_agent.core import logger
from nekro_agent.tools.common_util import limited_text_output


def extract_image_from_content(content: str) -> str:
    """从 content 中提取图片 URL 或 base64 数据

    Args:
        content: 响应内容

    Returns:
        str: 图片 URL 或 base64 数据

    Raises:
        Exception: 当无法找到图片内容时
    """
    # 尝试 markdown 语法匹配，例如 ![alt](url)
    m = re.search(r"!\[[^\]]*\]\(([^)]+)\)", content)
    if m:
        return m.group(1)

    # 尝试 HTML <img> 标签匹配，例如 <img src="url" />
    m = re.search(r'<img\s+src=["\']([^"\']+)["\']', content)
    if m:
        return m.group(1)

    # 尝试裸 URL 匹配，例如 http://... 或 https://...
    m = re.search(r"(https?://\S+)", content)
    if m:
        return m.group(1)

    # 尝试 base64 数据匹配
    m = re.search(r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)", content)
    if m:
        return f"data:image/png;base64,{m.group(1)}"

    logger.error(f"从内容中未找到图片信息: {limited_text_output(str(content))}")
    raise Exception("未找到图片内容，请检查模型响应或调整提示词")
