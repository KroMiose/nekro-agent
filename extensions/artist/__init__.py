import base64
from typing import Tuple

import httpx

from nekro_agent.core import logger
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.chat import chat_service
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.tools.collector import MethodType, agent_collector
from nekro_agent.tools.common_util import (
    convert_file_name_to_container_path,
    download_file_from_bytes,
)

from .designer import gen_sd_prompt_by_scene
from .stable_diffusion import text2img

SD_BASE_API = "http://127.0.0.1:7860"
DEFAULT_POSITIVE_PROMPTS = "best quality, masterpiece, anime illustration,"
DEFAULT_NEGATIVE_PROMPTS = (
    "ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured,"
    "deformed, body out of frame, bad anatomy, watermark, signature, cut off, low contrast, underexposed, overexposed,"
    "bad art, beginner, amateur, distorted face"
)

# 创建全局 httpx.AsyncClient 实例
client = httpx.AsyncClient()

__meta__ = ExtMetaData(
    name="stable_diffusion",
    description="Nekro-Agent 插件，用于调用 Stable Diffusion 生成图片",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@agent_collector.mount_method(MethodType.TOOL)
async def draw_image(scene_description: str, img_size: Tuple, _ctx: AgentCtx) -> str:
    """开始通过给定的自然语言场景描述提示词绘制图像 返回绘画结果保存路径(!!不会自动发送到聊天中!!)

    注意: 当你需要进行 "画画" / "绘画" 行为时，请**立即调用此方法**，禁止用 "正在画" 等行为表述来拖延对话!

    Args:
        scene_description (str): 图像场景信息的详细描述
        img_size (Tuple): 图像宽高 (width, height) 范围: (512 <= width, height <= 1024)

    Returns:
        str: 图像保存路径
    """
    logger.info(f"正在绘制图像: {scene_description}")
    prompts, negative_prompts = await gen_sd_prompt_by_scene(scene_description)
    bytes_data: bytes = await text2img(prompts, negative_prompts, img_size[0], img_size[1])
    file_path, file_name = await download_file_from_bytes(bytes_data, use_suffix=".png", from_chat_key=_ctx.from_chat_key)
    return str(convert_file_name_to_container_path(file_name))
