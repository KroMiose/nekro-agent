import base64
import io
from typing import Optional

from PIL import Image

from nekro_agent.core.logger import logger


async def process_image_data_url(data_url: str, max_size: int = 500 * 1024) -> str:
    """处理图片数据URL，压缩至指定大小以下

    Args:
        data_url: 图片的data URL (data:image/xxx;base64,...)
        max_size: 最大允许大小，默认500KB

    Returns:
        str: 压缩后的data URL
    """
    try:
        # 分离MIME类型和Base64数据
        mime_type = data_url.split(";")[0].split(":")[1]
        base64_data = data_url.split(",")[1]

        # 解码Base64
        binary_data = base64.b64decode(base64_data)

        # 使用PIL打开图片
        img = Image.open(io.BytesIO(binary_data))

        # 压缩图片，保持尺寸不变
        output = io.BytesIO()

        # 如果是PNG等透明图片，保持透明通道
        if mime_type == "image/png" or img.mode == "RGBA":
            img.save(output, format="PNG", optimize=True)
        else:
            img.convert("RGB").save(output, format="JPEG", quality=85, optimize=True)

        # 检查大小，如果超过指定大小，继续压缩
        img_data = output.getvalue()
        if len(img_data) > max_size:
            # 计算需要的压缩比例
            compression_ratio = max_size / len(img_data)
            quality = int(85 * compression_ratio)
            quality = max(10, min(quality, 85))  # 确保不太低也不太高

            output = io.BytesIO()
            img.convert("RGB").save(output, format="JPEG", quality=quality, optimize=True)
            img_data = output.getvalue()

            # 如果还是太大，降低分辨率
            if len(img_data) > max_size:
                width, height = img.size
                ratio = (max_size / len(img_data)) ** 0.5
                new_size = (int(width * ratio), int(height * ratio))
                # 使用数字2代替BICUBIC常量 (2=BICUBIC in PIL)
                img = img.resize(new_size, 2)

                output = io.BytesIO()
                img.convert("RGB").save(output, format="JPEG", quality=quality, optimize=True)
                img_data = output.getvalue()

        # 转为Base64
        base64_encoded = base64.b64encode(img_data).decode("utf-8")

        # 添加数据URL前缀
        output_mime_type = "image/jpeg" if mime_type != "image/png" and img.mode != "RGBA" else "image/png"

    except Exception as e:
        logger.error(f"处理图片数据URL失败: {e}")
        # 如果处理失败，返回原数据URL
        return data_url
    else:
        return f"data:{output_mime_type};base64,{base64_encoded}"
