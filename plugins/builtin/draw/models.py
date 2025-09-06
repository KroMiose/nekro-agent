from typing import List, Optional

from pydantic import BaseModel, Field

from .plugin import config


class ImageReference(BaseModel):
    """图片参考信息"""

    image_path: str = Field(description="图片文件路径")
    description: str = Field(description="图片描述信息，用于指导AI理解图片内容和用途")
    weight: float = Field(default=1.0, description="图片参考权重，范围0.1-2.0，默认1.0")

    def __str__(self) -> str:
        return f"Image: {self.image_path} (Weight: {self.weight}) - {self.description}"


class MultiImageDrawRequest(BaseModel):
    """多图绘制请求"""

    reference_images: List[ImageReference] = Field(description="参考图片列表，最多支持5张")
    target_prompt: str = Field(description="目标图片生成提示词，描述期望生成的图片")
    size: str = Field(default="1024x1024", description="图片尺寸")
    guidance_scale: float = Field(default=7.5, description="引导强度")
    send_to_chat: str = Field(default="", description="是否发送到聊天")

    def validate_images(self) -> None:
        """验证图片数量"""
        if len(self.reference_images) > config.MAX_IMAGE_NUM:
            raise ValueError(f"最多支持{config.MAX_IMAGE_NUM}张参考图片")
        if len(self.reference_images) == 0:
            raise ValueError("至少需要1张参考图片")

    def construct_prompt(self) -> str:
        """构建综合提示词"""
        image_descriptions = []
        for i, img_ref in enumerate(self.reference_images, 1):
            weight_desc = f"(重要程度: {img_ref.weight})" if img_ref.weight != 1.0 else ""
            image_descriptions.append(f"参考图片{i}: {img_ref.description} {weight_desc}")

        return f"""基于以下参考图片生成新图片:

{chr(10).join(image_descriptions)}

目标描述: {self.target_prompt}

请综合分析所有参考图片的特征，并根据目标描述生成一张新的图片。注意保持参考图片的关键特征，同时融入目标描述的要求。"""
