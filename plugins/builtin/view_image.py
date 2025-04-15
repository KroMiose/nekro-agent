import asyncio
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Dict, List

from pydantic import Field

from nekro_agent.api.core import logger
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.config import ModelConfigGroup
from nekro_agent.core.config import config as core_config
from nekro_agent.services.agent.creator import ContentSegment, OpenAIChatMessage
from nekro_agent.services.agent.openai import gen_openai_chat_response
from nekro_agent.services.message.message_service import message_service
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.services.plugin.manager import (
    disable_plugin,
    enable_plugin,
)
from nekro_agent.tools.path_convertor import convert_to_host_path

plugin = NekroPlugin(
    name="图片查看插件",
    module_name="view_image",
    description="提供图片查看功能",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)

# 缓存文件路径和锁
CACHE_FILE = plugin.get_plugin_path() / "image_view_cache.json"
cache_lock = asyncio.Lock()


async def load_cache() -> dict:
    """加载缓存文件"""
    async with cache_lock:
        if not CACHE_FILE.exists():
            return {}
        try:
            with Path.open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"加载图片描述缓存失败: {e}")
            return {}


async def save_cache(cache_data: dict):
    """保存缓存文件"""
    async with cache_lock:
        try:
            # 确保目录存在
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with Path.open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=4)
        except OSError as e:
            logger.error(f"保存图片描述缓存失败: {e}")


def parse_image_descriptions(text: str) -> Dict[str, str]:
    """解析模型返回的图片描述文本"""
    descriptions = {}
    # 正则表达式匹配 [Image X]: path/url 和 [Description X]: description
    pattern = re.compile(r"\[Image \d+\]: (.*?)\n\[Description \d+\]: (.*?)(?=\n\[Image|\Z)", re.DOTALL)
    matches = pattern.findall(text)
    for img_ref, desc in matches:
        descriptions[img_ref.strip()] = desc.strip()
    if not descriptions and text.strip(): # 如果正则没匹配到，但文本不为空，可能格式不对或只有描述
        logger.warning(f"无法按预期格式解析图片描述: {text}")

    return descriptions

def format_descriptions(original_images: List[str], descriptions: Dict[str, str]) -> str:
    """将解析后的描述格式化为字符串，保持原始顺序"""
    if not descriptions:
        return "未能获取到有效的图片描述。"

    formatted_lines = []
    i = 1
    for img_path in original_images:
        desc = descriptions.get(img_path, "Error: Description not found for this image.") # 获取描述，不存在则提示
        formatted_lines.append(f"[Image {i}]: {img_path}")
        formatted_lines.append(f"[Description {i}]: {desc}")
        i += 1
    return "\n".join(formatted_lines)


@plugin.mount_config()
class ViewImageConfig(ConfigBase):
    """基础配置"""

    VISION_MODEL: str = Field(
        default="default",
        title="用于查看图片的模型,如果主模型自带视觉请勿开启本插件",
        description="用于查看图片并描述内容,以文本形式返回给主模型",
        json_schema_extra={"ref_model_groups": True, "required": True},
    )

def get_view_image_config() -> ViewImageConfig:
    """获取最新的图片观察工具配置"""
    return plugin.get_config(ViewImageConfig)

#根据模型名获取模型组配置项
def get_model_group_info(model_name: str) -> ModelConfigGroup:
    try:
        return core_config.MODEL_GROUPS[model_name]
    except KeyError as e:
        raise ValueError(f"模型组 '{model_name}' 不存在，请确认配置正确") from e

@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "图片观察工具")
async def view_image(_ctx: AgentCtx, images: List[str]):
    """利用视觉观察图片

    Attention: Do not repeatedly observe the contents of the visual image given in the context!

    Args:
        images (List[str]): 图片共享路径或在线url列表
    """

    logger.debug(f"图片观察工具: {images}")

    # --- 缓存逻辑调整：基于单个图片路径 --- 
    cache = await load_cache() # 加载现有缓存 {image_path: description}
    final_descriptions: Dict[str, str] = {}
    images_to_describe: List[str] = []

    for img_path in images:
        if img_path in cache:
            logger.info(f"命中图片描述缓存: {img_path}")
            final_descriptions[img_path] = cache[img_path]
        else:
            images_to_describe.append(img_path)

    # 如果所有图片都在缓存中，直接格式化并返回
    if not images_to_describe:
        logger.info("所有请求的图片描述均已在缓存中。")
        return f"The visual description of the images is as follows:\n{format_descriptions(images, final_descriptions)}"
    
    logger.info(f"需要向模型请求描述的图片: {images_to_describe}")
    # --- 缓存检查结束 ---

    # 获取插件配置
    cfg: ViewImageConfig = get_view_image_config()
    vision_model_name = cfg.VISION_MODEL

    if not vision_model_name:
        raise ValueError("未配置有效的视觉模型 (VISION_MODEL)，无法使用图片观察工具。")
    
    vision_model_group = get_model_group_info(vision_model_name)

    if vision_model_group.MODEL_TYPE != "chat":
        raise ValueError("请选择正确的模型组")

    if not vision_model_group.ENABLE_VISION:
        raise ValueError("当前模型组不支持视觉功能")

    # 构造发送给视觉模型的消息
    vision_prompt = """
    Describe the content shown in this images in relatively detailed language.
    use format like this:
    [Image 1]: image_url or path
    [Description 1]: description
    [Image 2]: image_url or path
    [Description 2]: description
    ...
    don't add any other text, only the format above.
    """
    vision_msg = OpenAIChatMessage.from_text("system", vision_prompt)

    # 只为需要描述的图片构建消息
    for i, image_path in enumerate(images_to_describe):
        # 判断是否为URL（简单判断是否以http开头）
        if image_path.startswith(("http://", "https://")):
            # 使用URL方式
            vision_msg.batch_add(
                [
                    ContentSegment.text_content(f"Image {i+1}: {image_path}"),
                    ContentSegment.image_content(image_path),
                ],
            )
        else:
            # 使用文件路径方式
            path = convert_to_host_path(Path(image_path), chat_key=_ctx.from_chat_key)
            # 路径检查应该在添加到 images_to_describe 之前，或者这里再次检查并处理错误
            if not path or not path.exists():
                raise ValueError(f"图片路径不存在: {image_path}")
            vision_msg.batch_add(
                [
                    ContentSegment.text_content(f"Image {i+1}: {image_path}"),
                    ContentSegment.image_content_from_path(path),
                ],
            )

    # 调用 OpenAI 服务获取图片描述
    try:
        description_response = await gen_openai_chat_response(
            model=vision_model_group.CHAT_MODEL,
            messages=[vision_msg.to_dict()],
            base_url=vision_model_group.BASE_URL,
            api_key=vision_model_group.API_KEY,
        )
        # 响应对象现在是 OpenAIResponse
        raw_description = description_response.response_content

        if not raw_description:
            # 如果描述为空，缓存空字典
            parsed_descriptions = {}
        else:
            # 解析描述
            parsed_descriptions = parse_image_descriptions(raw_description)
            if not parsed_descriptions:
                logger.warning(f"解析后的描述为空，原始描述: {raw_description}")
                # 这里可以决定如何处理，例如返回原始描述或特定错误信息
                # 为了缓存，我们还是存空字典，但函数返回时带上原始信息或错误提示
                # 或者直接返回原始描述避免完全丢失信息
                # return f"Failed to parse descriptions. Raw response:\n{raw_description}"


    except Exception as e: # 网络或API调用错误
        logger.error(f"调用视觉模型 ({vision_model_group.CHAT_MODEL}) 时出错: {e}")
        # 即使模型调用失败，也可能部分图片已在缓存中，决定如何返回
        # 方案1: 抛出异常，中断流程
        raise RuntimeError(f"调用视觉模型失败: {e}") from e
        # 方案2: 返回已缓存的部分，并附带错误信息（需要调整后续逻辑）
        # error_message = f"\n\nError during vision model call for remaining images: {e}"
        # return f"The visual description of the images is as follows:\n{format_descriptions(images, final_descriptions)}{error_message}"

    # --- 缓存逻辑调整：更新单个图片描述 --- 
    # 将新解析的描述更新到主缓存对象中
    # parsed_descriptions 的 key 是图片路径/URL
    cache.update(parsed_descriptions)
    await save_cache(cache)
    logger.info(f"已更新并缓存图片描述: {list(parsed_descriptions.keys())}")
    # --- 缓存更新结束 ---

    # 合并缓存的和新获取的描述
    final_descriptions.update(parsed_descriptions)

    # 格式化解析后的描述或返回原始描述（如果解析失败）
    # 判断逻辑需要基于 final_descriptions 和原始请求的 images
    # if not parsed_descriptions and raw_description: # 这个判断不再准确
    #      # 如果解析失败但有原始响应，可以选择返回原始响应
    #      logger.warning("图片描述解析失败，将返回原始响应内容。")
    #      return f"The visual description of the images is as follows (raw):\n{raw_description}"
    # elif not parsed_descriptions:
    #      # 解析失败且无原始响应（或原始响应为空）
    #      return "未能获取到有效的图片描述。"
    # else:
    #      # 正常返回格式化后的描述
    #     return f"The visual description of the images is as follows:\n{format_descriptions(parsed_descriptions)}"
    # 使用更新后的 format_descriptions 函数，传入原始请求的图片列表和包含所有可用描述的字典
    return f"The visual description of the images is as follows:\n{format_descriptions(images, final_descriptions)}"
