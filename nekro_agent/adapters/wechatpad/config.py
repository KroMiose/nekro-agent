from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig, adapter_extra_field


class WeChatPadConfig(BaseAdapterConfig):
    """WeChatPad 适配器配置"""

    WECHATPAD_API_URL: str = Field(
        default="http://127.0.0.1:8080",
        title="WeChatPadPro API 地址",
        description="您部署的 WeChatPadPro 项目的 API 服务地址",
        json_schema_extra=adapter_extra_field(
            title_zh="WeChatPadPro API 地址",
            title_en="WeChatPadPro API URL",
            description_zh="您部署的 WeChatPadPro 项目的 API 服务地址",
            description_en="API service URL of your deployed WeChatPadPro instance.",
            category_zh="WeChatPadPro",
            category_en="WeChatPadPro",
        ),
    )

    WECHATPAD_AUTH_KEY: str = Field(
        default="",
        title="WeChatPadPro AuthKey",
        description="用于 API 认证的 AuthKey，作为 query parameter 'key' 传递",
        json_schema_extra=adapter_extra_field(
            title_zh="WeChatPadPro AuthKey",
            title_en="WeChatPadPro AuthKey",
            description_zh="用于 API 认证的 AuthKey，作为 query parameter 'key' 传递",
            description_en="AuthKey used for API authentication. It is passed as the 'key' query parameter.",
            category_zh="WeChatPadPro",
            category_en="WeChatPadPro",
            required=True,
        ),
    )

    WECHATPAD_CALLBACK_URL: str = Field(
        default="",
        title="WeChatPadPro 回调地址",
        description="用于接收微信事件（如新消息）的回调地址。需要是一个公网可访问的 URL，例如: http://your_domain.com/api/v1/adapters/wechatpad/webhook",
        json_schema_extra=adapter_extra_field(
            title_zh="WeChatPadPro 回调地址",
            title_en="WeChatPadPro Callback URL",
            description_zh="用于接收微信事件（如新消息）的回调地址。需要是一个公网可访问的 URL，例如: http://your_domain.com/api/v1/adapters/wechatpad/webhook",
            description_en="Callback URL used to receive WeChat events such as new messages. It must be publicly accessible, for example: http://your_domain.com/api/v1/adapters/wechatpad/webhook.",
            category_zh="WeChatPadPro",
            category_en="WeChatPadPro",
        ),
    )

    SESSION_PROCESSING_WITH_EMOJI: bool = Field(
        default=False,
        title="显示处理中表情反馈",
        description="当 AI 开始处理消息时，对应消息会显示处理中表情反馈（微信不支持此功能）",
        json_schema_extra=adapter_extra_field(
            title_zh="显示处理中表情反馈",
            title_en="Show Processing Emoji Feedback",
            description_zh="当 AI 开始处理消息时，对应消息会显示处理中表情反馈（微信不支持此功能）",
            description_en="When AI starts processing a message, a processing emoji reaction would be shown on the corresponding message. This is not supported by WeChat.",
            category_zh="交互",
            category_en="Interaction",
        ),
    )
