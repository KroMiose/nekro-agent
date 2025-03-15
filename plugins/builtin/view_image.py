from pathlib import Path
from typing import List

from pydantic import Field

from nekro_agent.api.core import logger
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.services.agent.creator import ContentSegment, OpenAIChatMessage
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.tools.path_convertor import convert_to_host_path

plugin = NekroPlugin(
    name="[NA] 图片查看插件",
    module_name="view_image",
    description="提供图片查看功能",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)

@plugin.mount_sandbox_method(SandboxMethodType.MULTIMODAL_AGENT, "图片观察工具")
async def view_image(_ctx: AgentCtx, images: List[str]):
    """利用视觉观察图片

    Attention: Do not repeatedly observe the contents of the visual image given in the context!

    Args:
        images (List[str]): 图片共享路径或在线url列表
    """
    logger.debug(f"图片观察工具: {images}")
    msg = OpenAIChatMessage.from_text("user", "Here are the images you requested:")

    for i, image_path in enumerate(images):
        # 判断是否为URL（简单判断是否以http开头）
        if image_path.startswith(("http://", "https://")):
            # 使用URL方式
            msg.batch_add(
                [
                    ContentSegment.text_content(f"Image {i+1}: {image_path}"),
                    ContentSegment.image_content(image_path),
                ],
            )
        else:
            # 使用文件路径方式
            path = convert_to_host_path(Path(image_path), chat_key=_ctx.from_chat_key)
            msg.batch_add(
                [
                    ContentSegment.text_content(f"Image {i+1}: {path}"),
                    ContentSegment.image_content_from_path(path),
                ],
            )

    return msg.to_dict()