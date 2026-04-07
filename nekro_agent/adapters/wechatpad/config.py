from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text


class WeChatPadConfig(BaseAdapterConfig):
    """WeChatPad 适配器配置"""

    WECHATPAD_API_URL: str = Field(
        default="http://127.0.0.1:8080",
        title="WeChatPadPro API 地址",
        description="您部署的 WeChatPadPro 项目的 API 服务地址",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="WeChatPadPro", en_US="WeChatPadPro"),
            i18n_title=i18n_text(zh_CN="WeChatPadPro API 地址", en_US="WeChatPadPro API URL"),
            i18n_description=i18n_text(
                zh_CN="您部署的 WeChatPadPro 项目的 API 服务地址",
                en_US="API service URL of your deployed WeChatPadPro instance.",
            ),
        ).model_dump(),
    )

    WECHATPAD_AUTH_KEY: str = Field(
        default="",
        title="WeChatPadPro AuthKey",
        description="用于 API 认证的 AuthKey，作为 query parameter 'key' 传递",
        json_schema_extra=ExtraField(
            required=True,
            i18n_category=i18n_text(zh_CN="WeChatPadPro", en_US="WeChatPadPro"),
            i18n_title=i18n_text(zh_CN="WeChatPadPro AuthKey", en_US="WeChatPadPro AuthKey"),
            i18n_description=i18n_text(
                zh_CN="用于 API 认证的 AuthKey，作为 query parameter 'key' 传递",
                en_US="AuthKey used for API authentication. It is passed as the 'key' query parameter.",
            ),
        ).model_dump(),
    )

    WECHATPAD_CALLBACK_URL: str = Field(
        default="",
        title="WeChatPadPro 回调地址",
        description="用于接收微信事件（如新消息）的回调地址。需要是一个公网可访问的 URL，例如: http://your_domain.com/api/v1/adapters/wechatpad/webhook",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="WeChatPadPro", en_US="WeChatPadPro"),
            i18n_title=i18n_text(zh_CN="WeChatPadPro 回调地址", en_US="WeChatPadPro Callback URL"),
            i18n_description=i18n_text(
                zh_CN="用于接收微信事件（如新消息）的回调地址。需要是一个公网可访问的 URL，例如: http://your_domain.com/api/v1/adapters/wechatpad/webhook",
                en_US="Callback URL used to receive WeChat events such as new messages. It must be publicly accessible, for example: http://your_domain.com/api/v1/adapters/wechatpad/webhook.",
            ),
        ).model_dump(),
    )

    SESSION_PROCESSING_WITH_EMOJI: bool = Field(
        default=False,
        title="显示处理中表情反馈",
        description="当 AI 开始处理消息时，对应消息会显示处理中表情反馈（微信不支持此功能）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="交互", en_US="Interaction"),
            i18n_title=i18n_text(zh_CN="显示处理中表情反馈", en_US="Show Processing Emoji Feedback"),
            i18n_description=i18n_text(
                zh_CN="当 AI 开始处理消息时，对应消息会显示处理中表情反馈（微信不支持此功能）",
                en_US="When AI starts processing a message, a processing emoji reaction would be shown on the corresponding message. This is not supported by WeChat.",
            ),
        ).model_dump(),
    )
