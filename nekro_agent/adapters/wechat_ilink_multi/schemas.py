from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OpenILinkSchema(BaseModel):
    """OpenILink 协议模型基类。"""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class BindStatus(str, Enum):
    PENDING = "pending"
    SCANNED = "scanned"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    FAILED = "failed"


class RecipientKind(str, Enum):
    USER = "user"
    GROUP = "group"


class MediaKind(str, Enum):
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"


class BindStartResult(OpenILinkSchema):
    session_id: str = Field(..., description="绑定会话 ID")
    qr_url: str = Field(..., description="绑定二维码或授权 URL")
    expires_at: datetime = Field(..., description="绑定会话过期时间")


class OpenILinkCredentials(OpenILinkSchema):
    provider_account_id: str = Field(..., description="OpenILink 侧账号 ID")
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str | None = Field(default=None, description="刷新令牌")
    expires_at: datetime | None = Field(default=None, description="访问令牌过期时间")
    device_id: str | None = Field(default=None, description="绑定设备 ID")
    scope: list[str] = Field(default_factory=list, description="授权范围")


class BindPollResult(OpenILinkSchema):
    status: BindStatus = Field(..., description="绑定状态")
    credentials: OpenILinkCredentials | None = Field(default=None, description="绑定成功后的凭据")
    provider_account_id: str | None = Field(default=None, description="OpenILink 侧账号 ID")
    error_message: str | None = Field(default=None, description="失败原因")


class SyncState(OpenILinkSchema):
    cursor: str | None = Field(default=None, description="增量同步游标")
    sequence: int | None = Field(default=None, description="同步序列号")
    last_sync_at: datetime | None = Field(default=None, description="最近同步时间")
    watermark: str | None = Field(default=None, description="服务端水位标记")


class OpenILinkRecipient(OpenILinkSchema):
    kind: RecipientKind = Field(..., description="接收者类型")
    id: str = Field(..., description="接收者 OpenILink ID")
    display_name: str | None = Field(default=None, description="展示名称")


class ContextToken(OpenILinkSchema):
    conversation_id: str = Field(..., description="会话 ID")
    message_id: str | None = Field(default=None, description="用于回复或引用的消息 ID")
    sync_cursor: str | None = Field(default=None, description="消息对应的同步游标")


class OpenILinkMedia(OpenILinkSchema):
    media_id: str = Field(..., description="媒体 ID")
    kind: MediaKind = Field(..., description="媒体类型")
    url: str | None = Field(default=None, description="临时下载 URL")
    file_name: str | None = Field(default=None, description="文件名")
    mime_type: str | None = Field(default=None, description="MIME 类型")
    size_bytes: int | None = Field(default=None, description="文件大小")
    checksum: str | None = Field(default=None, description="内容校验值")


class OpenILinkMessage(OpenILinkSchema):
    message_id: str = Field(..., description="OpenILink 消息 ID")
    sender_id: str = Field(..., description="发送者 ID")
    recipient: OpenILinkRecipient = Field(..., description="消息所属会话或接收者")
    timestamp: datetime = Field(..., description="消息时间")
    text: str | None = Field(default=None, description="文本内容")
    media: list[OpenILinkMedia] = Field(default_factory=list, description="媒体内容")
    context_token: ContextToken = Field(..., description="发送回复所需上下文")
    raw_type: str | None = Field(default=None, description="OpenILink 原始消息类型")
    raw: dict[str, Any] = Field(default_factory=dict, description="原始消息字典（用于媒体下载）")


class SendMessageResult(OpenILinkSchema):
    message_id: str = Field(..., description="发送后获得的消息 ID")
    accepted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="服务端接受时间")


class RenewResult(OpenILinkSchema):
    credentials: OpenILinkCredentials = Field(..., description="续期后的凭据")
    sync_state: SyncState = Field(..., description="续期后的同步状态")
    renew_at: datetime | None = Field(default=None, description="建议下次续期时间")


def parse_bind_start_payload(payload: Mapping[str, object]) -> BindStartResult:
    return BindStartResult(
        session_id=_require_str(payload, "session_id"),
        qr_url=_require_str(payload, "qr_url"),
        expires_at=_require_datetime(payload, "expires_at"),
    )


def parse_bind_poll_payload(payload: Mapping[str, object]) -> BindPollResult:
    credentials_payload = _optional_mapping(payload, "credentials")
    credentials = parse_credentials_payload(credentials_payload) if credentials_payload is not None else None
    provider_account_id = _optional_str(payload, "provider_account_id")
    return BindPollResult(
        status=BindStatus(_require_str(payload, "status")),
        credentials=credentials,
        provider_account_id=provider_account_id or (credentials.provider_account_id if credentials else None),
        error_message=_optional_str(payload, "error_message"),
    )


def parse_credentials_payload(payload: Mapping[str, object]) -> OpenILinkCredentials:
    return OpenILinkCredentials(
        provider_account_id=_require_str(payload, "provider_account_id"),
        access_token=_require_str(payload, "access_token"),
        refresh_token=_optional_str(payload, "refresh_token"),
        expires_at=_optional_datetime(payload, "expires_at"),
        device_id=_optional_str(payload, "device_id"),
        scope=_optional_str_list(payload, "scope"),
    )


def parse_sync_state_payload(payload: Mapping[str, object]) -> SyncState:
    return SyncState(
        cursor=_optional_str(payload, "cursor"),
        sequence=_optional_int(payload, "sequence"),
        last_sync_at=_optional_datetime(payload, "last_sync_at"),
        watermark=_optional_str(payload, "watermark"),
    )


def parse_media_payload(payload: Mapping[str, object]) -> OpenILinkMedia:
    return OpenILinkMedia(
        media_id=_require_str(payload, "media_id"),
        kind=MediaKind(_require_str(payload, "kind")),
        url=_optional_str(payload, "url"),
        file_name=_optional_str(payload, "file_name"),
        mime_type=_optional_str(payload, "mime_type"),
        size_bytes=_optional_int(payload, "size_bytes"),
        checksum=_optional_str(payload, "checksum"),
    )


def parse_message_payload(payload: Mapping[str, object]) -> OpenILinkMessage:
    media_payloads = _optional_mapping_list(payload, "media")
    return OpenILinkMessage(
        message_id=_require_str(payload, "message_id"),
        sender_id=_require_str(payload, "sender_id"),
        recipient=parse_recipient_payload(_require_mapping(payload, "recipient")),
        timestamp=_require_datetime(payload, "timestamp"),
        text=_optional_str(payload, "text"),
        media=[parse_media_payload(item) for item in media_payloads],
        context_token=parse_context_token_payload(_require_mapping(payload, "context_token")),
        raw_type=_optional_str(payload, "raw_type"),
    )


def parse_recipient_payload(payload: Mapping[str, object]) -> OpenILinkRecipient:
    return OpenILinkRecipient(
        kind=RecipientKind(_require_str(payload, "kind")),
        id=_require_str(payload, "id"),
        display_name=_optional_str(payload, "display_name"),
    )


def parse_context_token_payload(payload: Mapping[str, object]) -> ContextToken:
    return ContextToken(
        conversation_id=_require_str(payload, "conversation_id"),
        message_id=_optional_str(payload, "message_id"),
        sync_cursor=_optional_str(payload, "sync_cursor"),
    )


def parse_renew_payload(payload: Mapping[str, object]) -> RenewResult:
    return RenewResult(
        credentials=parse_credentials_payload(_require_mapping(payload, "credentials")),
        sync_state=parse_sync_state_payload(_require_mapping(payload, "sync_state")),
        renew_at=_optional_datetime(payload, "renew_at"),
    )


def _require_str(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"OpenILink payload missing non-empty string field: {key}")


def _optional_str(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value or None
    raise ValueError(f"OpenILink payload field must be a string: {key}")


def _optional_int(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, int):
        return value
    raise ValueError(f"OpenILink payload field must be an integer: {key}")


def _require_datetime(payload: Mapping[str, object], key: str) -> datetime:
    value = _optional_datetime(payload, key)
    if value is None:
        raise ValueError(f"OpenILink payload missing datetime field: {key}")
    return value


def _optional_datetime(payload: Mapping[str, object], key: str) -> datetime | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    raise ValueError(f"OpenILink payload field must be datetime-compatible: {key}")


def _require_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = _optional_mapping(payload, key)
    if value is None:
        raise ValueError(f"OpenILink payload missing object field: {key}")
    return value


def _optional_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, Mapping):
        return _normalize_mapping(value)
    raise ValueError(f"OpenILink payload field must be an object: {key}")


def _optional_mapping_list(payload: Mapping[str, object], key: str) -> list[Mapping[str, object]]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(f"OpenILink payload field must be an object list: {key}")
    return [_normalize_mapping(item) for item in value]


def _optional_str_list(payload: Mapping[str, object], key: str) -> list[str]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(f"OpenILink payload field must be a string list: {key}")

    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"OpenILink payload field must contain only strings: {key}")
        result.append(item)
    return result


def _normalize_mapping(value: Mapping[Any, Any]) -> Mapping[str, object]:
    normalized: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError("OpenILink payload object keys must be strings")
        normalized[key] = item
    return normalized


# ============================================================
# Management API Schemas
# ============================================================


class InstanceCreateRequest(OpenILinkSchema):
    """创建实例请求"""

    instance_key: str = Field(..., description="实例唯一标识")
    display_name: str = Field(default="", description="实例显示名称")
    provider: str = Field(default="", description="服务提供方")


class InstanceCreateResponse(OpenILinkSchema):
    """创建实例响应"""

    instance_key: str = Field(..., description="实例唯一标识")
    status: str = Field(default="pending", description="实例状态")
    renew_before_minutes: int = Field(default=60, description="提前续期分钟数")
    created_at: datetime = Field(..., description="创建时间")
    existing: bool = Field(default=False, description="是否为已存在实例")


class InstanceDetailResponse(OpenILinkSchema):
    """实例详情响应（不含凭据信息）"""

    instance_key: str = Field(..., description="实例唯一标识")
    display_name: str = Field(..., description="实例显示名称")
    status: str = Field(..., description="实例状态")
    enabled: bool = Field(..., description="是否启用")
    is_default: bool = Field(..., description="是否默认实例")
    provider: str = Field(..., description="服务提供方")
    provider_account_id: str = Field(..., description="服务提供方账号标识")
    metadata_json: str = Field(default="", description="实例元数据(JSON)")
    last_error: str | None = Field(default=None, description="最近错误信息")
    last_active_at: datetime | None = Field(default=None, description="最近活跃时间")
    next_renew_at: datetime | None = Field(default=None, description="下次续期时间")
    renew_before_minutes: int = Field(..., description="提前续期分钟数")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="更新时间")


class InstanceListResponse(OpenILinkSchema):
    """实例列表响应"""

    instances: list[InstanceDetailResponse] = Field(..., description="实例列表")


class BindStartResponse(OpenILinkSchema):
    """开始绑定响应"""

    bind_session_id: str = Field(..., description="绑定会话 ID")
    qr_url: str = Field(..., description="绑定二维码或授权 URL")
    status: str = Field(default="ok", description="操作状态")
    bind_status: str = Field(..., description="绑定子状态")
    expires_at: datetime = Field(..., description="绑定会话过期时间")


class BindStatusResponse(OpenILinkSchema):
    """绑定状态响应"""

    status: str = Field(..., description="操作状态")
    instance_status: str = Field(default="", description="实例主生命周期状态")
    bind_status: str = Field(..., description="绑定子状态")
    message: str | None = Field(default=None, description="提示信息")


class EventResponse(OpenILinkSchema):
    """事件记录响应"""

    event_type: str = Field(..., description="事件类型")
    status_from: str | None = Field(default=None, description="状态变更前")
    status_to: str | None = Field(default=None, description="状态变更后")
    message: str | None = Field(default=None, description="事件消息")
    create_time: datetime = Field(..., description="事件发生时间")


class RenewPolicyRequest(OpenILinkSchema):
    """更新续期策略请求"""

    renew_before_minutes: int = Field(..., ge=1, description="提前续期分钟数（分钟）")
