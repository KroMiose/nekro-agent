import base64
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

import aiofiles
import magic
from httpx import AsyncClient, Timeout

from nekro_agent.api.plugin import SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import logger
from nekro_agent.core.config import config as global_config
from nekro_agent.services.agent.creator import ContentSegment, OpenAIChatMessage
from nekro_agent.tools.path_convertor import convert_to_host_path

from .models import ImageReference, MultiImageDrawRequest
from .plugin import config, plugin
from .utils import extract_image_from_content

# 保存上次成功的模式
last_successful_mode: Optional[str] = None


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, name="绘图", description="支持文生图和图生图")
async def draw(
    _ctx: AgentCtx,
    prompt: str,
    size: str = "1024x1024",
    guidance_scale: float = 7.5,
    refer_image: str = "",
    send_to_chat: str = "",
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
        send_to_chat (str): if send_to_chat is not empty, the image will be sent to the chat_key after generation

    Returns:
        str: Generated image path

    Examples:
        # Generate new image but **NOT** send to chat
        draw("a illustration style cute orange cat napping on a sunny windowsill, watercolor painting style", "1024x1024")

        # Modify existing image and send to chat
        draw("change the background to a cherry blossom park, keep the anime style", "1024x1024", "shared/refer_image.jpg", send_to_chat=_ck) # if adapter supports file, you can use this method to send the image to the chat. Otherwise, find another method to use the image.
    """
    # 生成图片
    result_file_url = await generate_image(
        model_group_name=config.USE_DRAW_MODEL_GROUP,
        prompt=prompt,
        size=size,
        guidance_scale=guidance_scale,
        refer_image=refer_image,
        chat_key=_ctx.chat_key,
        container_key=_ctx.container_key or "",
    )

    # 转换为沙盒文件
    result_sandbox_file = await _ctx.fs.mixed_forward_file(result_file_url)

    # 如果需要发送到聊天
    if send_to_chat:
        await _ctx.ms.send_image(send_to_chat, result_sandbox_file, ctx=_ctx)

    return result_sandbox_file


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, name="多图绘制", description="使用多张参考图片生成新图片")
async def draw_with_multiple_images(
    _ctx: AgentCtx,
    reference_images: List[Dict[str, Any]],
    target_prompt: str,
    size: str = "1024x1024", 
    guidance_scale: float = 7.5,
    send_to_chat: str = "",
) -> str:
    """使用多张参考图片生成新图片
    
    Args:
        reference_images (List[Dict[str, Any]]): 参考图片列表，每个元素包含：
            - image_path (str): 图片文件路径
            - description (str): 图片描述信息，用于指导AI理解图片内容和用途
            - weight (float, 可选): 图片参考权重，范围0.1-2.0，默认1.0
            最多支持5张图片
        target_prompt (str): 目标图片生成提示词，描述期望生成的图片内容和风格
        size (str): 图片尺寸，如 "1024x1024", "512x768", "768x512"
        guidance_scale (float): 引导强度，范围0-20，默认7.5，数值越高越贴近提示词
        send_to_chat (str): 如果不为空，生成的图片将发送到指定聊天
        
    Returns:
        str: 生成的图片路径
        
    Examples:
        # 使用两张参考图生成新图
        draw_with_multiple_images(
            [
                {"image_path": "shared/style_ref.jpg", "description": "艺术风格参考，水彩画风格", "weight": 1.2},
                {"image_path": "shared/pose_ref.jpg", "description": "人物姿势参考", "weight": 0.8}
            ],
            "一个穿着古装的女子在樱花树下跳舞，融合水彩画风格",
            "1024x1024"
        )
    """
    # 检查是否启用多图功能且处于聊天模式
    if not config.ENABLE_MULTI_IMAGE:
        raise Exception("多图输入功能已禁用，请在插件配置中启用")
    
    if config.MODEL_MODE != "聊天模式":
        raise Exception("多图输入功能仅在聊天模式下可用，请切换到聊天模式")
    
    def _validate_reference_images(ref_images: List[Dict[str, Any]]) -> List[ImageReference]:
        """验证并转换参考图片数据"""
        if not isinstance(ref_images, list):
            raise TypeError("reference_images 必须是列表格式")
        
        if len(ref_images) == 0:
            raise ValueError("至少需要提供一张参考图片")
        
        if len(ref_images) > 5:
            raise ValueError("最多支持5张参考图片")
        
        image_refs = []
        for i, img_data in enumerate(ref_images):
            if not isinstance(img_data, dict):
                raise TypeError(f"参考图片{i+1}必须是字典格式")
            
            if "image_path" not in img_data:
                raise ValueError(f"参考图片{i+1}缺少必需的 image_path 字段")
            
            if "description" not in img_data:
                raise ValueError(f"参考图片{i+1}缺少必需的 description 字段")
            
            image_ref = ImageReference(
                image_path=img_data["image_path"],
                description=img_data["description"],
                weight=img_data.get("weight", 1.0),
            )
            image_refs.append(image_ref)
        
        return image_refs
    
    try:
        # 验证并转换参考图片数据
        image_refs = _validate_reference_images(reference_images)
        
        # 创建多图绘制请求
        multi_request = MultiImageDrawRequest(
            reference_images=image_refs,
            target_prompt=target_prompt,
            size=size,
            guidance_scale=guidance_scale,
            send_to_chat=send_to_chat,
        )
        
        # 验证请求
        multi_request.validate_images()
        
        # 生成图片
        result_file_url = await generate_multi_image(
            multi_request=multi_request,
            chat_key=_ctx.chat_key,
            container_key=_ctx.container_key or "",
        )
        
        # 转换为沙盒文件
        result_sandbox_file = await _ctx.fs.mixed_forward_file(result_file_url)
        
        # 如果需要发送到聊天
        if send_to_chat:
            await _ctx.ms.send_image(send_to_chat, result_sandbox_file, ctx=_ctx)
        
    except (ValueError, TypeError, KeyError) as e:
        raise Exception(f"参考图片信息格式错误: {e}") from e
    except Exception as e:
        logger.error(f"多图绘制失败: {e}")
        raise Exception(f"多图绘制失败: {e}") from e
    else:
        return result_sandbox_file


@plugin.mount_collect_methods()
async def collect_available_methods(_ctx: AgentCtx) -> List[Any]:
    """根据配置动态提供可用方法"""
    methods = [draw]  # 基础绘图方法始终可用
    
    # 只有在聊天模式且启用多图功能时才提供多图绘制方法
    if config.MODEL_MODE == "聊天模式" and config.ENABLE_MULTI_IMAGE:
        methods.append(draw_with_multiple_images)
    
    return methods


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""


async def generate_image_api(
    model_group,
    prompt: str,
    negative_prompt: str,
    size: str,
    num_inference_steps: int,
    guidance_scale: float,
    source_image_data: str,
) -> str:
    """使用图像生成 API 模式绘图"""

    # 构造请求体
    json_data = {
        "model": model_group.CHAT_MODEL,
        "prompt": prompt,
        "image_size": size,
        "batch_size": 1,
        "seed": random.randint(0, 9999999999),
        "num_inference_steps": num_inference_steps,
        "guidance_scale": guidance_scale,
    }

    # 如果source_image_data != "data:image/webp;base64, XXX"(根据前面refer_image)则在json_data中填入image
    # 防止siliconcloud在image填入错误数据会失败
    if source_image_data != "data:image/webp;base64, XXX":
        json_data["image"] = source_image_data

    # 检测negative_prompt删去所有空格字符是否为空
    if negative_prompt.replace(" ", "") != "":
        json_data["negative_prompt"] = negative_prompt

    async with AsyncClient() as client:
        response = await client.post(
            f"{model_group.BASE_URL}/images/generations",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {model_group.API_KEY}",
            },
            json=json_data,
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


async def generate_chat_response_with_image_support(
    model_group,
    messages: List[Dict[str, Any]],
    stream_mode: bool = True,
    max_wait_time: int = 300,
) -> str:
    """生成支持 image 字段的聊天响应

    Args:
        model_group: 模型组配置
        messages: 消息列表
        stream_mode: 是否使用流式模式
        max_wait_time: 最大等待时间

    Returns:
        str: 图片 URL 或 base64 数据

    Raises:
        Exception: 当无法找到图片内容时
    """
    #判断是否使用谷歌原生API适配模式    
    if config.GOOGLE_NATAVE:
        logger.info("使用谷歌原生API适配模式绘图请求")
        
        # 1. 基础配置
        URL = f"https://generativelanguage.googleapis.com/v1beta/{model_group.CHAT_MODEL}:generateContent?key={model_group.API_KEY}"
        
        # 2. 消息转换逻辑
        def build_google_contents(messages):
            contents = []
            for msg in messages:
                if not isinstance(msg, dict): continue
                
                # 角色映射: assistant/system -> model, 其它 -> user
                role = "model" if msg.get("role") in ["assistant", "system"] else "user"
                parts = []

                # A. 处理文本
                if msg.get("content"):
                    parts.append({"text": str(msg["content"])})
                
                # B. 处理图片 (自动清洗Base64前缀)
                if msg.get("image"):
                    img_data = msg["image"]
                    mime_type = "image/jpeg" # 默认
                    
                    # 简单解析 data:image/png;base64,xxxx
                    if "base64," in img_data:
                        header, img_data = img_data.split("base64,")
                        if "png" in header: mime_type = "image/png"
                        elif "webp" in header: mime_type = "image/webp"

                    parts.append({
                        "inlineData": {"mimeType": mime_type, "data": img_data}
                    })

                if parts:
                    contents.append({"role": role, "parts": parts})
            return contents

        # 3. 构造请求 Payload
        payload = {
            "contents": build_google_contents(messages),
            # 安全设置：一键全关
            "safetySettings": [
                {"category": cat, "threshold": "BLOCK_NONE"} 
                for cat in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", 
                            "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT", 
                            "HARM_CATEGORY_CIVIC_INTEGRITY"]
            ],
            "generationConfig": {"temperature": 0.8}
        }
        
        # logger.info(f"请求Payload摘要: {str(payload)[:200]}...")

        try:
            response = requests.post(URL, json=payload) # requests可以直接传json参数
            if response.status_code != 200:
                raise Exception(f"谷歌API报错 ({response.status_code}): {response.text}")

            result = response.json()
            candidate = result.get('candidates', [{}])[0]
            content_parts = candidate.get('content', {}).get('parts', [])

            collected_image_data = None
            collected_text = ""

            # 4. 解析响应 (扁平化处理)
            for part in content_parts:
                # 优先找图片
                if 'inlineData' in part:
                    collected_image_data = part['inlineData']['data']
                elif 'inline_data' in part: # 兼容写法
                    collected_image_data = part['inline_data']['data']
                # 记录文本用于兜底
                if 'text' in part:
                    collected_text += part['text']
                    logger.info(f"文本输出: {collected_text}")
            
        except Exception as e:
            logger.error(f"❌ 谷歌API请求流程失败: {e}")
            raise                    
    else:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {model_group.API_KEY}",
        }

        json_data = {
            "model": model_group.CHAT_MODEL,
            "messages": messages,
            "stream": stream_mode,
        }

        collected_content = ""
        collected_image_data: Optional[str] = None

        async with AsyncClient(timeout=Timeout(read=max_wait_time, write=max_wait_time, connect=10, pool=10)) as client:
            if stream_mode:
                # 流式请求
                async with client.stream(
                    "POST",
                    f"{model_group.BASE_URL}/chat/completions",
                    headers=headers,
                    json=json_data,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue

                        # 处理 SSE 格式
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            if data_str.strip() == "[DONE]":
                                break

                            try:
                                chunk_data = json.loads(data_str)
                                choices = chunk_data.get("choices", [])
                                if not choices:
                                    continue

                                delta = choices[0].get("delta", {})

                                # 优先检查 image 字段
                                image_data = delta.get("image")
                                if image_data and isinstance(image_data, list) and image_data:
                                    # 取第一张图片的 base64 数据
                                    collected_image_data = image_data[0].get("data")
                                    if isinstance(collected_image_data, str):
                                        logger.debug(f"找到 image 字段，数据长度: {len(collected_image_data)}")

                                # 收集 content 内容作为备选
                                content_data = delta.get("content")
                                if content_data:
                                    collected_content += content_data

                            except json.JSONDecodeError as e:
                                logger.debug(f"解析 JSON 失败: {e}, 数据: {data_str}")
                                continue
            else:
                # 非流式请求
                response = await client.post(
                    f"{model_group.BASE_URL}/chat/completions",
                    headers=headers,
                    json=json_data,
                )
                response.raise_for_status()
                data = response.json()

                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})

                    # 检查是否有 image 字段
                    image_data = message.get("image")
                    if image_data and isinstance(image_data, list) and image_data:
                        collected_image_data = image_data[0]

                    # 收集 content 内容
                    content_data = message.get("content")
                    if content_data:
                        collected_content = content_data

    # 优先返回 image 字段中的 base64 数据
    if collected_image_data:
        logger.info("使用 image 字段中的 base64 数据")
        return f"data:image/png;base64,{collected_image_data}"

    # 回退到从 content 中提取图片信息
    if collected_content:
        logger.info("从 content 中提取图片信息")
        return extract_image_from_content(collected_content)

    # 都没有找到
    raise Exception("未找到图片内容，请检查模型响应或调整提示词")


async def generate_chat_mode_image(model_group, prompt: str, size: str, refer_image: str, source_image_data: str) -> str:
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

    try:
        # 使用新的支持 image 字段的响应处理函数
        return await generate_chat_response_with_image_support(
            model_group=model_group,
            messages=messages,
            stream_mode=config.STREAM_MODE,
            max_wait_time=config.TIMEOUT,
        )
    except Exception as e:
        logger.error(f"绘图响应处理失败: {e}")
        raise Exception(
            "No image content found in image generation AI response. You can adjust the prompt and try again. Make sure the prompt is not contain any sensitive or illegal information.",
        ) from e


async def prepare_reference_image(refer_image: str, chat_key: str, container_key: str) -> str:
    """准备参考图片数据"""
    if refer_image:
        async with aiofiles.open(
            convert_to_host_path(Path(refer_image), chat_key=chat_key, container_key=container_key),
            mode="rb",
        ) as f:
            image_data = await f.read()
            mime_type = magic.from_buffer(image_data, mime=True)
            image_data = base64.b64encode(image_data).decode("utf-8")
        return f"data:{mime_type};base64,{image_data}"
    return "data:image/webp;base64, XXX"


async def prepare_multiple_reference_images(
    image_refs: List[ImageReference], 
    chat_key: str, 
    container_key: str,
) -> List[str]:
    """准备多个参考图片数据"""
    image_data_list = []
    
    for image_ref in image_refs:
        async with aiofiles.open(
            convert_to_host_path(Path(image_ref.image_path), chat_key=chat_key, container_key=container_key),
            mode="rb",
        ) as f:
            image_data = await f.read()
            mime_type = magic.from_buffer(image_data, mime=True)
            image_data_b64 = base64.b64encode(image_data).decode("utf-8")
            image_data_list.append(f"data:{mime_type};base64,{image_data_b64}")
    
    return image_data_list


async def generate_multi_image(
    multi_request: MultiImageDrawRequest,
    chat_key: str,
    container_key: str,
) -> str:
    """生成多图输入的图片"""
    if config.MODEL_MODE != "聊天模式":
        raise Exception("多图输入功能仅在聊天模式下可用")
    
    logger.info(f"使用多图绘制模式，参考图片数量: {len(multi_request.reference_images)}")
    
    if config.USE_DRAW_MODEL_GROUP not in global_config.MODEL_GROUPS:
        raise Exception(f"绘图模型组 `{config.USE_DRAW_MODEL_GROUP}` 未配置")
    
    model_group = global_config.MODEL_GROUPS[config.USE_DRAW_MODEL_GROUP]
    
    # 准备所有参考图片数据
    image_data_list = await prepare_multiple_reference_images(
        multi_request.reference_images, chat_key, container_key,
    )
    
    # 构建多图聊天消息
    system_content = "You are a professional painter with expertise in analyzing and combining multiple visual references. Use your skills to create a new image that thoughtfully incorporates elements from all provided reference images while following the target description."
    
    # 构建综合提示词
    combined_prompt = multi_request.construct_prompt()
    
    msg = OpenAIChatMessage.create_empty("user")
    
    # 添加所有参考图片
    for i, (image_ref, image_data) in enumerate(zip(multi_request.reference_images, image_data_list)):
        msg = msg.add(ContentSegment.image_content(image_data))
        # 为每张图片添加单独的描述
        weight_info = f" (参考权重: {image_ref.weight})" if image_ref.weight != 1.0 else ""
        msg = msg.add(ContentSegment.text_content(f"参考图片{i+1}: {image_ref.description}{weight_info}\n"))
    
    # 添加目标描述
    if not config.USE_SYSTEM_ROLE:
        full_prompt = f"{system_content}\n\n{combined_prompt}\n\n请生成尺寸为 {multi_request.size} 的图片。"
    else:
        full_prompt = f"{combined_prompt}\n\n请生成尺寸为 {multi_request.size} 的图片。"
    
    msg = msg.add(ContentSegment.text_content(full_prompt))
    
    # 构建消息列表
    messages = []
    if config.USE_SYSTEM_ROLE:
        messages.append({
            "role": "system", 
            "content": system_content,
        })
    messages.append(msg.to_dict())
    
    try:
        # 使用聊天模式生成图片
        return await generate_chat_response_with_image_support(
            model_group=model_group,
            messages=messages,
            stream_mode=config.STREAM_MODE,
            max_wait_time=config.TIMEOUT,
        )
    except Exception as e:
        logger.error(f"多图绘制失败: {e}")
        raise Exception(f"多图绘制失败: {e}") from e


async def generate_image(
    model_group_name: str,
    prompt: str,
    size: str = "1024x1024",
    guidance_scale: float = 7.5,
    refer_image: str = "",
    chat_key: str = "",
    container_key: str = "",
) -> str:
    """生成图片的主函数"""
    global last_successful_mode

    logger.info(f"使用绘图模型组: {model_group_name} 绘制: {prompt}")

    if model_group_name not in global_config.MODEL_GROUPS:
        raise Exception(f"绘图模型组 `{model_group_name}` 未配置")

    model_group = global_config.MODEL_GROUPS[model_group_name]

    # 准备参考图片数据
    source_image_data = await prepare_reference_image(refer_image, chat_key, container_key)

    # 使用指定模式
    if config.MODEL_MODE == "图像生成":
        return await generate_image_api(
            model_group,
            prompt,
            config.NEGATIVE_PROMPT,
            size,
            config.NUM_INFERENCE_STEPS,
            guidance_scale,
            source_image_data,
        )
    # 聊天模式
    return await generate_chat_mode_image(model_group, prompt, size, refer_image, source_image_data)
