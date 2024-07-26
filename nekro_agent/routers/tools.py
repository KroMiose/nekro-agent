import base64

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from nekro_agent.core import logger
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.http_exception import server_error_exception
from nekro_agent.systems.user.deps import get_current_active_user
from nekro_agent.tools.sd_util import text2img

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.post("/sd_draw", summary="Stable Diffusion - Text2Img")
async def sd_draw(
    positive_prompt: str,
    negative_prompt: str = "",
    image_size: str = "512x512",
    current_user: DBUser = Depends(get_current_active_user),
) -> Response:
    assert current_user
    logger.info(f"用户 {current_user.username} 请求生成SD图片: {positive_prompt[:32]}...")

    try:
        base64_img_str = await text2img(positive_prompt, negative_prompt, image_size)
    except Exception as e:
        logger.error(f"生成SD图片失败: {e}")
        raise server_error_exception from e

    file_bytes = base64.b64decode(base64_img_str)
    return Response(content=file_bytes, media_type="image/png")
