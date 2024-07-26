from miose_toolkit_common.mxios import AioResponse, Mxios

from nekro_agent.core import config

BASE_API = config.STABLE_DIFFUSION_API
PROXY = config.STABLE_DIFFUSION_PROXY or ""
DEFAULT_POSITIVE_PROMPTS = "best quality, masterpiece, anime illustration,,"
DEFAULT_NEGATIVE_PROMPTS = (
    "ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, extra limbs, disfigured,"
    "deformed, body out of frame, bad anatomy, watermark, signature, cut off, low contrast, underexposed, overexposed,"
    "bad art, beginner, amateur, distorted face"
)


http = Mxios()


async def text2img(positive_prompt: str, negative_prompt: str = DEFAULT_NEGATIVE_PROMPTS, resolution: str = "512x768") -> str:
    """文字转图像 返回base64图像

    Args:
        positive_prompt (str): 正向提示
        negative_prompt (str, optional): 负向提示. Defaults to DEFAULT_NEGATIVE_PROMPTS.
        resolution (str, optional): 图像分辨率. Defaults to "512x768".

    Returns:
        str: base64图像
    """

    sd_api = ("http://" + BASE_API) if not BASE_API.startswith("http") else BASE_API
    sd_api = sd_api[:-1] if sd_api.endswith("/") else sd_api

    # 检查 resolution 格式
    if "x" not in resolution and len(resolution.split("x")) != 2:
        raise ValueError("Invalid resolution format, should be like '512x768'")
    try:
        width, height = map(int, resolution.split("x"))
    except ValueError as e:
        raise ValueError("Invalid resolution format, should be like '512x768'") from e

    res: AioResponse = await http.async_post(
        f"{sd_api}/sdapi/v1/txt2img",
        data={
            "prompt": DEFAULT_POSITIVE_PROMPTS + positive_prompt,
            "negative_prompt": negative_prompt,
            "seed": -1,
            "batch_size": 1,
            "n_iter": 1,
            "steps": 12,
            "cfg_scale": 7,
            "width": width,
            "height": height,
            "restore_faces": False,
            "tiling": False,
            "override_settings": {},
            "override_settings_restore_afterwards": True,
            "disable_extra_networks": False,
            "enable_hr": False,
            "sampler_index": "DPM++ 2M",
            "send_images": True,
            "save_images": False,
        },
        headers={
            "Content-Type": "application/json",
            "accept": "application/json",
        },
        timeout=120,
        proxy_server=PROXY,
    )
    return res.json()["images"][0]


async def ai_text2img(prompt) -> str:
    prompt, negative_prompt = split_content(prompt)
    return await text2img(prompt, negative_prompt)


def split_content(gpt_prompt: str) -> tuple[str, str]:
    """分割 prompt"""
    if gpt_prompt.startswith("**Prompt:**"):
        gpt_prompt = gpt_prompt[len("**Prompt:**") :].strip()
    res_list = [s.strip() for s in gpt_prompt.split("**Negative Prompt:**")]
    return res_list[0], res_list[1] if len(res_list) > 1 else ""
