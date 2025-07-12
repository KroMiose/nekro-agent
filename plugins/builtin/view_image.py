"""
# 查看图片 (View Image)

为**不具备**多模态视觉能力的模型提供"看懂"图片的能力。

## 主要功能

- **图像描述**: 当主模型不具备视觉能力时，此插件会调用一个独立配置的视觉模型来分析图片内容，并将分析结果以文字形式返回给主模型。
- **兼容层**: 它作为一个兼容性插件，使得非多模态模型也能处理包含图片的用户输入。

## 使用方法

- **配置视觉模型**: 在插件配置中，你需要指定一个拥有视觉能力的模型（`VISION_MODEL`），这个模型将专门用于解析图片。
- **自动调用**: 配置完成后，当一个不具备视觉能力的 Agent 需要理解图片时，可以调用此插件提供的工具来"观察"图片。

## 注意事项

- 如果你的主模型本身就支持多模态（例如 GPT-4V），请**不要**启用此插件。启用此插件可能会导致不必要的性能开销和非预期的行为。
- 对于本身支持多模态的模型，框架内置了处理逻辑，它们可以直接接收和处理图片信息，无需此插件介入。
"""

from pathlib import Path
from typing import Any, Dict, List

from pydantic import Field

from nekro_agent.api import core
from nekro_agent.api.plugin import ConfigBase, NekroPlugin, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.config import ModelConfigGroup
from nekro_agent.core.config import config as core_config
from nekro_agent.services.agent.creator import ContentSegment, OpenAIChatMessage
from nekro_agent.services.agent.openai import gen_openai_chat_response
from nekro_agent.tools.path_convertor import convert_to_host_path

plugin = NekroPlugin(
    name="查看图片",
    module_name="view_image",
    description="为不具备多模态视觉能力的模型提供图像理解能力",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    support_adapter=["onebot_v11", "sse", "discord"],
)


@plugin.mount_config()
class ViewImageConfig(ConfigBase):
    """基础配置"""

    VISION_MODEL: str = Field(
        default="default",
        title="用于查看图片的模型,如果主模型自带视觉请勿开启本插件",
        description="用于查看图片并描述内容,以文本形式返回给主模型",
        json_schema_extra={"ref_model_groups": True, "required": True, "model_type": "chat"},
    )


def get_view_image_config() -> ViewImageConfig:
    """获取最新的记忆模块配置"""
    return plugin.get_config(ViewImageConfig)


# 根据模型名获取模型组配置项
def get_model_group_info(model_name: str) -> ModelConfigGroup:
    try:
        return core_config.MODEL_GROUPS[model_name]
    except KeyError as e:
        raise ValueError(f"模型组 '{model_name}' 不存在，请确认配置正确") from e


# @plugin.mount_sandbox_method(
#     SandboxMethodType.MULTIMODAL_AGENT,
#     name="查看图片",
#     description="使 Agent 能够读取图片内容，以更好地理解上下文",
# )
# async def view_image(_ctx: AgentCtx, image_path: str, prompt: str) -> Dict[str, Any]:
#     """查看图片

#     Args:
#         image_path (str): 图片路径
#         prompt (str): 提示

#     Returns:
#         Dict: 多模态消息
#     """
#     msg = OpenAIChatMessage.create_empty("user")
#     msg = msg.add(ContentSegment.image_content_from_path(image_path))
#     msg = msg.add(ContentSegment.text_content(prompt))
#     return msg.to_dict()


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "图片观察工具")
async def view_image(_ctx: AgentCtx, images: List[str]):
    """利用视觉观察图片

    Attention: Do not repeatedly observe the contents of the visual image given in the context!

    Args:
        images (List[str]): 图片路径或在线url列表
    """

    core.logger.debug(f"图片观察工具: {images}")

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
    vision_prompt = "Describe the content shown in this images in relatively detailed language."
    vision_msg = OpenAIChatMessage.from_text("system", vision_prompt)

    for i, image_path in enumerate(images):
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
            path = convert_to_host_path(Path(image_path), chat_key=_ctx.chat_key)
            if not path.exists():
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
        description = description_response.response_content

        if not description:
            return ""

    except Exception as e:
        core.logger.error(f"调用视觉模型 ({vision_model_group.CHAT_MODEL}) 时出错: {e}")
        raise RuntimeError(f"调用视觉模型失败: {e}") from e

    return f"The visual description of the images is as follows:\n{description}"
