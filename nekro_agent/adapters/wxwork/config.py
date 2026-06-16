from typing import Literal

from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text


class WxWorkConfig(BaseAdapterConfig):
    """企业微信 AI Bot 长连接适配器配置。"""

    BOT_ID: str = Field(
        default="",
        title="Bot ID",
        description="企业微信智能机器人后台获取的 Bot ID",
        json_schema_extra=ExtraField(
            is_secret=True,
            required=True,
            i18n_category=i18n_text(zh_CN="AI Bot 模式", en_US="AI Bot Mode"),
            i18n_title=i18n_text(zh_CN="Bot ID", en_US="Bot ID"),
            i18n_description=i18n_text(
                zh_CN="企业微信智能机器人后台获取的 Bot ID",
                en_US="Bot ID obtained from the WeCom AI Bot console.",
            ),
        ).model_dump(),
    )

    BOT_SECRET: str = Field(
        default="",
        title="Secret",
        description="企业微信智能机器人后台获取的 Secret",
        json_schema_extra=ExtraField(
            is_secret=True,
            required=True,
            i18n_category=i18n_text(zh_CN="AI Bot 模式", en_US="AI Bot Mode"),
            i18n_title=i18n_text(zh_CN="Secret", en_US="Secret"),
            i18n_description=i18n_text(
                zh_CN="企业微信智能机器人后台获取的 Secret",
                en_US="Secret obtained from the WeCom AI Bot console.",
            ),
        ).model_dump(),
    )

    USER_INFO_CORP_ID: str = Field(
        default="",
        title="User Info Corp ID",
        description="用于查询企业通讯录成员姓名的企业 ID（CorpID），可选；配置后可稳定将 userid 解析为用户名",
        json_schema_extra=ExtraField(
            placeholder="wwxxxxxxxxxxxxxxxx",
            i18n_category=i18n_text(zh_CN="用户名解析", en_US="User Name Resolution"),
            i18n_title=i18n_text(zh_CN="企业 ID", en_US="Enterprise Corp ID"),
            i18n_description=i18n_text(
                zh_CN="用于查询企业通讯录成员姓名的企业 ID（CorpID），可选；配置后可稳定将 userid 解析为用户名",
                en_US="Optional enterprise CorpID used to query member names from the directory. When configured, userid can be stably resolved to display names.",
            ),
        ).model_dump(),
    )

    USER_INFO_LOOKUP_MODE: Literal["direct", "proxy"] = Field(
        default="direct",
        title="User Info Lookup Mode",
        description="企业微信用户名查询模式。默认 direct 直连官方接口；配置为 proxy 时通过独立代理服务查询。若使用 proxy，则企业 ID 与自建应用 Secret 只需配置在代理服务端。",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="用户名解析", en_US="User Name Resolution"),
            i18n_title=i18n_text(zh_CN="用户名查询模式", en_US="User Name Lookup Mode"),
            i18n_description=i18n_text(
                zh_CN="企业微信用户名查询模式。默认 direct 直连官方接口；配置为 proxy 时通过独立代理服务查询。若使用 proxy，则企业 ID 与自建应用 Secret 只需配置在代理服务端。",
                en_US="WeCom user name lookup mode. Default is direct official API access; set to proxy to resolve names through a dedicated proxy service. In proxy mode, the enterprise CorpID and self-built app Secret only need to be configured on the proxy server.",
            ),
        ).model_dump(),
    )

    USER_INFO_APP_SECRET: str = Field(
        default="",
        title="User Info App Secret",
        description="具备通讯录读取权限的企业微信自建应用 Secret，可选；配置后可稳定将 userid 解析为用户名",
        json_schema_extra=ExtraField(
            is_secret=True,
            i18n_category=i18n_text(zh_CN="用户名解析", en_US="User Name Resolution"),
            i18n_title=i18n_text(zh_CN="自建应用 Secret", en_US="Corp App Secret"),
            i18n_description=i18n_text(
                zh_CN="具备通讯录读取权限的企业微信自建应用 Secret，可选；配置后可稳定将 userid 解析为用户名",
                en_US="Optional Secret of a self-built WeCom app with directory read permission. When configured, userid can be stably resolved to display names.",
            ),
        ).model_dump(),
    )

    USER_INFO_PROXY_URL: str = Field(
        default="",
        title="User Info Proxy URL",
        description="企业微信用户名查询代理地址，仅在 lookup mode=proxy 时使用，例如 https://example.com/api/wxwork/user/resolve",
        json_schema_extra=ExtraField(
            placeholder="https://example.com/api/wxwork/user/resolve",
            i18n_category=i18n_text(zh_CN="用户名解析", en_US="User Name Resolution"),
            i18n_title=i18n_text(zh_CN="用户名代理地址", en_US="User Name Proxy URL"),
            i18n_description=i18n_text(
                zh_CN="企业微信用户名查询代理地址，仅在 lookup mode=proxy 时使用，例如 https://example.com/api/wxwork/user/resolve",
                en_US="Proxy endpoint used for WeCom user name lookup when lookup mode=proxy, for example https://example.com/api/wxwork/user/resolve",
            ),
        ).model_dump(),
    )

    USER_INFO_PROXY_SHARED_SECRET: str = Field(
        default="",
        title="User Info Proxy Shared Secret",
        description="企业微信用户名查询代理共享密钥，仅在 lookup mode=proxy 时使用。本地实例与代理服务端需配置为相同值，用于 HMAC 签名鉴权。",
        json_schema_extra=ExtraField(
            is_secret=True,
            i18n_category=i18n_text(zh_CN="用户名解析", en_US="User Name Resolution"),
            i18n_title=i18n_text(zh_CN="用户名代理共享密钥", en_US="User Name Proxy Shared Secret"),
            i18n_description=i18n_text(
                zh_CN="企业微信用户名查询代理共享密钥，仅在 lookup mode=proxy 时使用。本地实例与代理服务端需配置为相同值，用于 HMAC 签名鉴权。",
                en_US="Shared secret used for WeCom user name proxy lookup when lookup mode=proxy. The local instance and proxy server must use the same value for HMAC signature authentication.",
            ),
        ).model_dump(),
    )

    USER_INFO_CACHE_TTL_SECONDS: int = Field(
        default=86400,
        title="User Info Cache TTL",
        description="企业微信用户名缓存时长（秒），包含本地内存缓存与失败后的短期退避",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="用户名解析", en_US="User Name Resolution"),
            i18n_title=i18n_text(zh_CN="用户名缓存时长", en_US="User Name Cache TTL"),
            i18n_description=i18n_text(
                zh_CN="企业微信用户名缓存时长（秒），包含本地内存缓存与失败后的短期退避",
                en_US="TTL for WeCom user name cache in seconds, including in-memory cache and short backoff after lookup failures.",
            ),
        ).model_dump(),
    )

    HEARTBEAT_INTERVAL_SECONDS: int = Field(
        default=30,
        title="心跳间隔",
        description="长连接心跳间隔（秒）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="心跳间隔", en_US="Heartbeat Interval"),
            i18n_description=i18n_text(
                zh_CN="长连接心跳间隔（秒）",
                en_US="Heartbeat interval of the long-lived connection, in seconds.",
            ),
        ).model_dump(),
    )

    REQUEST_TIMEOUT_SECONDS: int = Field(
        default=10,
        title="请求超时",
        description="长连接请求超时（秒），用于认证、发送消息和心跳等待",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="请求超时", en_US="Request Timeout"),
            i18n_description=i18n_text(
                zh_CN="长连接请求超时（秒），用于认证、发送消息和心跳等待",
                en_US="Request timeout of the long-lived connection, in seconds, used for authentication, message sending, and heartbeat waiting.",
            ),
        ).model_dump(),
    )

    RECONNECT_INTERVAL_SECONDS: int = Field(
        default=1,
        title="基础重连间隔",
        description="长连接断开后的基础重连间隔（秒），实际会按指数退避增长",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="基础重连间隔", en_US="Base Reconnect Interval"),
            i18n_description=i18n_text(
                zh_CN="长连接断开后的基础重连间隔（秒），实际会按指数退避增长",
                en_US="Base reconnect interval after the long-lived connection is disconnected, in seconds. Actual retries will use exponential backoff.",
            ),
        ).model_dump(),
    )

    MAX_RECONNECT_ATTEMPTS: int = Field(
        default=-1,
        title="最大重连次数",
        description="-1 表示无限重连，其余值表示最大重连尝试次数",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="最大重连次数", en_US="Max Reconnect Attempts"),
            i18n_description=i18n_text(
                zh_CN="-1 表示无限重连，其余值表示最大重连尝试次数",
                en_US="-1 means unlimited reconnect attempts. Any other value specifies the maximum number of reconnect attempts.",
            ),
        ).model_dump(),
    )

    TREAT_ALL_RECEIVED_MESSAGES_AS_TOME: bool = Field(
        default=True,
        title="所有收到的消息均触发 AI",
        description="开启后，所有企业微信长连接收到的消息都会视为与机器人相关并进入触发判断",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="所有收到的消息均触发 AI", en_US="Treat All Received Messages as To-Me"),
            i18n_description=i18n_text(
                zh_CN="开启后，所有企业微信长连接收到的消息都会视为与机器人相关并进入触发判断",
                en_US="When enabled, all messages received through the WeCom long-lived connection will be treated as related to the bot and enter trigger evaluation.",
            ),
        ).model_dump(),
    )

    ENABLE_TEXT_MESSAGE_COLLECTION: bool = Field(
        default=True,
        title="接入文本消息",
        description="开启后会将文本与语音转写消息接入统一消息收集器",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="接入文本消息", en_US="Collect Text Messages"),
            i18n_description=i18n_text(
                zh_CN="开启后会将文本与语音转写消息接入统一消息收集器",
                en_US="When enabled, text messages and voice transcription messages will be collected by the unified message collector.",
            ),
        ).model_dump(),
    )

    INBOUND_IMAGE_TARGET_MAX_KB: int = Field(
        default=180,
        title="入站图片目标大小",
        description="企业微信入站图片归一化后的目标体积上限（KB），超过后会尝试压缩或缩放",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="媒体处理", en_US="Media Processing"),
            i18n_title=i18n_text(zh_CN="入站图片目标大小", en_US="Inbound Image Target Size"),
            i18n_description=i18n_text(
                zh_CN="企业微信入站图片归一化后的目标体积上限（KB），超过后会尝试压缩或缩放",
                en_US="Target size limit in KB for normalized inbound WeCom images. Images exceeding it will be compressed or scaled down.",
            ),
        ).model_dump(),
    )

    INBOUND_IMAGE_MIN_QUALITY: int = Field(
        default=45,
        title="入站图片最低质量",
        description="企业微信入站图片 JPEG 压缩时允许降到的最低质量",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="媒体处理", en_US="Media Processing"),
            i18n_title=i18n_text(zh_CN="入站图片最低质量", en_US="Inbound Image Min Quality"),
            i18n_description=i18n_text(
                zh_CN="企业微信入站图片 JPEG 压缩时允许降到的最低质量",
                en_US="Lowest JPEG quality allowed when compressing inbound WeCom images.",
            ),
        ).model_dump(),
    )

    INBOUND_IMAGE_INITIAL_QUALITY: int = Field(
        default=85,
        title="入站图片初始质量",
        description="企业微信入站图片 JPEG 压缩时的起始质量",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="媒体处理", en_US="Media Processing"),
            i18n_title=i18n_text(zh_CN="入站图片初始质量", en_US="Inbound Image Initial Quality"),
            i18n_description=i18n_text(
                zh_CN="企业微信入站图片 JPEG 压缩时的起始质量",
                en_US="Starting JPEG quality used when compressing inbound WeCom images.",
            ),
        ).model_dump(),
    )

    INBOUND_IMAGE_MIN_EDGE: int = Field(
        default=320,
        title="入站图片最短边下限",
        description="企业微信入站图片缩放时允许保留的最短边像素下限",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="媒体处理", en_US="Media Processing"),
            i18n_title=i18n_text(zh_CN="入站图片最短边下限", en_US="Inbound Image Min Edge"),
            i18n_description=i18n_text(
                zh_CN="企业微信入站图片缩放时允许保留的最短边像素下限",
                en_US="Minimum allowed shorter edge in pixels when scaling inbound WeCom images.",
            ),
        ).model_dump(),
    )

    ENABLE_EVENT_LOGGING: bool = Field(
        default=True,
        title="记录事件回调",
        description="开启后会在日志中记录进入会话、反馈等事件回调原始数据",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="记录事件回调", en_US="Log Event Callbacks"),
            i18n_description=i18n_text(
                zh_CN="开启后会在日志中记录进入会话、反馈等事件回调原始数据",
                en_US="When enabled, raw event callback data such as session entry and feedback events will be recorded in logs.",
            ),
        ).model_dump(),
    )

    LOG_RAW_WS_FRAMES: bool = Field(
        default=True,
        title="记录原始帧",
        description="开启后会在日志中记录企业微信长连接收到的原始 WebSocket 帧，便于补齐字段映射",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="记录原始帧", en_US="Log Raw Frames"),
            i18n_description=i18n_text(
                zh_CN="开启后会在日志中记录企业微信长连接收到的原始 WebSocket 帧，便于补齐字段映射",
                en_US="When enabled, raw WebSocket frames received from the WeCom long-lived connection will be recorded in logs to help complete field mappings.",
            ),
        ).model_dump(),
    )

    RAW_LOG_MAX_LENGTH: int = Field(
        default=12000,
        title="日志最大长度",
        description="原始帧日志最大长度，超过后自动截断",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
            i18n_title=i18n_text(zh_CN="日志最大长度", en_US="Raw Log Max Length"),
            i18n_description=i18n_text(
                zh_CN="原始帧日志最大长度，超过后自动截断",
                en_US="Maximum length of raw frame logs. Content beyond this length will be truncated automatically.",
            ),
        ).model_dump(),
    )
