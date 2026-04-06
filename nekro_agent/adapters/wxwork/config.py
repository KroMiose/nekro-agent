from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig, adapter_extra_field


class WxWorkConfig(BaseAdapterConfig):
    """企业微信 AI Bot 长连接适配器配置。"""

    BOT_ID: str = Field(
        default="",
        title="Bot ID",
        description="企业微信智能机器人后台获取的 Bot ID",
        json_schema_extra=adapter_extra_field(
            title_zh="Bot ID",
            title_en="Bot ID",
            description_zh="企业微信智能机器人后台获取的 Bot ID",
            description_en="Bot ID obtained from the WeCom AI Bot console.",
            is_secret=True,
            category_zh="AI Bot 模式",
            category_en="AI Bot Mode",
            required=True,
        ),
    )

    BOT_SECRET: str = Field(
        default="",
        title="Secret",
        description="企业微信智能机器人后台获取的 Secret",
        json_schema_extra=adapter_extra_field(
            title_zh="Secret",
            title_en="Secret",
            description_zh="企业微信智能机器人后台获取的 Secret",
            description_en="Secret obtained from the WeCom AI Bot console.",
            is_secret=True,
            category_zh="AI Bot 模式",
            category_en="AI Bot Mode",
            required=True,
        ),
    )

    HEARTBEAT_INTERVAL_SECONDS: int = Field(
        default=30,
        title="心跳间隔",
        description="长连接心跳间隔（秒）",
        json_schema_extra=adapter_extra_field(
            title_zh="心跳间隔",
            title_en="Heartbeat Interval",
            description_zh="长连接心跳间隔（秒）",
            description_en="Heartbeat interval of the long-lived connection, in seconds.",
            category_zh="通用",
            category_en="General",
        ),
    )

    REQUEST_TIMEOUT_SECONDS: int = Field(
        default=10,
        title="请求超时",
        description="长连接请求超时（秒），用于认证、发送消息和心跳等待",
        json_schema_extra=adapter_extra_field(
            title_zh="请求超时",
            title_en="Request Timeout",
            description_zh="长连接请求超时（秒），用于认证、发送消息和心跳等待",
            description_en="Request timeout of the long-lived connection, in seconds, used for authentication, message sending, and heartbeat waiting.",
            category_zh="通用",
            category_en="General",
        ),
    )

    RECONNECT_INTERVAL_SECONDS: int = Field(
        default=1,
        title="基础重连间隔",
        description="长连接断开后的基础重连间隔（秒），实际会按指数退避增长",
        json_schema_extra=adapter_extra_field(
            title_zh="基础重连间隔",
            title_en="Base Reconnect Interval",
            description_zh="长连接断开后的基础重连间隔（秒），实际会按指数退避增长",
            description_en="Base reconnect interval after the long-lived connection is disconnected, in seconds. Actual retries will use exponential backoff.",
            category_zh="通用",
            category_en="General",
        ),
    )

    MAX_RECONNECT_ATTEMPTS: int = Field(
        default=-1,
        title="最大重连次数",
        description="-1 表示无限重连，其余值表示最大重连尝试次数",
        json_schema_extra=adapter_extra_field(
            title_zh="最大重连次数",
            title_en="Max Reconnect Attempts",
            description_zh="-1 表示无限重连，其余值表示最大重连尝试次数",
            description_en="-1 means unlimited reconnect attempts. Any other value specifies the maximum number of reconnect attempts.",
            category_zh="通用",
            category_en="General",
        ),
    )

    TREAT_ALL_RECEIVED_MESSAGES_AS_TOME: bool = Field(
        default=True,
        title="所有收到的消息均触发 AI",
        description="开启后，所有企业微信长连接收到的消息都会视为与机器人相关并进入触发判断",
        json_schema_extra=adapter_extra_field(
            title_zh="所有收到的消息均触发 AI",
            title_en="Treat All Received Messages as To-Me",
            description_zh="开启后，所有企业微信长连接收到的消息都会视为与机器人相关并进入触发判断",
            description_en="When enabled, all messages received through the WeCom long-lived connection will be treated as related to the bot and enter trigger evaluation.",
            category_zh="通用",
            category_en="General",
        ),
    )

    ENABLE_TEXT_MESSAGE_COLLECTION: bool = Field(
        default=True,
        title="接入文本消息",
        description="开启后会将文本与语音转写消息接入统一消息收集器",
        json_schema_extra=adapter_extra_field(
            title_zh="接入文本消息",
            title_en="Collect Text Messages",
            description_zh="开启后会将文本与语音转写消息接入统一消息收集器",
            description_en="When enabled, text messages and voice transcription messages will be collected by the unified message collector.",
            category_zh="通用",
            category_en="General",
        ),
    )

    ENABLE_EVENT_LOGGING: bool = Field(
        default=True,
        title="记录事件回调",
        description="开启后会在日志中记录进入会话、反馈等事件回调原始数据",
        json_schema_extra=adapter_extra_field(
            title_zh="记录事件回调",
            title_en="Log Event Callbacks",
            description_zh="开启后会在日志中记录进入会话、反馈等事件回调原始数据",
            description_en="When enabled, raw event callback data such as session entry and feedback events will be recorded in logs.",
            category_zh="通用",
            category_en="General",
        ),
    )

    LOG_RAW_WS_FRAMES: bool = Field(
        default=True,
        title="记录原始帧",
        description="开启后会在日志中记录企业微信长连接收到的原始 WebSocket 帧，便于补齐字段映射",
        json_schema_extra=adapter_extra_field(
            title_zh="记录原始帧",
            title_en="Log Raw Frames",
            description_zh="开启后会在日志中记录企业微信长连接收到的原始 WebSocket 帧，便于补齐字段映射",
            description_en="When enabled, raw WebSocket frames received from the WeCom long-lived connection will be recorded in logs to help complete field mappings.",
            category_zh="通用",
            category_en="General",
        ),
    )

    RAW_LOG_MAX_LENGTH: int = Field(
        default=12000,
        title="日志最大长度",
        description="原始帧日志最大长度，超过后自动截断",
        json_schema_extra=adapter_extra_field(
            title_zh="日志最大长度",
            title_en="Raw Log Max Length",
            description_zh="原始帧日志最大长度，超过后自动截断",
            description_en="Maximum length of raw frame logs. Content beyond this length will be truncated automatically.",
            category_zh="通用",
            category_en="General",
        ),
    )
