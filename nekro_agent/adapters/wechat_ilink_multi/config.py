from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text


class WeChatILinkMultiConfig(BaseAdapterConfig):
    """微信 OpenILink 多实例适配器配置。"""

    ENABLED: bool = Field(
        default=False,
        title="启用 OpenILink 多实例适配器",
        description="是否启用微信 OpenILink 多实例适配器。默认关闭，等待具体协议实现接入。",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="OpenILink 多实例", en_US="OpenILink Multi"),
            i18n_title=i18n_text(zh_CN="启用适配器", en_US="Enable Adapter"),
            i18n_description=i18n_text(
                zh_CN="是否启用微信 OpenILink 多实例适配器。默认关闭，等待具体协议实现接入。",
                en_US="Whether to enable the WeChat OpenILink multi-instance adapter. Disabled by default until a concrete protocol transport is wired.",
            ),
        ).model_dump(),
    )

    API_BASE_URL: str = Field(
        default="https://ilinkai.weixin.qq.com",
        title="OpenILink API 地址",
        description="OpenILink 协议服务基础地址，不包含具体资源路径。",
        json_schema_extra=ExtraField(
            placeholder="https://ilinkai.weixin.qq.com",
            i18n_category=i18n_text(zh_CN="OpenILink 多实例", en_US="OpenILink Multi"),
            i18n_title=i18n_text(zh_CN="API 地址", en_US="API Base URL"),
            i18n_description=i18n_text(
                zh_CN="OpenILink 协议服务基础地址，不包含具体资源路径。",
                en_US="Base URL for the OpenILink protocol service, without concrete resource paths.",
            ),
        ).model_dump(),
    )

    DEFAULT_RENEW_BEFORE_MINUTES: int = Field(
        default=60,
        title="默认续期提前量（分钟）",
        description="会话凭据过期前多少分钟触发默认续期。",
        json_schema_extra=ExtraField(
            placeholder="60",
            i18n_category=i18n_text(zh_CN="会话", en_US="Session"),
            i18n_title=i18n_text(zh_CN="默认续期提前量", en_US="Default Renew Lead Time"),
            i18n_description=i18n_text(
                zh_CN="会话凭据过期前多少分钟触发默认续期。",
                en_US="How many minutes before credential expiry the default renewal should be triggered.",
            ),
        ).model_dump(),
    )

    BIND_TIMEOUT_SECONDS: int = Field(
        default=180,
        title="绑定超时（秒）",
        description="二维码或外部绑定流程等待完成的最长时间。",
        json_schema_extra=ExtraField(
            placeholder="180",
            i18n_category=i18n_text(zh_CN="绑定", en_US="Binding"),
            i18n_title=i18n_text(zh_CN="绑定超时", en_US="Bind Timeout"),
            i18n_description=i18n_text(
                zh_CN="二维码或外部绑定流程等待完成的最长时间。",
                en_US="Maximum wait time for QR-code or external binding flow completion.",
            ),
        ).model_dump(),
    )

    DEDUP_WINDOW_SECONDS: int = Field(
        default=120,
        title="消息去重窗口（秒）",
        description="入站消息按 provider 消息 ID 去重的时间窗口。",
        json_schema_extra=ExtraField(
            placeholder="120",
            i18n_category=i18n_text(zh_CN="消息", en_US="Messages"),
            i18n_title=i18n_text(zh_CN="消息去重窗口", en_US="Dedup Window"),
            i18n_description=i18n_text(
                zh_CN="入站消息按 provider 消息 ID 去重的时间窗口。",
                en_US="Time window for deduplicating inbound messages by provider message ID.",
            ),
        ).model_dump(),
    )

    MEDIA_DOWNLOAD_MAX_BYTES: int = Field(
        default=20 * 1024 * 1024,
        title="媒体下载大小上限（字节）",
        description="单个媒体文件允许下载的最大字节数。",
        json_schema_extra=ExtraField(
            placeholder="20971520",
            i18n_category=i18n_text(zh_CN="媒体", en_US="Media"),
            i18n_title=i18n_text(zh_CN="媒体下载大小上限", en_US="Media Download Limit"),
            i18n_description=i18n_text(
                zh_CN="单个媒体文件允许下载的最大字节数。",
                en_US="Maximum allowed bytes for a single media download.",
            ),
        ).model_dump(),
    )

    MEDIA_DOWNLOAD_TIMEOUT_SECONDS: int = Field(
        default=60,
        title="媒体下载超时（秒）",
        description="单个媒体文件下载的超时时间。",
        json_schema_extra=ExtraField(
            placeholder="60",
            i18n_category=i18n_text(zh_CN="媒体", en_US="Media"),
            i18n_title=i18n_text(zh_CN="媒体下载超时", en_US="Media Download Timeout"),
            i18n_description=i18n_text(
                zh_CN="单个媒体文件下载的超时时间。",
                en_US="Timeout in seconds for downloading a single media item.",
            ),
        ).model_dump(),
    )
