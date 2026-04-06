from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig, adapter_extra_field


class WxWorkCorpAppConfig(BaseAdapterConfig):
    """企业微信自建应用适配器配置。"""

    CORP_ID: str = Field(
        default="",
        title="Corp ID",
        description="企业微信自建应用所属企业的 CorpID，用于获取 access_token 和回调校验",
        json_schema_extra=adapter_extra_field(
            title_zh="Corp ID",
            title_en="Corp ID",
            description_zh="企业微信自建应用所属企业的 CorpID，用于获取 access_token 和回调校验",
            description_en="CorpID of the enterprise that owns the WeCom custom app. Used to obtain access_token and validate callbacks.",
            placeholder="wwxxxxxxxxxxxxxxxx",
            category_zh="自建应用模式",
            category_en="Corp App Mode",
            required=True,
        ),
    )

    CORP_APP_SECRET: str = Field(
        default="",
        title="Secret",
        description="企业微信自建应用的 Secret，用于获取 access_token",
        json_schema_extra=adapter_extra_field(
            title_zh="Secret",
            title_en="Secret",
            description_zh="企业微信自建应用的 Secret，用于获取 access_token",
            description_en="Secret of the WeCom custom app, used to obtain access_token.",
            is_secret=True,
            category_zh="自建应用模式",
            category_en="Corp App Mode",
            required=True,
        ),
    )

    CORP_APP_AGENT_ID: str = Field(
        default="",
        title="Agent ID",
        description="企业微信自建应用的 AgentId，用于发送应用消息和标识当前应用",
        json_schema_extra=adapter_extra_field(
            title_zh="Agent ID",
            title_en="Agent ID",
            description_zh="企业微信自建应用的 AgentId，用于发送应用消息和标识当前应用",
            description_en="AgentId of the WeCom custom app, used to send app messages and identify the current app.",
            placeholder="1000002",
            category_zh="自建应用模式",
            category_en="Corp App Mode",
            required=True,
        ),
    )

    CORP_API_BASE_URL: str = Field(
        default="https://qyapi.weixin.qq.com",
        title="API 地址",
        description="企业微信自建应用 API 地址，默认使用官方地址",
        json_schema_extra=adapter_extra_field(
            title_zh="API 地址",
            title_en="API Base URL",
            description_zh="企业微信自建应用 API 地址，默认使用官方地址",
            description_en="API base URL for the WeCom custom app. The official URL is used by default.",
            placeholder="https://qyapi.weixin.qq.com",
            category_zh="自建应用模式",
            category_en="Corp App Mode",
        ),
    )

    CALLBACK_TOKEN: str = Field(
        default="",
        title="Callback Token",
        description="企业微信自建应用回调配置中的 Token，用于校验请求来源",
        json_schema_extra=adapter_extra_field(
            title_zh="Callback Token",
            title_en="Callback Token",
            description_zh="企业微信自建应用回调配置中的 Token，用于校验请求来源",
            description_en="Token configured for WeCom custom app callbacks, used to verify the request source.",
            is_secret=True,
            category_zh="自建应用模式",
            category_en="Corp App Mode",
            required=True,
        ),
    )

    CALLBACK_ENCODING_AES_KEY: str = Field(
        default="",
        title="Callback EncodingAESKey",
        description="企业微信自建应用回调配置中的 EncodingAESKey，用于消息加解密",
        json_schema_extra=adapter_extra_field(
            title_zh="Callback EncodingAESKey",
            title_en="Callback EncodingAESKey",
            description_zh="企业微信自建应用回调配置中的 EncodingAESKey，用于消息加解密",
            description_en="EncodingAESKey configured for WeCom custom app callbacks, used for message encryption and decryption.",
            is_secret=True,
            category_zh="自建应用模式",
            category_en="Corp App Mode",
            required=True,
        ),
    )

    REQUEST_TIMEOUT_SECONDS: int = Field(
        default=10,
        title="请求超时",
        description="HTTP 请求与回调处理的超时时间（秒）",
        json_schema_extra=adapter_extra_field(
            title_zh="请求超时",
            title_en="Request Timeout",
            description_zh="HTTP 请求与回调处理的超时时间（秒）",
            description_en="Timeout for HTTP requests and callback handling, in seconds.",
            category_zh="通用",
            category_en="General",
        ),
    )

    TREAT_ALL_RECEIVED_MESSAGES_AS_TOME: bool = Field(
        default=True,
        title="所有收到的消息均触发 AI",
        description="开启后，所有自建应用回调收到的消息都会视为与机器人相关并进入触发判断",
        json_schema_extra=adapter_extra_field(
            title_zh="所有收到的消息均触发 AI",
            title_en="Treat All Received Messages as To-Me",
            description_zh="开启后，所有自建应用回调收到的消息都会视为与机器人相关并进入触发判断",
            description_en="When enabled, all messages received from custom app callbacks will be treated as related to the bot and enter trigger evaluation.",
            category_zh="通用",
            category_en="General",
        ),
    )

    ENABLE_TEXT_MESSAGE_COLLECTION: bool = Field(
        default=True,
        title="接入文本消息",
        description="开启后会将自建应用回调中的文本消息接入统一消息收集器",
        json_schema_extra=adapter_extra_field(
            title_zh="接入文本消息",
            title_en="Collect Text Messages",
            description_zh="开启后会将自建应用回调中的文本消息接入统一消息收集器",
            description_en="When enabled, text messages from custom app callbacks will be collected by the unified message collector.",
            category_zh="通用",
            category_en="General",
        ),
    )

    RAW_LOG_MAX_LENGTH: int = Field(
        default=12000,
        title="日志最大长度",
        description="回调原始内容日志最大长度，超过后自动截断",
        json_schema_extra=adapter_extra_field(
            title_zh="日志最大长度",
            title_en="Raw Log Max Length",
            description_zh="回调原始内容日志最大长度，超过后自动截断",
            description_en="Maximum length of raw callback content logs. Content beyond this length will be truncated automatically.",
            category_zh="通用",
            category_en="General",
        ),
    )
