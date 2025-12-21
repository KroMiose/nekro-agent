from typing import Literal

from pydantic import Field

from nekro_agent.api import i18n
from nekro_agent.api.plugin import ConfigBase, ExtraField, NekroPlugin

# 创建插件实例
plugin = NekroPlugin(
    name="绘画插件",
    module_name="draw",
    description="学会画画！",
    version="0.2.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="绘画插件",
        en_US="Drawing Plugin",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="学会画画！",
        en_US="Learn to draw!",
    ),
)


@plugin.mount_config()
class DrawConfig(ConfigBase):
    """绘画配置"""

    USE_DRAW_MODEL_GROUP: str = Field(
        default="default-draw-chat",
        title="绘图模型组",
        description="主要使用的绘图模型组，可在 `系统配置` -> `模型组` 选项卡配置",
        json_schema_extra=ExtraField(
            ref_model_groups=True,
            required=True,
            model_type="draw",
            i18n_title=i18n.i18n_text(
                zh_CN="绘图模型组",
                en_US="Drawing Model Group",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="主要使用的绘图模型组，可在 `系统配置` -> `模型组` 选项卡配置",
                en_US="Primary drawing model group, configurable in `System Settings` -> `Model Groups` tab",
            ),
        ).model_dump(),
    )
    MODEL_MODE: Literal["图像生成", "聊天模式"] = Field(
        default="聊天模式",
        title="绘图模型调用格式",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="绘图模型调用格式",
                en_US="Drawing Model Call Format",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="选择模型的调用方式：图像生成或聊天模式",
                en_US="Select model invocation method: Image Generation or Chat Mode",
            ),
        ).model_dump(),
    )
    NUM_INFERENCE_STEPS: int = Field(
        default=20,
        title="模型推理步数",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="模型推理步数",
                en_US="Model Inference Steps",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="模型生成图像的推理步数，步数越多质量越高但速度越慢",
                en_US="Number of inference steps for image generation, more steps means higher quality but slower speed",
            ),
        ).model_dump(),
    )
    USE_SYSTEM_ROLE: bool = Field(
        default=False,
        title="是否使用系统角色",
        description="只对聊天模式下的模型调用有效，如果启用时会把部分绘图提示词添加到系统角色中，如果模型不支持系统消息请关闭该选项",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="是否使用系统角色",
                en_US="Use System Role",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="只对聊天模式下的模型调用有效，如果启用时会把部分绘图提示词添加到系统角色中，如果模型不支持系统消息请关闭该选项",
                en_US="Only valid in chat mode, adds drawing prompts to system role when enabled. Disable if model doesn't support system messages",
            ),
        ).model_dump(),
    )
    STREAM_MODE: bool = Field(
        default=False,
        title="聊天模式使用流式 API",
        description="由于模型生成时间问题，部分模型需要在聊天模式下启用流式 API 才能正常工作",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="聊天模式使用流式 API",
                en_US="Use Streaming API in Chat Mode",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="由于模型生成时间问题，部分模型需要在聊天模式下启用流式 API 才能正常工作",
                en_US="Some models require streaming API in chat mode due to generation time constraints",
            ),
        ).model_dump(),
    )
    ENABLE_MULTI_IMAGE: bool = Field(
        default=True,
        title="启用多图输入参考",
        description="仅在聊天模式下有效，允许AI使用多张参考图片来生成新图片。推荐使用 gemini-2.5-flash-image-preview 等高一致性模型。",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="启用多图输入参考",
                en_US="Enable Multi-Image Reference",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="仅在聊天模式下有效，允许AI使用多张参考图片来生成新图片。推荐使用 gemini-2.5-flash-image-preview 等高一致性模型",
                en_US="Only valid in chat mode, allows AI to use multiple reference images. Recommended with high-consistency models like gemini-2.5-flash-image-preview",
            ),
        ).model_dump(),
    )
    MAX_IMAGE_NUM: int = Field(
        default=5,
        title="最大参考图片数量",
        description="允许的最大参考图片数量",
        ge=1,
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="最大参考图片数量",
                en_US="Max Reference Image Count",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="允许的最大参考图片数量",
                en_US="Maximum number of reference images allowed",
            ),
        ).model_dump(),
    )
    TIMEOUT: int = Field(
        default=300,
        title="绘图超时时间",
        description="单位: 秒",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="绘图超时时间",
                en_US="Drawing Timeout",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="单位: 秒",
                en_US="Unit: seconds",
            ),
        ).model_dump(),
    )
    NEGATIVE_PROMPT: str = Field(
        default="((blurred)), ((disorderly)), ((bad art)), ((morbid)), ((Luminous)), out of frame, not clear, overexposure, lens flare, bokeh, jpeg artifacts, glowing light, (low quality:2.0),((black color)), shadowlowers, bad anatomy, ((bad hands)), (worst quality:2), (low quality:2), (normal quality:2), lowres, bad anatomy, text",
        title="负面提示",
        description="模型生成图像时的负面提示。置空则请求中不添加负面提示词，不修改原行为，支持自然语言，默认为 `(blurred), (disorderly), (morbid), (low quality:2), (bad art)` 等",
        json_schema_extra=ExtraField(
            is_textarea=True,
            i18n_title=i18n.i18n_text(
                zh_CN="负面提示",
                en_US="Negative Prompt",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="模型生成图像时的负面提示。置空则请求中不添加负面提示词，不修改原行为，支持自然语言",
                en_US="Negative prompt for image generation. Leave empty to omit negative prompts, supports natural language",
            ),
        ).model_dump(),
    )


# 获取配置
config: DrawConfig = plugin.get_config(DrawConfig)
