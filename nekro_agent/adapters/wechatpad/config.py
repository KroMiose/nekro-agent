
from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField


class WeChatPadConfig(BaseAdapterConfig):
    """WeChatPad 适配器配置"""

    WECHATPAD_API_URL: str = Field(
        default="http://127.0.0.1:8080",
        title="WeChatPadPro API 地址",
        description="您部署的 WeChatPadPro 项目的 API 服务地址",
    )

    WECHATPAD_AUTH_KEY: str = Field(
        default="",
        title="WeChatPadPro AuthKey",
        description="用于 API 认证的 AuthKey，作为 query parameter 'key' 传递",
        json_schema_extra=ExtraField(required=True).model_dump(),
    )

    WECHATPAD_CALLBACK_URL: str = Field(
        default="",
        title="WeChatPadPro 回调地址",
        description="用于接收微信事件（如新消息）的回调地址。需要是一个公网可访问的 URL，例如: http://your_domain.com/api/v1/adapters/wechatpad/webhook",
    )

    SESSION_PROCESSING_WITH_EMOJI: bool = Field(
        default=False,
        title="显示处理中表情反馈",
        description="当 AI 开始处理消息时，对应消息会显示处理中表情反馈（微信不支持此功能）",
    )
