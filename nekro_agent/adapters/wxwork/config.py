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
            i18n_category=i18n_text(zh_CN="AI Bot 模式", en_US="AI Bot Mode"),
        ).model_dump(),
    )

    BOT_SECRET: str = Field(
        default="",
        title="Secret",
        description="企业微信智能机器人后台获取的 Secret",
        json_schema_extra=ExtraField(
            is_secret=True,
            i18n_category=i18n_text(zh_CN="AI Bot 模式", en_US="AI Bot Mode"),
        ).model_dump(),
    )

    HEARTBEAT_INTERVAL_SECONDS: int = Field(
        default=30,
        title="心跳间隔",
        description="长连接心跳间隔（秒）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
        ).model_dump(),
    )

    REQUEST_TIMEOUT_SECONDS: int = Field(
        default=10,
        title="请求超时",
        description="长连接请求超时（秒），用于认证、发送消息和心跳等待",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
        ).model_dump(),
    )

    RECONNECT_INTERVAL_SECONDS: int = Field(
        default=1,
        title="基础重连间隔",
        description="长连接断开后的基础重连间隔（秒），实际会按指数退避增长",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
        ).model_dump(),
    )

    MAX_RECONNECT_ATTEMPTS: int = Field(
        default=-1,
        title="最大重连次数",
        description="-1 表示无限重连，其余值表示最大重连尝试次数",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
        ).model_dump(),
    )

    TREAT_ALL_RECEIVED_MESSAGES_AS_TOME: bool = Field(
        default=True,
        title="所有收到的消息均触发 AI",
        description="开启后，所有企业微信长连接收到的消息都会视为与机器人相关并进入触发判断",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
        ).model_dump(),
    )

    ENABLE_TEXT_MESSAGE_COLLECTION: bool = Field(
        default=True,
        title="接入文本消息",
        description="开启后会将文本与语音转写消息接入统一消息收集器",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
        ).model_dump(),
    )

    ENABLE_EVENT_LOGGING: bool = Field(
        default=True,
        title="记录事件回调",
        description="开启后会在日志中记录进入会话、反馈等事件回调原始数据",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
        ).model_dump(),
    )

    LOG_RAW_WS_FRAMES: bool = Field(
        default=True,
        title="记录原始帧",
        description="开启后会在日志中记录企业微信长连接收到的原始 WebSocket 帧，便于补齐字段映射",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
        ).model_dump(),
    )

    RAW_LOG_MAX_LENGTH: int = Field(
        default=12000,
        title="日志最大长度",
        description="原始帧日志最大长度，超过后自动截断",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通用", en_US="General"),
        ).model_dump(),
    )
