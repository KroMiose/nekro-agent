"""
# AI 绘画 (Draw)

赋予 AI 使用各种模型进行绘画创作的能力，支持文生图和图生图。

## 主要功能

- **文生图**: 根据用户或 AI 提供的自然语言描述（Prompt），生成一张全新的图片。
- **图生图 (图片参考)**: 在生成图片时，可以提供一张参考图，让 AI 模仿其风格或保留其元素。
- **多模型支持**: 可以接入任何兼容 OpenAI 格式的图像生成模型，并通过配置进行切换。

## 使用方法

- **与 AI 对话**: 直接对 AI 说 "画一只在晒太阳的橘猫"，AI 就会调用此插件来完成绘画。
- **修改图片**: 发送一张图片并告诉 AI 如何修改，例如"把背景换成樱花公园"，AI 会使用图生图功能来处理。

## 配置说明

- **绘图模型组**: 这是最重要的配置，您需要在这里选择一个已配置好的、用于绘画的模型组。
- **模型调用格式**:
  - `图像生成`: 使用标准的 `/images/generations` API 接口。
  - `聊天模式`: 使用 `/chat/completions` 接口，通过多模态消息进行绘图。
  - `自动选择`: 插件会自动尝试并使用上次成功的模式，推荐在不确定模型支持哪种格式时使用。
- **超时时间**: 由于绘图是耗时操作，可以设置一个较长的超时时间防止中断。

## 配置推荐预设参考

> 如果你的配置无法正常工作，请根据选择的模型参考以下配置进行调整

- **gemini-2.0-flash-exp-image-generation**: 使用 Gemini 模型进行绘图，支持文生图和图生图，效果较好
  - `是否使用系统角色`: 禁用 (**谷歌模型不支持系统角色**)
  - `绘图模型调用格式`: 聊天模式
  - `聊天模式使用流式 API`: 启用
- **sora_image**: 使用 Sora 模型进行绘图，支持文生图和图生图，效果非常好，支持精细化绘图指令，但速度较慢且价格较贵
  - `绘图模型调用格式`: 聊天模式
  - `绘图超时时间`: 300
- **Kolors**: 国产绘图模型，价格便宜，画风单一，效果一般，但速度较快
  - `绘图模型调用格式`: 图像生成
  - `模型推理步数`: 20
"""

import base64
import random
import re
from pathlib import Path
from typing import Literal, Optional

import aiofiles
import magic
from httpx import AsyncClient, Timeout
from pydantic import Field

from nekro_agent.api import core
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import logger
from nekro_agent.core.config import config as global_config
from nekro_agent.services.agent.creator import ContentSegment, OpenAIChatMessage
from nekro_agent.services.agent.openai import gen_openai_chat_response
from nekro_agent.tools.common_util import limited_text_output
from nekro_agent.tools.path_convertor import convert_to_host_path

plugin = NekroPlugin(
    name="绘画插件",
    module_name="draw",
    description="学会画画！",
    version="0.1.1",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_config()
class DrawConfig(ConfigBase):
    """绘画配置"""

    USE_DRAW_MODEL_GROUP: str = Field(
        default="default-draw-chat",
        title="绘图模型组",
        json_schema_extra={"ref_model_groups": True, "required": True, "model_type": "draw"},
        description="主要使用的绘图模型组，可在 `系统配置` -> `模型组` 选项卡配置",
    )
    MODEL_MODE: Literal["自动选择", "图像生成", "聊天模式"] = Field(default="自动选择", title="绘图模型调用格式")
    NUM_INFERENCE_STEPS: int = Field(default=20, title="模型推理步数")
    USE_SYSTEM_ROLE: bool = Field(
        default=False,
        title="是否使用系统角色",
        description="只对聊天模式下的模型调用有效，如果启用时会把部分绘图提示词添加到系统角色中，如果模型不支持系统消息请关闭该选项",
    )
    STREAM_MODE: bool = Field(
        default=False,
        title="聊天模式使用流式 API",
        description="由于模型生成时间问题，部分模型需要在聊天模式下启用流式 API 才能正常工作",
    )
    TIMEOUT: int = Field(default=300, title="绘图超时时间", description="单位: 秒")


# 获取配置
config: DrawConfig = plugin.get_config(DrawConfig)

# 保存上次成功的模式
last_successful_mode: Optional[str] = None


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, name="绘图", description="支持文生图和图生图")
async def draw(
    _ctx: AgentCtx,
    prompt: str,
    size: str = "1024x1024",
    guidance_scale: float = 7.5,
    refer_image: str = "",
) -> str:
    """Generate or modify images

    Args:
        prompt (str): Natural language description of the image you want to create. (Only supports English)
            Suggested elements to include:
            - Type of drawing (e.g., character setting, landscape, comics, etc.)
            - What to draw details (characters, animals, objects, etc.)
            - What they are doing or their state
            - The scene or environment
            - Overall mood or atmosphere
            - Very detailed description or story (optional, recommend for comics)
            - Art style (e.g., illustration, watercolor... any style you want)

        size (str): Image dimensions (e.g., "1024x1024" square, "512x768" portrait, "768x512" landscape)
        guidance_scale (float): Guidance scale for the image generation, lower is more random, higher is more like the prompt (default: 7.5, from 0 to 20)
        refer_image (str): Optional source image path for image reference (useful for image style transfer or keep the elements of the original image)

    Returns:
        str: Generated image path

    Examples:
        # Generate new image but **NOT** send to chat
        draw("a illustration style cute orange cat napping on a sunny windowsill, watercolor painting style", "1024x1024")

        # Modify existing image
        send_msg_file(chat_key, draw("change the background to a cherry blossom park, keep the anime style", "1024x1024", "shared/refer_image.jpg")) # if adapter supports file, you can use this method to send the image to the chat. Otherwise, find another method to use the image.
    """
    global last_successful_mode
    # logger.info(f"绘图提示: {prompt}")
    # logger.info(f"绘图尺寸: {size}")
    logger.info(f"使用绘图模型组: {config.USE_DRAW_MODEL_GROUP} 绘制: {prompt}")
    if refer_image:
        async with aiofiles.open(
            convert_to_host_path(Path(refer_image), chat_key=_ctx.chat_key, container_key=_ctx.container_key),
            mode="rb",
        ) as f:
            image_data = await f.read()
            mime_type = magic.from_buffer(image_data, mime=True)
            image_data = base64.b64encode(image_data).decode("utf-8")
        source_image_data = f"data:{mime_type};base64,{image_data}"
    else:
        source_image_data = "data:image/webp;base64, XXX"
    if config.USE_DRAW_MODEL_GROUP not in global_config.MODEL_GROUPS:
        raise Exception(f"绘图模型组 `{config.USE_DRAW_MODEL_GROUP}` 未配置")
    model_group = global_config.MODEL_GROUPS[config.USE_DRAW_MODEL_GROUP]

    # 处理自动选择模式
    if config.MODEL_MODE == "自动选择":
        # 优先使用上次成功的模式
        modes_to_try = []
        if last_successful_mode:
            modes_to_try.append(last_successful_mode)
            logger.debug(f"优先使用上次成功的模式: {last_successful_mode}")

        # 添加未尝试过的模式
        for mode in ["聊天模式", "图像生成"]:
            if mode not in modes_to_try:
                modes_to_try.append(mode)

        # 依次尝试各种模式
        last_error = None
        for mode in modes_to_try:
            logger.debug(f"尝试使用模式: {mode}")
            try:
                if mode == "图像生成":
                    ret_file_url = await _generate_image(
                        model_group,
                        prompt,
                        size,
                        config.NUM_INFERENCE_STEPS,
                        guidance_scale,
                        source_image_data,
                    )
                else:  # 聊天模式
                    ret_file_url = await _chat_image(model_group, prompt, size, refer_image, source_image_data)

            except Exception as e:
                last_error = e
                logger.error(f"模式 {mode} 失败: {e!s}")
                # 清除当前模式记录
                if last_successful_mode == mode:
                    last_successful_mode = None
            else:
                # 记录成功的模式
                last_successful_mode = mode
                return await _ctx.fs.mixed_forward_file(ret_file_url)

        # 如果所有模式都失败，抛出最后一个错误
        if last_error:
            raise last_error
        raise Exception("所有绘图模式都失败")  # 确保有返回值或异常

    if config.MODEL_MODE == "图像生成":
        return await _ctx.fs.mixed_forward_file(
            await _generate_image(model_group, prompt, size, config.NUM_INFERENCE_STEPS, guidance_scale, source_image_data),
        )
    # 聊天模式
    return await _ctx.fs.mixed_forward_file(
        await _chat_image(model_group, prompt, size, refer_image, source_image_data),
    )


async def _generate_image(model_group, prompt, size, num_inference_steps, guidance_scale, source_image_data) -> str:
    """使用图像生成模式绘图"""
    async with AsyncClient() as client:
        response = await client.post(
            f"{model_group.BASE_URL}/images/generations",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {model_group.API_KEY}",
            },
            json={
                "model": model_group.CHAT_MODEL,
                "prompt": prompt,
                "image_size": size,
                "batch_size": 1,
                "seed": random.randint(0, 9999999999),
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "image": source_image_data,
            },
            timeout=Timeout(read=config.TIMEOUT, write=config.TIMEOUT, connect=10, pool=10),
        )
    response.raise_for_status()
    data = response.json()
    ret_url = data["data"][0]["url"]
    if ret_url:
        return ret_url
    logger.error(f"绘图响应中未找到图片信息: {data}")
    raise Exception(
        "No image content found in image generation AI response. You can adjust the prompt and try again. Make sure the prompt is clear and detailed.",
    )


async def _chat_image(model_group, prompt, size, refer_image, source_image_data) -> str:
    """使用聊天模式绘图"""
    system_content = "You are a professional painter. Use your high-quality drawing skills to draw a picture based on the user's description. Just provide the image and do not ask for more information."

    msg = OpenAIChatMessage.create_empty("user")
    if refer_image:
        msg = msg.add(ContentSegment.image_content(source_image_data))
        if not config.USE_SYSTEM_ROLE:
            msg = msg.add(
                ContentSegment.text_content(
                    f"{system_content}\n\nCarefully analyze the above image and make a picture based on the following description: {prompt} (size: {size})",
                ),
            )
        else:
            msg = msg.add(
                ContentSegment.text_content(
                    f"Carefully analyze the above image and make a picture based on the following description: {prompt} (size: {size})",
                ),
            )
    else:
        if not config.USE_SYSTEM_ROLE:
            msg = msg.add(
                ContentSegment.text_content(
                    f"{system_content}\n\nMake a picture based on the following description: {prompt} (size: {size})",
                ),
            )
        else:
            msg = msg.add(
                ContentSegment.text_content(f"Make a picture based on the following description: {prompt} (size: {size})"),
            )

    messages = []
    if config.USE_SYSTEM_ROLE:
        messages.append(
            {
                "role": "system",
                "content": system_content,
            },
        )
    messages.append(msg.to_dict())

    response = await gen_openai_chat_response(
        model=model_group.CHAT_MODEL,
        messages=messages,
        base_url=model_group.BASE_URL,
        api_key=model_group.API_KEY,
        stream_mode=config.STREAM_MODE,
        max_wait_time=config.TIMEOUT,
    )
    content = response.response_content

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
    logger.error(f"绘图响应中未找到图片信息: {limited_text_output(str(content))}")
    raise Exception(
        "No image content found in image generation AI response. You can adjust the prompt and try again. Make sure the prompt is clear and detailed.",
    )


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
