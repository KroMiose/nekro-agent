import shutil
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from pydantic import BaseModel, Field
from tortoise.expressions import Q

from nekro_agent.adapters.interface.collector import collect_message
from nekro_agent.adapters.interface.schemas.platform import PlatformChannel, PlatformMessage, PlatformUser
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import SANDBOX_SHARED_HOST_DIR, USER_UPLOAD_DIR
from nekro_agent.models.db_chat_channel import ChannelStatus, DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_mem_episode import DBMemEpisode
from nekro_agent.models.db_mem_paragraph import DBMemParagraph
from nekro_agent.models.db_plugin_data import DBPluginData
from nekro_agent.models.db_recurring_timer_job import DBRecurringTimerJob
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)
from nekro_agent.schemas.errors import NotFoundError, ValidationError
from nekro_agent.services.mcp.web_chat_auth import (
    WEB_CHAT_MCP_URL,
    clear_external_web_chat_mcp_token,
    generate_external_web_chat_mcp_token,
    get_external_web_chat_mcp_status,
    save_external_web_chat_mcp_token,
)
from nekro_agent.services.channel_broadcaster import channel_broadcaster
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.tools.path_convertor import sanitize_chat_key_for_path

if TYPE_CHECKING:
    from .adapter import WebAdapter

router = APIRouter()
_adapter: Optional["WebAdapter"] = None
logger = get_sub_logger("adapter.web.router")

WEB_ADAPTER_KEY = "web"
DEFAULT_SESSION_NAME = "网页测试会话"


def set_adapter(adapter: "WebAdapter") -> None:
    global _adapter
    _adapter = adapter


def _get_adapter() -> "WebAdapter":
    if _adapter is None:
        raise ValidationError(reason="Web Adapter 未加载")
    return _adapter


class WebSessionItem(BaseModel):
    chat_key: str
    channel_id: str
    channel_name: Optional[str]
    custom_channel_name: Optional[str]
    status: str
    message_count: int
    update_time: str


class WebSessionLimits(BaseModel):
    message_max_length: int
    file_upload_max_size_mb: int


class WebSessionListResponse(BaseModel):
    total: int
    items: List[WebSessionItem]
    limits: WebSessionLimits


class WebSessionCreateRequest(BaseModel):
    name: str = Field(default="", max_length=64)


class WebSessionResponse(BaseModel):
    chat_key: str
    channel_id: str
    channel_name: str
    status: str


class WebMessageCreateRequest(BaseModel):
    content: str


class WebSessionUpdateRequest(BaseModel):
    name: str = Field(default="", max_length=64)


class WebMessageCreateResponse(BaseModel):
    ok: bool = True
    chat_key: str
    message_id: str


class WebActionResponse(BaseModel):
    ok: bool = True


class WebMcpExternalAuthStatus(BaseModel):
    enabled: bool
    configured: bool
    token_preview: Optional[str] = None
    updated_at: Optional[str] = None


class WebMcpAuthStatusResponse(BaseModel):
    ok: bool = True
    mcp_url: str
    external: WebMcpExternalAuthStatus


class WebMcpExternalAuthUpdateRequest(BaseModel):
    enabled: bool
    token: Optional[str] = Field(default=None, max_length=512)


class WebMcpExternalAuthGenerateResponse(WebMcpAuthStatusResponse):
    token: str


async def _get_session_sort_time(channel: DBChatChannel) -> tuple[int, float]:
    last_message = await DBChatMessage.filter(chat_key=channel.chat_key).order_by("-create_time").first()
    last_time = last_message.create_time if last_message else channel.update_time
    return channel.id, last_time.timestamp()


async def _to_session_item(channel: DBChatChannel) -> WebSessionItem:
    message_count = await DBChatMessage.filter(chat_key=channel.chat_key).count()
    last_message = await DBChatMessage.filter(chat_key=channel.chat_key).order_by("-create_time").first()
    display_time = last_message.create_time if last_message else channel.update_time
    return WebSessionItem(
        chat_key=channel.chat_key,
        channel_id=channel.channel_id,
        channel_name=channel.channel_name,
        custom_channel_name=channel.get_custom_channel_name(),
        status=channel.channel_status.value,
        message_count=message_count,
        update_time=display_time.strftime("%Y-%m-%d %H:%M:%S"),
    )


def _get_session_limits(adapter: "WebAdapter") -> WebSessionLimits:
    return WebSessionLimits(
        message_max_length=adapter.config.MESSAGE_MAX_LENGTH,
        file_upload_max_size_mb=adapter.config.FILE_UPLOAD_MAX_SIZE_MB,
    )


def _build_mcp_auth_status() -> WebMcpAuthStatusResponse:
    return WebMcpAuthStatusResponse(
        mcp_url=WEB_CHAT_MCP_URL,
        external=WebMcpExternalAuthStatus(**get_external_web_chat_mcp_status()),
    )


async def _get_web_channel(chat_key: str) -> DBChatChannel:
    channel = await DBChatChannel.filter(chat_key=chat_key).first()
    if channel is None or channel.adapter_key != WEB_ADAPTER_KEY:
        raise NotFoundError(resource="网页聊天会话")
    return channel


def _build_platform_user(current_user: DBUser, adapter: "WebAdapter") -> PlatformUser:
    fallback_username = f"web_user_{current_user.id}"
    try:
        platform_username = adapter.config.WEB_USER_NAME_TEMPLATE.format(
            id=current_user.id,
            username=current_user.username,
        ).strip()
    except (KeyError, IndexError, ValueError):
        platform_username = fallback_username
    if not platform_username or platform_username == "admin":
        platform_username = fallback_username

    return PlatformUser(
        platform_name="Web",
        user_id=f"admin_{current_user.id}",
        user_name=platform_username,
        user_avatar="",
    )


def _build_platform_channel(channel: DBChatChannel) -> PlatformChannel:
    return PlatformChannel(
        channel_id=channel.channel_id,
        channel_name=channel.channel_name or DEFAULT_SESSION_NAME,
        channel_type=ChatType.PRIVATE,
        channel_avatar="",
    )


def _is_writable_dir(path: Path) -> bool:
    test_path = path / f".write_test_{uuid4().hex}"
    try:
        test_path.write_bytes(b"")
        test_path.unlink(missing_ok=True)
        return True
    except OSError:
        try:
            test_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _ensure_upload_dir(chat_key: str, *, require_writable: bool = True) -> Path:
    safe_chat_key = sanitize_chat_key_for_path(chat_key)
    upload_dir = Path(USER_UPLOAD_DIR) / safe_chat_key
    upload_dir.mkdir(parents=True, exist_ok=True)
    try:
        upload_dir.chmod(0o755)
    except OSError:
        pass

    if _is_writable_dir(upload_dir):
        return upload_dir

    try:
        if not any(upload_dir.iterdir()):
            upload_dir.rmdir()
            upload_dir.mkdir(parents=True, exist_ok=True)
            upload_dir.chmod(0o755)
    except OSError as exc:
        raise ValidationError(reason="上传目录不可写，请检查运行用户与 uploads 目录权限") from exc

    if not _is_writable_dir(upload_dir) and require_writable:
        raise ValidationError(reason="上传目录不可写，请检查运行用户与 uploads 目录权限")

    return upload_dir


async def _save_upload_file(chat_key: str, file: UploadFile, max_size_mb: int) -> tuple[str, str]:
    if not file.filename:
        raise ValidationError(reason="上传文件名不能为空")

    original_filename = Path(file.filename).name.strip()
    if not original_filename:
        raise ValidationError(reason="上传文件名不能为空")

    safe_filename = f"{uuid4().hex}_{original_filename}"
    upload_dir = _ensure_upload_dir(chat_key, require_writable=True)
    save_path = upload_dir / safe_filename

    max_upload_size = max_size_mb * 1024 * 1024
    total_size = 0
    with save_path.open("wb") as target:
        while chunk := await file.read(1024 * 1024):
            total_size += len(chunk)
            if total_size > max_upload_size:
                save_path.unlink(missing_ok=True)
                raise ValidationError(reason=f"文件大小不能超过 {max_size_mb}MB")
            target.write(chunk)
    save_path.chmod(0o755)
    return str(save_path), safe_filename


async def _collect_web_message(
    adapter: "WebAdapter",
    channel: DBChatChannel,
    current_user: DBUser,
    content: str,
    content_data: List[ChatMessageSegment],
) -> WebMessageCreateResponse:
    if channel.channel_status == ChannelStatus.DISABLED:
        raise ValidationError(reason="当前网页聊天会话已停用")

    _ensure_upload_dir(channel.chat_key, require_writable=False)
    message_id = f"webmsg_{uuid4().hex}"
    platform_user = _build_platform_user(current_user, adapter)
    platform_message = PlatformMessage(
        message_id=message_id,
        sender_id=platform_user.user_id,
        sender_name=platform_user.user_name,
        sender_nickname=platform_user.user_name,
        sender_avatar="",
        content_text=content,
        content_data=content_data,
        is_tome=True,
        is_self=False,
    )

    await collect_message(adapter, _build_platform_channel(channel), platform_user, platform_message)
    return WebMessageCreateResponse(ok=True, chat_key=channel.chat_key, message_id=message_id)


@router.get("/mcp-auth", response_model=WebMcpAuthStatusResponse, summary="获取 Web Chat MCP 外接密钥状态")
@require_role(Role.Admin)
async def get_web_mcp_auth_status(
    _current_user: DBUser = Depends(get_current_active_user),
) -> WebMcpAuthStatusResponse:
    return _build_mcp_auth_status()


@router.put("/mcp-auth/external", response_model=WebMcpAuthStatusResponse, summary="保存 Web Chat MCP 外接密钥")
@require_role(Role.Admin)
async def update_web_mcp_external_auth(
    body: WebMcpExternalAuthUpdateRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WebMcpAuthStatusResponse:
    try:
        save_external_web_chat_mcp_token(enabled=body.enabled, token=body.token)
    except ValueError as exc:
        raise ValidationError(reason=str(exc)) from exc
    return _build_mcp_auth_status()


@router.post(
    "/mcp-auth/external/generate",
    response_model=WebMcpExternalAuthGenerateResponse,
    summary="生成 Web Chat MCP 外接固定密钥",
)
@require_role(Role.Admin)
async def generate_web_mcp_external_auth(
    _current_user: DBUser = Depends(get_current_active_user),
) -> WebMcpExternalAuthGenerateResponse:
    token, status = generate_external_web_chat_mcp_token()
    return WebMcpExternalAuthGenerateResponse(
        mcp_url=WEB_CHAT_MCP_URL,
        external=WebMcpExternalAuthStatus(**status),
        token=token,
    )


@router.delete("/mcp-auth/external", response_model=WebMcpAuthStatusResponse, summary="清除 Web Chat MCP 外接密钥")
@require_role(Role.Admin)
async def delete_web_mcp_external_auth(
    _current_user: DBUser = Depends(get_current_active_user),
) -> WebMcpAuthStatusResponse:
    clear_external_web_chat_mcp_token()
    return _build_mcp_auth_status()


@router.get("/sessions", response_model=WebSessionListResponse, summary="获取网页聊天会话列表")
@require_role(Role.Admin)
async def list_web_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str = "",
    _current_user: DBUser = Depends(get_current_active_user),
) -> WebSessionListResponse:
    """获取 Web Adapter 创建的网页聊天会话。"""
    adapter = _get_adapter()
    query = DBChatChannel.filter(adapter_key=WEB_ADAPTER_KEY)
    search_text = search.strip()
    if search_text:
        query = query.filter(
            Q(chat_key__icontains=search_text)
            | Q(channel_id__icontains=search_text)
            | Q(channel_name__icontains=search_text)
            | Q(data__icontains=search_text)
        )

    channels = await query.all()
    channel_sort_pairs = [(channel, await _get_session_sort_time(channel)) for channel in channels]
    channel_sort_pairs.sort(key=lambda item: (item[1][1], item[1][0]), reverse=True)

    start_index = (page - 1) * page_size
    paged_channels = [channel for channel, _sort_key in channel_sort_pairs[start_index : start_index + page_size]]
    return WebSessionListResponse(
        total=len(channels),
        items=[await _to_session_item(channel) for channel in paged_channels],
        limits=_get_session_limits(adapter),
    )


@router.post("/sessions", response_model=WebSessionResponse, status_code=201, summary="创建网页聊天会话")
@require_role(Role.Admin)
async def create_web_session(
    body: WebSessionCreateRequest,
    response: Response,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WebSessionResponse:
    """创建一个稳定映射到 DBChatChannel 的网页测试会话。"""
    adapter = _get_adapter()
    name = body.name.strip() or DEFAULT_SESSION_NAME
    channel_id = f"session_{uuid4().hex}"
    chat_key = adapter.build_chat_key(channel_id)

    existing = await DBChatChannel.get_or_none(adapter_key=WEB_ADAPTER_KEY, channel_id=channel_id)
    if existing is not None:
        response.status_code = 200
        return WebSessionResponse(
            chat_key=existing.chat_key,
            channel_id=existing.channel_id,
            channel_name=existing.channel_name or DEFAULT_SESSION_NAME,
            status=existing.channel_status.value,
        )

    channel = await DBChatChannel.get_or_create(
        adapter_key=WEB_ADAPTER_KEY,
        channel_id=channel_id,
        channel_type=ChatType.PRIVATE,
        channel_name=name,
        chat_key=chat_key,
    )
    await channel_broadcaster.publish_update(
        event_type="created",
        chat_key=channel.chat_key,
        channel_name=channel.channel_name,
        is_active=channel.is_active,
        status=channel.channel_status.value,
    )
    return WebSessionResponse(
        chat_key=channel.chat_key,
        channel_id=channel.channel_id,
        channel_name=channel.channel_name or DEFAULT_SESSION_NAME,
        status=channel.channel_status.value,
    )


@router.put("/sessions/{chat_key}", response_model=WebActionResponse, summary="更新网页聊天会话名称")
@require_role(Role.Admin)
async def update_web_session(
    chat_key: str,
    body: WebSessionUpdateRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WebActionResponse:
    """更新网页聊天会话的自定义名称。"""
    channel = await _get_web_channel(chat_key)
    name = body.name.strip()
    await channel.set_custom_channel_name(name or None)
    await channel_broadcaster.publish_update(
        event_type="updated",
        chat_key=channel.chat_key,
        channel_name=channel.channel_name,
        custom_channel_name=channel.get_custom_channel_name(),
        is_active=channel.is_active,
        status=channel.channel_status.value,
    )
    return WebActionResponse(ok=True)


@router.delete("/sessions/{chat_key}", response_model=WebActionResponse, summary="删除网页聊天会话")
@require_role(Role.Admin)
async def delete_web_session(
    chat_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WebActionResponse:
    """永久删除网页聊天会话及其关联数据。"""
    channel = await _get_web_channel(chat_key)

    await DBRecurringTimerJob.filter(chat_key=chat_key).delete()
    await DBPluginData.filter(target_chat_key=chat_key).delete()
    await DBMemParagraph.filter(origin_chat_key=chat_key).update(origin_chat_key=None)
    await DBMemEpisode.filter(origin_chat_key=chat_key).update(origin_chat_key=None)

    while await DBChatMessage.filter(chat_key=chat_key).limit(1000).delete():
        pass

    await channel.delete()

    upload_dir = Path(USER_UPLOAD_DIR) / sanitize_chat_key_for_path(chat_key)
    if upload_dir.exists():
        try:
            shutil.rmtree(upload_dir)
        except OSError as exc:
            logger.warning(f"清理网页会话上传目录失败 {upload_dir}: {exc}")

    sandbox_dir = Path(SANDBOX_SHARED_HOST_DIR) / f"sandbox_{sanitize_chat_key_for_path(chat_key)}"
    if sandbox_dir.exists():
        try:
            shutil.rmtree(sandbox_dir)
        except OSError as exc:
            logger.warning(f"清理网页会话沙盒目录失败 {sandbox_dir}: {exc}")

    await channel_broadcaster.publish_update(event_type="deleted", chat_key=chat_key)
    return WebActionResponse(ok=True)


@router.post("/sessions/{chat_key}/messages", response_model=WebMessageCreateResponse, summary="发送网页用户入站消息")
@require_role(Role.Admin)
async def create_web_message(
    chat_key: str,
    body: WebMessageCreateRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WebMessageCreateResponse:
    """以网页平台用户身份发送入站消息，并进入 collect_message 管线。"""
    adapter = _get_adapter()
    channel = await _get_web_channel(chat_key)

    content = body.content.strip()
    if not content:
        raise ValidationError(reason="消息内容不能为空")
    if len(content) > adapter.config.MESSAGE_MAX_LENGTH:
        raise ValidationError(reason=f"消息长度不能超过 {adapter.config.MESSAGE_MAX_LENGTH} 个字符")

    return await _collect_web_message(
        adapter,
        channel,
        _current_user,
        content,
        [
            ChatMessageSegment(
                type=ChatMessageSegmentType.TEXT,
                text=content,
            )
        ],
    )


@router.post("/sessions/{chat_key}/messages/upload", response_model=WebMessageCreateResponse, summary="上传网页用户文件入站消息")
@require_role(Role.Admin)
async def create_web_upload_message(
    chat_key: str,
    content: str = Form(default=""),
    file: UploadFile = File(...),
    _current_user: DBUser = Depends(get_current_active_user),
) -> WebMessageCreateResponse:
    """上传网页用户文件，并作为入站文件/图片消息进入 collect_message 管线。"""
    adapter = _get_adapter()
    channel = await _get_web_channel(chat_key)
    text = content.strip()
    if len(text) > adapter.config.MESSAGE_MAX_LENGTH:
        raise ValidationError(reason=f"消息长度不能超过 {adapter.config.MESSAGE_MAX_LENGTH} 个字符")

    _saved_path, file_name = await _save_upload_file(
        chat_key=channel.chat_key,
        file=file,
        max_size_mb=adapter.config.FILE_UPLOAD_MAX_SIZE_MB,
    )
    is_image = (file.content_type or "").startswith("image/")
    file_segment_cls = ChatMessageSegmentImage if is_image else ChatMessageSegmentFile
    file_label = "Image" if is_image else "File"
    file_segment = file_segment_cls(
        type=ChatMessageSegmentType.IMAGE if is_image else ChatMessageSegmentType.FILE,
        text=f"[{file_label}: {file_name}]",
        file_name=file_name,
    )

    content_data: List[ChatMessageSegment] = []
    if text:
        content_data.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=text))
    content_data.append(file_segment)
    content_text = f"{text}\n{file_segment.text}".strip()

    return await _collect_web_message(adapter, channel, _current_user, content_text, content_data)
