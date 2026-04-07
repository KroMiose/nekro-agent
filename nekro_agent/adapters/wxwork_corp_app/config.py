from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text


class WxWorkCorpAppConfig(BaseAdapterConfig):
    """企业微信自建应用适配器配置。"""

    CORP_ID: str = Field(
        default="",
        title="Corp ID",
        description="企业微信自建应用所属企业的 CorpID，用于获取 access_token 和回调校验",
        json_schema_extra=ExtraField(
            required=True,
            placeholder="wwxxxxxxxxxxxxxxxx",
            i18n_category=i18n_text(zh_CN="自建应用模式", en_US="Corp App Mode"),
            i18n_title=i18n_text(zh_CN="Corp ID", en_US="Corp ID"),
            i18n_description=i18n_text(
                zh_CN="企业微信自建应用所属企业的 CorpID，用于获取 access_token 和回调校验",
                en_US="CorpID of the enterprise that owns the WeCom custom app. Used to obtain access_token and validate callbacks.",
            ),
        ).model_dump(),
    )

    CORP_APP_SECRET: str = Field(
        default="",
        title="Secret",
        description="企业微信自建应用的 Secret，用于获取 access_token",
        json_schema_extra=ExtraField(
            required=True,
            is_secret=True,
            i18n_category=i18n_text(zh_CN="自建应用模式", en_US="Corp App Mode"),
            i18n_title=i18n_text(zh_CN="Secret", en_US="Secret"),
            i18n_description=i18n_text(
                zh_CN="企业微信自建应用的 Secret，用于获取 access_token",
                en_US="Secret of the WeCom custom app, used to obtain access_token.",
            ),
        ).model_dump(),
    )

    CORP_APP_AGENT_ID: str = Field(
        default="",
        title="Agent ID",
        description="企业微信自建应用的 AgentId，用于发送应用消息和标识当前应用",
        json_schema_extra=ExtraField(
            required=True,
            placeholder="1000002",
            i18n_category=i18n_text(zh_CN="自建应用模式", en_US="Corp App Mode"),
            i18n_title=i18n_text(zh_CN="Agent ID", en_US="Agent ID"),
            i18n_description=i18n_text(
                zh_CN="企业微信自建应用的 AgentId，用于发送应用消息和标识当前应用",
                en_US="AgentId of the WeCom custom app, used to send app messages and identify the current app.",
            ),
        ).model_dump(),
    )

    CORP_API_BASE_URL: str = Field(
        default="https://qyapi.weixin.qq.com",
        title="API 地址",
        description="企业微信自建应用 API 地址，默认使用官方地址",
        json_schema_extra=ExtraField(
            placeholder="https://qyapi.weixin.qq.com",
            i18n_category=i18n_text(zh_CN="自建应用模式", en_US="Corp App Mode"),
            i18n_title=i18n_text(zh_CN="API 地址", en_US="API Base URL"),
            i18n_description=i18n_text(
                zh_CN="企业微信自建应用 API 地址，默认使用官方地址",
                en_US="API base URL for the WeCom custom app. The official URL is used by default.",
            ),
        ).model_dump(),
    )

    CALLBACK_TOKEN: str = Field(
        default="",
        title="Callback Token",
        description="企业微信自建应用回调配置中的 Token，用于校验请求来源",
        json_schema_extra=ExtraField(
            required=True,
            is_secret=True,
            i18n_category=i18n_text(zh_CN="自建应用模式", en_US="Corp App Mode"),
            i18n_title=i18n_text(zh_CN="Callback Token", en_US="Callback Token"),
            i18n_description=i18n_text(
                zh_CN="企业微信自建应用回调配置中的 Token，用于校验请求来源",
                en_US="Token configured for WeCom custom app callbacks, used to verify the request source.",
            ),
        ).model_dump(),
    )

    CALLBACK_ENCODING_AES_KEY: str = Field(
        default="",
        title="Callback EncodingAESKey",
        description="企业微信自建应用回调配置中的 EncodingAESKey，用于消息加解密",
        json_schema_extra=ExtraField(
            required=True,
            is_secret=True,
            i18n_category=i18n_text(zh_CN="自建应用模式", en_US="Corp App Mode"),
            i18n_title=i18n_text(zh_CN="Callback EncodingAESKey", en_US="Callback EncodingAESKey"),
            i18n_description=i18n_text(
                zh_CN="企业微信自建应用回调配置中的 EncodingAESKey，用于消息加解密",
                en_US="EncodingAESKey configured for WeCom custom app callbacks, used for message encryption and decryption.",
            ),
        ).model_dump(),
    )

    REQUEST_TIMEOUT_SECONDS: int = Field(
        default=10,
        title="请求超时",
        description="HTTP 请求与回调处理的超时时间（秒）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="请求超时", en_US="Request Timeout"),
            i18n_description=i18n_text(
                zh_CN="HTTP 请求与回调处理的超时时间（秒）",
                en_US="Timeout for HTTP requests and callback handling, in seconds.",
            ),
        ).model_dump(),
    )

    TREAT_ALL_RECEIVED_MESSAGES_AS_TOME: bool = Field(
        default=True,
        title="所有收到的消息均触发 AI",
        description="开启后，所有自建应用回调收到的消息都会视为与机器人相关并进入触发判断",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="所有收到的消息均触发 AI", en_US="Treat All Received Messages as To-Me"),
            i18n_description=i18n_text(
                zh_CN="开启后，所有自建应用回调收到的消息都会视为与机器人相关并进入触发判断",
                en_US="When enabled, all messages received from custom app callbacks will be treated as related to the bot and enter trigger evaluation.",
            ),
        ).model_dump(),
    )

    ENABLE_TEXT_MESSAGE_COLLECTION: bool = Field(
        default=True,
        title="接入文本消息",
        description="开启后会将自建应用回调中的文本消息接入统一消息收集器",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="接入文本消息", en_US="Collect Text Messages"),
            i18n_description=i18n_text(
                zh_CN="开启后会将自建应用回调中的文本消息接入统一消息收集器",
                en_US="When enabled, text messages from custom app callbacks will be collected by the unified message collector.",
            ),
        ).model_dump(),
    )

    RAW_LOG_MAX_LENGTH: int = Field(
        default=12000,
        title="日志最大长度",
        description="回调原始内容日志最大长度，超过后自动截断",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="日志最大长度", en_US="Raw Log Max Length"),
            i18n_description=i18n_text(
                zh_CN="回调原始内容日志最大长度，超过后自动截断",
                en_US="Maximum length of raw callback content logs. Content beyond this length will be truncated automatically.",
            ),
        ).model_dump(),
    )
