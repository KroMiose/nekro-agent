import base64

import httpx

from nekro_agent.core import config, logger

DEFAULT_POSITIVE_PROMPTS = "best quality, masterpiece, anime illustration,"
DEFAULT_NEGATIVE_PROMPTS = (
    "ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured,"
    "deformed, body out of frame, bad anatomy, watermark, signature, cut off, low contrast, underexposed, overexposed,"
    "bad art, beginner, amateur, distorted face,"
)

client = httpx.AsyncClient(
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
    timeout=120,
)


async def text2img(prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
    """通过 Stable Diffusion API 使用文本生成图像并返回图像字节数据"""
    base_api: str = config.STABLE_DIFFUSION_API
    base_api = base_api[:-1] if base_api.endswith("/") else base_api
    if not base_api.startswith("http"):
        base_api = f"http://{base_api}"
    logger.info(f"Generating image with Stable Diffusion API: {base_api}")
    try:
        response = await client.post(
            f"{base_api}/sdapi/v1/txt2img",
            json={
                "prompt": DEFAULT_POSITIVE_PROMPTS + prompt,
                "negative_prompt": DEFAULT_NEGATIVE_PROMPTS + negative_prompt,
                "sampler_name": "DPM++ 2M",
                "batch_size": 1,
                "n_iter": 1,
                "steps": 29,
                "cfg_scale": 7,
                "width": width,
                "height": height,
            },
        )
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Generating image failed: {e}")
        raise
    else:
        try:
            base64_img = response.json()["images"][0]["image"]
        except Exception:
            base64_img = response.json()["images"][0]
        return base64.decodebytes(base64_img.encode())
