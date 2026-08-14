from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import json5
from pydantic import BaseModel, ConfigDict, Field
from tortoise.expressions import Q

from nekro_agent.adapters import (
    ADAPTER_REGISTRY,
    adapter_load_errors,
    get_adapter,
    get_adapter_config_path,
    is_adapter_enabled,
)
from nekro_agent.models.db_chat_channel import ChannelStatus, DBChatChannel
from nekro_agent.models.db_chat_message import DBChatMessage
from nekro_agent.models.db_mem_episode import DBMemEpisode
from nekro_agent.models.db_mem_paragraph import DBMemParagraph
from nekro_agent.models.db_plugin_data import DBPluginData
from nekro_agent.models.db_recurring_timer_job import DBRecurringTimerJob
from nekro_agent.schemas.chat_message import (
    ChatMessageSegment,
    ChatMessageSegmentFile,
    ChatMessageSegmentImage,
    ChatMessageSegmentType,
    ChatType,
)
from nekro_agent.schemas.errors import AppError
from nekro_agent.schemas.i18n import SupportedLang
from nekro_agent.services.channel_broadcaster import channel_broadcaster
from nekro_agent.tools.path_convertor import sanitize_chat_key_for_path

from .context import get_current_user

WEB_ADAPTER_KEY = "web"
DEFAULT_SESSION_NAME = "网页测试会话"
BOT_SENDER_ID = "-1"


class WebChatMcpSettings(BaseModel):
    file_allowlist: list[Path] = Field(default_factory=list)
    wait_timeout_seconds: float = Field(default=60.0, ge=1.0, le=300.0)
    poll_interval_seconds: float = Field(default=1.5, ge=0.5, le=30.0)

    @classmethod
    def from_env(cls) -> "WebChatMcpSettings":
        allowlist_raw = os.getenv("NEKRO_WEB_CHAT_MCP_FILE_ALLOWLIST", "")
        allowlist = [Path(item).expanduser().resolve() for item in allowlist_raw.split(os.pathsep) if item.strip()]
        return cls(
            file_allowlist=allowlist,
            wait_timeout_seconds=_float_env("NEKRO_WAIT_TIMEOUT", 60.0),
            poll_interval_seconds=_float_env("NEKRO_POLL_INTERVAL", 1.5),
        )


class ChatMessageItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    sender_id: str
    sender_name: str
    sender_nickname: str
    platform_userid: str
    content: str
    content_data: list[dict[str, Any]] = Field(default_factory=list)
    chat_key: str
    create_time: str
    message_id: str = ""
    ref_msg_id: str = ""

    @property
    def role(self) -> str:
        if self.platform_userid == "0" or self.sender_name == "SYSTEM":
            return "system"
        if self.sender_id == BOT_SENDER_ID:
            return "agent"
        return "user"

    def to_public(self, *, include_segments: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "role": self.role,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "sender_nickname": self.sender_nickname,
            "platform_userid": self.platform_userid,
            "content": self.content,
            "chat_key": self.chat_key,
            "create_time": self.create_time,
            "message_id": self.message_id,
            "ref_msg_id": self.ref_msg_id,
        }
        if include_segments:
            payload["content_data"] = self.content_data
        return payload


class WebChatMcpService:
    def __init__(self, settings: WebChatMcpSettings | None = None) -> None:
        self.settings = settings or WebChatMcpSettings.from_env()

    async def check_status(self) -> dict[str, Any]:
        if WEB_ADAPTER_KEY not in ADAPTER_REGISTRY:
            return error_result(status="adapter_not_registered", message="Web Adapter 未注册", error_type="NotFoundError")

        try:
            adapter = get_adapter(WEB_ADAPTER_KEY)
            status = {
                "status": "enabled",
                "loaded": True,
                "initialized": True,
                "has_config": hasattr(adapter, "config") and adapter.config is not None,
                "config_file_exists": getattr(adapter, "config_path", None).exists()
                if hasattr(adapter, "config_path")
                else None,
            }
        except Exception:
            status = {
                "status": "failed"
                if is_adapter_enabled(WEB_ADAPTER_KEY) and WEB_ADAPTER_KEY in adapter_load_errors
                else "disabled",
                "loaded": False,
                "initialized": False,
                "has_config": True,
                "config_file_exists": get_adapter_config_path(WEB_ADAPTER_KEY).exists(),
                "error_message": adapter_load_errors.get(WEB_ADAPTER_KEY),
            }

        return {
            "ok": status["status"] == "enabled",
            "status": "ready" if status["status"] == "enabled" else "adapter_unavailable",
            "adapter": status,
            "auth": "handled_by_nekro_agent",
        }

    async def list_sessions(self, *, page: int = 1, page_size: int = 20, search: str = "") -> dict[str, Any]:
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
        pairs = [(channel, await _get_session_sort_time(channel)) for channel in channels]
        pairs.sort(key=lambda item: (item[1][1], item[1][0]), reverse=True)
        start_index = (page - 1) * page_size
        paged_channels = [channel for channel, _sort_key in pairs[start_index : start_index + page_size]]
        return {
            "ok": True,
            "status": "ok",
            "total": len(channels),
            "items": [await _session_to_public(channel) for channel in paged_channels],
        }

    async def create_session(self, *, name: str = "") -> dict[str, Any]:
        adapter = _get_web_adapter()
        session_name = name.strip() or DEFAULT_SESSION_NAME
        channel_id = f"session_{uuid4().hex}"
        chat_key = adapter.build_chat_key(channel_id)
        channel = await DBChatChannel.get_or_create(
            adapter_key=WEB_ADAPTER_KEY,
            channel_id=channel_id,
            channel_type=ChatType.PRIVATE,
            channel_name=session_name,
            chat_key=chat_key,
        )
        await channel_broadcaster.publish_update(
            event_type="created",
            chat_key=channel.chat_key,
            channel_name=channel.channel_name,
            is_active=channel.is_active,
            status=channel.channel_status.value,
        )
        return {
            "ok": True,
            "status": "ok",
            "session": {
                "chat_key": channel.chat_key,
                "channel_id": channel.channel_id,
                "channel_name": channel.channel_name or DEFAULT_SESSION_NAME,
                "status": channel.channel_status.value,
            },
        }

    async def rename_session(self, chat_key: str, *, name: str) -> dict[str, Any]:
        channel = await _get_web_channel(chat_key)
        await channel.set_custom_channel_name(name.strip() or None)
        await channel_broadcaster.publish_update(
            event_type="updated",
            chat_key=channel.chat_key,
            channel_name=channel.channel_name,
            custom_channel_name=channel.get_custom_channel_name(),
            is_active=channel.is_active,
            status=channel.channel_status.value,
        )
        return {"ok": True, "status": "ok"}

    async def delete_session(self, chat_key: str, *, confirm: bool) -> dict[str, Any]:
        if not confirm:
            return error_result(
                status="confirmation_required",
                message="删除网页聊天会话会清理历史、插件数据、定时任务和上传目录；请显式传入 confirm=true",
                error_type="ConfirmationRequired",
            )
        channel = await _get_web_channel(chat_key)
        await DBRecurringTimerJob.filter(chat_key=chat_key).delete()
        await DBPluginData.filter(target_chat_key=chat_key).delete()
        await DBMemParagraph.filter(origin_chat_key=chat_key).update(origin_chat_key=None)
        await DBMemEpisode.filter(origin_chat_key=chat_key).update(origin_chat_key=None)
        while await DBChatMessage.filter(chat_key=chat_key).limit(1000).delete():
            pass
        await channel.delete()

        from nekro_agent.core.os_env import SANDBOX_SHARED_HOST_DIR, USER_UPLOAD_DIR

        for path in (
            Path(USER_UPLOAD_DIR) / sanitize_chat_key_for_path(chat_key),
            Path(SANDBOX_SHARED_HOST_DIR) / f"sandbox_{sanitize_chat_key_for_path(chat_key)}",
        ):
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)

        await channel_broadcaster.publish_update(event_type="deleted", chat_key=chat_key)
        return {"ok": True, "status": "ok"}

    async def send_message(self, chat_key: str, *, content: str) -> dict[str, Any]:
        content = content.strip()
        if not content:
            return error_result(status="validation_error", message="消息内容不能为空", error_type="ValidationError")
        adapter = _get_web_adapter()
        channel = await _get_web_channel(chat_key)
        try:
            message_max_length = adapter.config.MESSAGE_MAX_LENGTH
        except AttributeError:
            message_max_length = 8000
        if len(content) > message_max_length:
            return error_result(
                status="validation_error",
                message=f"消息长度不能超过 {message_max_length} 个字符",
                error_type="ValidationError",
            )
        result = await _collect_message(
            adapter,
            channel,
            content,
            [ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=content)],
        )
        if not result.get("ok", True):
            return result
        return {"ok": True, "status": "ok", "message": result}

    async def send_file(self, chat_key: str, *, file_path: str, content: str = "") -> dict[str, Any]:
        safe_path = self._validate_file_path(file_path)
        if isinstance(safe_path, dict):
            return safe_path
        adapter = _get_web_adapter()
        channel = await _get_web_channel(chat_key)
        try:
            message_max_length = adapter.config.MESSAGE_MAX_LENGTH
            max_size_mb = adapter.config.FILE_UPLOAD_MAX_SIZE_MB
        except AttributeError:
            message_max_length = 8000
            max_size_mb = 100
        text = content.strip()
        if len(text) > message_max_length:
            return error_result(
                status="validation_error",
                message=f"消息长度不能超过 {message_max_length} 个字符",
                error_type="ValidationError",
            )
        if safe_path.stat().st_size > max_size_mb * 1024 * 1024:
            return error_result(
                status="validation_error",
                message=f"文件大小不能超过 {max_size_mb}MB",
                error_type="ValidationError",
            )

        from starlette.datastructures import UploadFile

        from nekro_agent.adapters.web.routers import _save_upload_file

        with safe_path.open("rb") as file_obj:
            upload = UploadFile(file=file_obj, filename=safe_path.name)
            saved_path, file_name = await _save_upload_file(channel.chat_key, upload, max_size_mb)

        is_image = safe_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        segment_cls = ChatMessageSegmentImage if is_image else ChatMessageSegmentFile
        file_label = "Image" if is_image else "File"
        file_segment = segment_cls(
            type=ChatMessageSegmentType.IMAGE if is_image else ChatMessageSegmentType.FILE,
            text=f"[{file_label}: {file_name}]",
            file_name=file_name,
            local_path=saved_path,
        )
        segments: list[ChatMessageSegment] = []
        if text:
            segments.append(ChatMessageSegment(type=ChatMessageSegmentType.TEXT, text=text))
        segments.append(file_segment)
        result = await _collect_message(adapter, channel, f"{text}\n{file_segment.text}".strip(), segments)
        if not result.get("ok", True):
            return result
        return {"ok": True, "status": "ok", "message": result}

    async def get_messages(
        self,
        chat_key: str,
        *,
        before_id: int | None = None,
        page_size: int = 32,
        include_segments: bool = True,
    ) -> dict[str, Any]:
        items = await _get_messages(chat_key, before_id=before_id, page_size=page_size)
        return {
            "ok": True,
            "status": "ok",
            "items": [item.to_public(include_segments=include_segments) for item in items],
        }

    async def get_channel_detail(self, chat_key: str) -> dict[str, Any]:
        channel = await _get_web_channel(chat_key)
        message_count = await DBChatMessage.filter(chat_key=chat_key).count()
        return {
            "ok": True,
            "status": "ok",
            "channel": {
                "id": channel.id,
                "chat_key": channel.chat_key,
                "channel_name": channel.channel_name,
                "custom_channel_name": channel.get_custom_channel_name(),
                "is_active": channel.is_active,
                "status": channel.channel_status.value,
                "chat_type": channel.chat_type.value,
                "message_count": message_count,
                "create_time": channel.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": channel.update_time.strftime("%Y-%m-%d %H:%M:%S"),
                "conversation_start_time": channel.conversation_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "preset_id": channel.preset_id,
            },
        }

    async def wait_for_reply(
        self,
        chat_key: str,
        *,
        after_id: int | None = None,
        after_message_id: str = "",
        timeout_seconds: float | None = None,
        poll_interval_seconds: float | None = None,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + (timeout_seconds or self.settings.wait_timeout_seconds)
        poll_interval = poll_interval_seconds or self.settings.poll_interval_seconds
        observed: list[ChatMessageItem] = []
        last_seen_id = after_id or 0

        while True:
            items = await _get_messages(chat_key, page_size=64)
            lower_bound = _resolve_after_id(items, after_id=after_id, after_message_id=after_message_id)
            new_messages = [item for item in items if item.id > lower_bound]
            if new_messages:
                observed = new_messages
                last_seen_id = max(last_seen_id, max(item.id for item in new_messages))
                agent_messages = [item for item in new_messages if item.role == "agent"]
                if agent_messages:
                    return {
                        "ok": True,
                        "status": "reply_received",
                        "chat_key": chat_key,
                        "last_seen_id": last_seen_id,
                        "messages": [item.to_public() for item in new_messages],
                        "agent_messages": [item.to_public() for item in agent_messages],
                    }
            if time.monotonic() >= deadline:
                return {
                    "ok": False,
                    "status": "timeout",
                    "chat_key": chat_key,
                    "last_seen_id": last_seen_id,
                    "messages": [item.to_public() for item in observed],
                    "message": "等待 Agent 回复超时",
                }
            await asyncio.sleep(poll_interval)

    async def send_and_wait(
        self,
        chat_key: str,
        *,
        content: str,
        timeout_seconds: float | None = None,
        poll_interval_seconds: float | None = None,
    ) -> dict[str, Any]:
        before_items = await _get_messages(chat_key, page_size=1)
        after_id = max((item.id for item in before_items), default=0)
        send_result = await self.send_message(chat_key, content=content)
        if not send_result.get("ok"):
            return send_result
        sent_message_id = str((send_result.get("message") or {}).get("message_id") or "")
        wait_result = await self.wait_for_reply(
            chat_key,
            after_id=after_id,
            after_message_id=sent_message_id,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        return {
            "ok": bool(wait_result.get("ok")),
            "status": wait_result.get("status", "unknown"),
            "sent": send_result.get("message"),
            "reply": wait_result,
        }

    def _validate_file_path(self, file_path: str) -> Path | dict[str, Any]:
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            return error_result(status="file_error", message="上传文件不存在或不是普通文件", error_type="FileNotFound")
        if not self.settings.file_allowlist:
            return error_result(
                status="file_not_allowed",
                message="文件上传需要配置 NEKRO_WEB_CHAT_MCP_FILE_ALLOWLIST，避免 MCP 读取任意本地文件",
                error_type="FileAllowlistRequired",
            )
        for allowed in self.settings.file_allowlist:
            try:
                path.relative_to(allowed)
                return path
            except ValueError:
                continue
        return error_result(status="file_not_allowed", message="上传文件不在允许目录内", error_type="FileNotAllowed")


def error_result(*, status: str, message: str, error_type: str) -> dict[str, Any]:
    return {"ok": False, "status": status, "error": {"type": error_type, "message": message}}


def app_error_result(exc: AppError) -> dict[str, Any]:
    return error_result(
        status="api_error",
        message=exc.get_message(SupportedLang.ZH_CN),
        error_type=exc.get_error_name(),
    )


async def _get_session_sort_time(channel: DBChatChannel) -> tuple[int, float]:
    last_message = await DBChatMessage.filter(chat_key=channel.chat_key).order_by("-create_time").first()
    last_time = last_message.create_time if last_message else channel.update_time
    return channel.id, last_time.timestamp()


async def _session_to_public(channel: DBChatChannel) -> dict[str, Any]:
    message_count = await DBChatMessage.filter(chat_key=channel.chat_key).count()
    last_message = await DBChatMessage.filter(chat_key=channel.chat_key).order_by("-create_time").first()
    display_time = last_message.create_time if last_message else channel.update_time
    display_name = channel.get_custom_channel_name() or channel.channel_name or channel.chat_key
    return {
        "chat_key": channel.chat_key,
        "channel_id": channel.channel_id,
        "display_name": display_name,
        "channel_name": channel.channel_name,
        "custom_channel_name": channel.get_custom_channel_name(),
        "status": channel.channel_status.value,
        "message_count": message_count,
        "update_time": display_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


async def _get_web_channel(chat_key: str) -> DBChatChannel:
    channel = await DBChatChannel.filter(chat_key=chat_key).first()
    if channel is None or channel.adapter_key != WEB_ADAPTER_KEY:
        from nekro_agent.schemas.errors import NotFoundError

        raise NotFoundError(resource="网页聊天会话")
    return channel


def _get_web_adapter() -> Any:
    return get_adapter(WEB_ADAPTER_KEY)


async def _collect_message(
    adapter: Any,
    channel: DBChatChannel,
    content: str,
    content_data: list[ChatMessageSegment],
) -> dict[str, Any]:
    from nekro_agent.adapters.web.routers import _collect_web_message

    if channel.channel_status == ChannelStatus.DISABLED:
        return error_result(status="validation_error", message="当前网页聊天会话已停用", error_type="ValidationError")
    response = await _collect_web_message(adapter, channel, get_current_user(), content, content_data)
    return response.model_dump()


async def _get_messages(chat_key: str, *, before_id: int | None = None, page_size: int = 32) -> list[ChatMessageItem]:
    channel = await _get_web_channel(chat_key)
    query = DBChatMessage.filter(chat_key=chat_key, create_time__gte=channel.conversation_start_time)
    if before_id:
        query = query.filter(id__lt=before_id)
    messages = await query.order_by("-id").limit(page_size)
    items = [
        ChatMessageItem(
            id=msg.id,
            sender_id=str(msg.sender_id),
            sender_name=msg.sender_name,
            sender_nickname=msg.sender_nickname or msg.sender_name,
            platform_userid=msg.platform_userid or "",
            content=msg.content_text,
            content_data=_parse_content_data(msg.content_data),
            chat_key=msg.chat_key,
            create_time=msg.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            message_id=getattr(msg, "message_id", "") or "",
            ref_msg_id=_safe_ref_msg_id(msg),
        )
        for msg in messages
    ]
    return sorted(items, key=lambda item: item.id)


def _parse_content_data(raw: str) -> list[dict[str, Any]]:
    try:
        value = json5.loads(raw) if raw else []
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _safe_ref_msg_id(msg: DBChatMessage) -> str:
    try:
        return msg.ext_data_obj.ref_msg_id or ""
    except (AttributeError, KeyError, ValueError):
        return ""


def _resolve_after_id(messages: list[ChatMessageItem], *, after_id: int | None, after_message_id: str) -> int:
    if after_message_id:
        matched = next((message for message in messages if message.message_id == after_message_id), None)
        if matched:
            return matched.id
    return after_id or 0


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default
