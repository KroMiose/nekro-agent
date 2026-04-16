import asyncio
import contextlib
import fcntl
import json
import os
import pty
import struct
import subprocess
import termios
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Literal, Optional

import aiodocker
from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_user import DBUser
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.schemas.errors import (
    ConflictError,
    NotFoundError,
    OperationFailedError,
    ValidationError,
)
from nekro_agent.schemas.workspace import (
    BoundChannelInfo,
    BoundChannelsResponse,
    ChannelAnnotationUpdate,
    ChannelBindRequest,
    ClaudeMdExtraUpdate,
    ClaudeMdResponse,
    CommHistoryResponse,
    CommLogEntry,
    CommSendBody,
    CommStatusPayload,
    PromptComposerResponse,
    PromptLayerItem,
    PromptLayerUpdate,
    SandboxStatus,
    ToolsResponse,
    WorkspaceCommQueueResponse,
    WorkspaceCommQueueTask,
    WorkspaceCreate,
    WorkspaceDetail,
    WorkspaceListResponse,
    WorkspaceOverviewStats,
    WorkspaceSkillsUpdate,
    WorkspaceSummary,
    WorkspaceUpdate,
)
from nekro_agent.services.mcp.schemas import McpServerConfig
from nekro_agent.services.memory.feature_flags import (
    MemoryOperation,
    ensure_memory_system_enabled,
    is_memory_system_enabled,
)
from nekro_agent.services.memory.maintenance import MemoryPruneResult, prune_workspace_memories
from nekro_agent.services.memory.qdrant_manager import memory_qdrant_manager
from nekro_agent.services.memory.retriever import retrieve_memories
from nekro_agent.services.memory.semantic_writer import persist_cc_task_memory
from nekro_agent.services.resources import workspace_resource_service
from nekro_agent.services.runtime_state import is_shutting_down
from nekro_agent.services.system_broadcast import (
    WorkspaceCcActiveEvent,
    WorkspaceCcRuntimeStatusEvent,
    WorkspaceStatusEvent,
    publish_system_event,
)
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.services.workspace.client import CCSandboxClient, CCSandboxError
from nekro_agent.services.workspace.container import ImageNotFoundError, SandboxContainerManager
from nekro_agent.services.workspace.manager import WorkspaceService
from nekro_agent.services.workspace.prompt_envelope import CcPromptEnvelope

if TYPE_CHECKING:
    from nekro_agent.models.db_mem_episode import DBMemEpisode

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])
logger = get_sub_logger("workspaces")


class ActionOkResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None


class LogsOkResponse(BaseModel):
    logs: str


class ChannelListResponse(BaseModel):
    channels: List[str]


class WorkspaceSkillsResponse(BaseModel):
    skills: List[str]


class McpConfigResponse(BaseModel):
    mcp_config: Dict[str, Any]


class McpConfigUpdate(BaseModel):
    mcp_config: Dict[str, Any]


class SandboxQueuedChunk(BaseModel):
    type: Literal["queued"]
    queue_length: int = 0


class SandboxToolChunk(BaseModel):
    type: Literal["tool_call", "tool_result"]
    name: Optional[str] = None
    tool_use_id: Optional[str] = None


def _summarize_comm_block_text(value: str, max_length: int = 48) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        return ""
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 1]}…"


# ─────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_timestamp_ms(value: object) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric <= 0:
            return None
        if numeric < 1_000_000_000_000:
            numeric *= 1000
        return int(numeric)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            numeric = float(text)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return None
            return int(parsed.timestamp() * 1000)
        if numeric <= 0:
            return None
        if numeric < 1_000_000_000_000:
            numeric *= 1000
        return int(numeric)
    return None


def _parse_comm_queue_task(raw: object) -> Optional[WorkspaceCommQueueTask]:
    if not isinstance(raw, dict):
        return None
    return WorkspaceCommQueueTask(
        task_id=str(raw.get("task_id")) if raw.get("task_id") is not None else None,
        source_chat_key=str(raw.get("source_chat_key")) if raw.get("source_chat_key") is not None else None,
        started_at=_normalize_timestamp_ms(raw.get("started_at")),
        enqueued_at=_normalize_timestamp_ms(raw.get("enqueued_at")),
    )


def _parse_comm_queue_response(raw: object) -> WorkspaceCommQueueResponse:
    if not isinstance(raw, dict):
        return WorkspaceCommQueueResponse()
    queue_length_raw = raw.get("queue_length")
    queue_length = int(queue_length_raw) if isinstance(queue_length_raw, (int, float)) and not isinstance(queue_length_raw, bool) else 0
    parsed_tasks = [_parse_comm_queue_task(item) for item in raw.get("queued_tasks", []) if isinstance(raw.get("queued_tasks"), list)]
    return WorkspaceCommQueueResponse(
        current_task=_parse_comm_queue_task(raw.get("current_task")),
        queued_tasks=[task for task in parsed_tasks if task is not None],
        queue_length=max(queue_length, 0),
    )


def _build_cc_status_entry(
    workspace_id: int,
    *,
    running: bool,
    started_at: Optional[int],
) -> CommLogEntry:
    return CommLogEntry(
        id=0,
        workspace_id=workspace_id,
        direction="CC_STATUS",
        source_chat_key="",
        content=CommStatusPayload(running=running, started_at=started_at).model_dump_json(),
        is_streaming=False,
        task_id=None,
        create_time=_utc_now_iso(),
    )


def _summary(
    ws: DBWorkspace,
    *,
    channel_names: "List[str] | None" = None,
    channel_display_names: "List[str] | None" = None,
) -> WorkspaceSummary:
    from nekro_agent.core.cc_model_presets import cc_presets_store
    from nekro_agent.core.config import config as app_config

    metadata = ws.metadata or {}
    skill_count = len(metadata.get("skills", []))
    mcp_count = len((metadata.get("mcp_config") or {}).get("mcpServers", {}))

    preset_name: Optional[str] = None
    preset_id = metadata.get("cc_model_preset_id")
    if preset_id is not None:
        preset = cc_presets_store.get_by_id(int(preset_id))
        if preset:
            preset_name = preset.name
    if preset_name is None:
        default = cc_presets_store.get_default()
        if default:
            preset_name = default.name

    channels = channel_names or []
    display_names = channel_display_names or channels  # fallback 到 chat_key
    return WorkspaceSummary(
        id=ws.id,
        name=ws.name,
        description=ws.description,
        status=ws.status,
        memory_system_enabled=bool(app_config.MEMORY_ENABLE_SYSTEM),
        sandbox_image=ws.sandbox_image or app_config.CC_SANDBOX_IMAGE,
        sandbox_version=ws.sandbox_version or app_config.CC_SANDBOX_IMAGE_TAG,
        container_name=ws.container_name,
        host_port=ws.host_port,
        runtime_policy=ws.runtime_policy,
        create_time=ws.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        update_time=ws.update_time.strftime("%Y-%m-%d %H:%M:%S"),
        channel_count=len(channels),
        channel_names=channels[:2],
        channel_display_names=display_names[:2],
        skill_count=skill_count,
        mcp_count=mcp_count,
        cc_model_preset_name=preset_name,
    )


async def _detail_async(ws: DBWorkspace) -> WorkspaceDetail:
    """异步版本的 _detail，自动查询绑定频道以填充 primary_channel_chat_key。"""
    channels = await WorkspaceService.get_bound_channels(ws.id)
    return _detail(ws, bound_chat_keys=[ch.chat_key for ch in channels])


async def _build_cc_memory_handshake(workspace_id: int, instruction: str, limit: int = 6) -> CcPromptEnvelope:
    """为用户直发 CC 指令构造含记忆握手的 prompt 封装。"""
    now_str = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")

    if not is_memory_system_enabled():
        return CcPromptEnvelope.for_user_path(current_time=now_str, task_body=instruction)

    try:
        memories = await retrieve_memories(
            workspace_id=workspace_id,
            query=instruction,
            limit=limit,
        )
    except Exception as e:
        logger.debug(f"构建 CC 记忆握手失败（检索异常，可忽略）: {e}")
        return CcPromptEnvelope.for_user_path(current_time=now_str, task_body=instruction)

    if not memories:
        return CcPromptEnvelope.for_user_path(current_time=now_str, task_body=instruction)

    memory_lines: List[str] = []
    for idx, mem in enumerate(memories, start=1):
        summary = mem.summary or mem.content[:120]
        summary = summary.replace("\n", " ").strip()
        memory_lines.append(f"{idx}. [{mem.cognitive_type}/{mem.knowledge_type}] {summary}")

    return CcPromptEnvelope.for_user_path(
        current_time=now_str,
        task_body=instruction,
        memory_lines=memory_lines,
    )


def _detail(ws: DBWorkspace, *, bound_chat_keys: "List[str] | None" = None) -> WorkspaceDetail:
    from nekro_agent.core.cc_model_presets import cc_presets_store

    base = _summary(ws)
    cc_model_preset_id = (ws.metadata or {}).get("cc_model_preset_id")
    if cc_model_preset_id is None:
        default = cc_presets_store.get_default()
        if default:
            cc_model_preset_id = default.id
    primary_channel_chat_key = WorkspaceService.get_primary_channel_chat_key(ws, bound_chat_keys or [])
    return WorkspaceDetail(
        **base.model_dump(),
        container_id=ws.container_id,
        last_heartbeat=ws.last_heartbeat.strftime("%Y-%m-%d %H:%M:%S") if ws.last_heartbeat else None,
        last_error=ws.last_error,
        metadata=dict(ws.metadata),
        cc_model_preset_id=int(cc_model_preset_id) if cc_model_preset_id is not None else None,
        primary_channel_chat_key=primary_channel_chat_key,
    )


async def _resolve_workspace_runtime_env(workspace: DBWorkspace) -> "Dict[str, str]":
    return await workspace_resource_service.resolve_workspace_resources_to_env(workspace.id)


def _get_prompt_layers_metadata(workspace: DBWorkspace) -> dict[str, Any]:
    metadata = dict(workspace.metadata or {})
    prompt_layers = metadata.get("prompt_layers")
    return prompt_layers if isinstance(prompt_layers, dict) else {}


def _build_prompt_layer_item(
    *,
    key: str,
    title: str,
    target: Literal["cc", "na", "shared"],
    maintainer: Literal["manual", "cc", "na", "manual+cc", "manual+na"],
    content: str,
    description: str,
    editable_by_cc: bool,
    auto_inject: bool,
    updated_at: str | None = None,
    updated_by: str | None = None,
) -> PromptLayerItem:
    return PromptLayerItem(
        key=key,
        title=title,
        target=target,
        maintainer=maintainer,
        content=content,
        description=description,
        editable_by_cc=editable_by_cc,
        auto_inject=auto_inject,
        updated_at=updated_at,
        updated_by=updated_by,
    )


# ─────────────────────────────────────────────────────────────
# 工作区 CRUD
# ─────────────────────────────────────────────────────────────


@router.get("/list", summary="获取工作区列表", response_model=WorkspaceListResponse)
@require_role(Role.Admin)
async def list_workspaces(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceListResponse:
    from nekro_agent.models.db_chat_channel import DBChatChannel

    query = DBWorkspace.all()
    if search:
        query = query.filter(name__contains=search)
    total = await query.count()
    workspaces = await query.offset((page - 1) * page_size).limit(page_size).order_by("-update_time")

    # 批量查询频道绑定（避免 N+1 查询），同时取 channel_name 用于显示
    ws_ids = [ws.id for ws in workspaces]
    channels_all = await DBChatChannel.filter(workspace_id__in=ws_ids).values("workspace_id", "chat_key", "channel_name")
    channels_by_ws: Dict[int, List[str]] = {}
    display_by_ws: Dict[int, List[str]] = {}
    for ch in channels_all:
        wid: int = ch["workspace_id"]
        chat_key: str = ch["chat_key"]
        # 优先使用 channel_name，无则 fallback 到 chat_key
        display: str = ch.get("channel_name") or chat_key
        channels_by_ws.setdefault(wid, []).append(chat_key)
        display_by_ws.setdefault(wid, []).append(display)

    return WorkspaceListResponse(
        total=total,
        items=[
            _summary(
                ws,
                channel_names=channels_by_ws.get(ws.id, []),
                channel_display_names=display_by_ws.get(ws.id, []),
            )
            for ws in workspaces
        ],
    )


@router.post("", summary="创建工作区", response_model=WorkspaceDetail)
@require_role(Role.Admin)
async def create_workspace(
    body: WorkspaceCreate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceDetail:
    existing = await DBWorkspace.get_or_none(name=body.name)
    if existing:
        raise ConflictError(resource=f"工作区 '{body.name}'")

    ws = await DBWorkspace.create(
        name=body.name,
        description=body.description,
        runtime_policy=body.runtime_policy,
    )

    # 自动注入默认技能
    from nekro_agent.core.auto_inject_skills import get_auto_inject_skills

    auto_skills = get_auto_inject_skills()
    if auto_skills:
        valid_skills = [s["name"] for s in WorkspaceService.list_all_skills()]
        injected = [name for name in auto_skills if name in valid_skills]
        if injected:
            metadata = ws.metadata or {}
            metadata["skills"] = injected
            ws.metadata = metadata
            await ws.save(update_fields=["metadata"])

    # 自动注入 MCP 服务
    from nekro_agent.core.auto_inject_mcp import get_auto_inject_mcp_servers

    auto_mcp = get_auto_inject_mcp_servers()
    if auto_mcp:
        metadata = ws.metadata or {}
        mcp_config: Dict[str, Any] = metadata.get("mcp_config", {"mcpServers": {}})
        if "mcpServers" not in mcp_config:
            mcp_config["mcpServers"] = {}
        for server in auto_mcp:
            name = server.get("name", "")
            if not name:
                continue
            raw: Dict[str, Any] = {}
            srv_type = server.get("type", "stdio")
            if not server.get("enabled", True):
                raw["enabled"] = False
            raw["transport"] = srv_type
            if server.get("url"):
                raw["url"] = server["url"]
                if server.get("headers"):
                    raw["headers"] = dict(server["headers"])
            else:
                if server.get("command"):
                    raw["command"] = server["command"]
                if server.get("args"):
                    raw["args"] = list(server["args"])
                if server.get("env"):
                    raw["env"] = dict(server["env"])
            mcp_config["mcpServers"][name] = raw
        metadata["mcp_config"] = mcp_config
        ws.metadata = metadata
        await ws.save(update_fields=["metadata"])

    return await _detail_async(ws)


@router.get("/{workspace_id}", summary="获取工作区详情", response_model=WorkspaceDetail)
@require_role(Role.Admin)
async def get_workspace(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceDetail:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    return await _detail_async(ws)


@router.get("/{workspace_id}/overview-stats", summary="获取工作区概览统计", response_model=WorkspaceOverviewStats)
@require_role(Role.Admin)
async def get_workspace_overview_stats(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceOverviewStats:
    """聚合工作区各维度统计数据，供概览页一次性获取，避免多次请求。"""
    from datetime import timedelta

    from nekro_agent.models.db_mem_entity import DBMemEntity
    from nekro_agent.models.db_mem_paragraph import DBMemParagraph
    from nekro_agent.models.db_mem_reinforcement_log import DBMemReinforcementLog
    from nekro_agent.models.db_mem_relation import DBMemRelation
    from nekro_agent.models.db_workspace_resource_binding import DBWorkspaceResourceBinding

    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    memory_enabled = is_memory_system_enabled()

    if memory_enabled:
        paragraph_count, entity_count, relation_count, reinforcement_count_7d = await asyncio.gather(
            DBMemParagraph.filter(workspace_id=workspace_id).count(),
            DBMemEntity.filter(workspace_id=workspace_id).count(),
            DBMemRelation.filter(workspace_id=workspace_id).count(),
            DBMemReinforcementLog.filter(
                workspace_id=workspace_id,
                create_time__gte=datetime.now(timezone.utc) - timedelta(days=7),
            ).count(),
        )
    else:
        paragraph_count = entity_count = relation_count = reinforcement_count_7d = 0

    resource_binding_count, = await asyncio.gather(
        DBWorkspaceResourceBinding.filter(workspace_id=workspace_id, enabled=True).count(),
    )

    dynamic_skill_count = len(WorkspaceService.list_dynamic_skills(workspace_id))

    na_context_body, na_context_updated = WorkspaceService.read_na_context(workspace_id)
    na_context_preview = na_context_body[:150] if na_context_body else ""

    return WorkspaceOverviewStats(
        memory_enabled=memory_enabled,
        memory_paragraph_count=paragraph_count,
        memory_entity_count=entity_count,
        memory_relation_count=relation_count,
        memory_reinforcement_7d=reinforcement_count_7d,
        dynamic_skill_count=dynamic_skill_count,
        resource_binding_count=resource_binding_count,
        na_context_preview=na_context_preview,
        na_context_updated_at=na_context_updated or None,
    )


@router.patch("/{workspace_id}", summary="更新工作区", response_model=WorkspaceDetail)
@require_role(Role.Admin)
async def update_workspace(
    workspace_id: int,
    body: WorkspaceUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceDetail:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    update_fields: List[str] = ["update_time"]
    if body.name is not None:
        conflict = await DBWorkspace.get_or_none(name=body.name)
        if conflict and conflict.id != workspace_id:
            raise ConflictError(resource=f"工作区名称 '{body.name}'")
        ws.name = body.name
        update_fields.append("name")
    if body.description is not None:
        ws.description = body.description
        update_fields.append("description")
    if body.sandbox_image is not None:
        ws.sandbox_image = body.sandbox_image
        update_fields.append("sandbox_image")
    if body.sandbox_version is not None:
        ws.sandbox_version = body.sandbox_version
        update_fields.append("sandbox_version")
    if body.runtime_policy is not None:
        ws.runtime_policy = body.runtime_policy
        update_fields.append("runtime_policy")

    await ws.save(update_fields=update_fields)
    # 若 runtime_policy 更新，即时刷新 CLAUDE.md（bind mount 无需重建容器）
    if "runtime_policy" in update_fields:
        WorkspaceService.update_claude_md(ws)
    return await _detail_async(ws)


@router.delete("/{workspace_id}", summary="删除工作区", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def delete_workspace(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    if ws.status == "active" and ws.container_name:
        await SandboxContainerManager.stop(ws)

    # 清理工作区相关的结构化记忆
    try:
        from nekro_agent.models.db_mem_entity import DBMemEntity
        from nekro_agent.models.db_mem_paragraph import DBMemParagraph
        from nekro_agent.models.db_mem_reinforcement_log import DBMemReinforcementLog
        from nekro_agent.models.db_mem_relation import DBMemRelation

        await DBMemReinforcementLog.filter(workspace_id=workspace_id).delete()
        await DBMemRelation.filter(workspace_id=workspace_id).delete()
        await DBMemEntity.filter(workspace_id=workspace_id).delete()
        await DBMemParagraph.filter(workspace_id=workspace_id).delete()
        await memory_qdrant_manager.delete_by_workspace(workspace_id)
        logger.info(f"工作区 {workspace_id} 的记忆数据已清理")
    except Exception as e:
        logger.warning(f"清理工作区记忆失败（非致命）: workspace_id={workspace_id}, error={e}")

    await ws.delete()
    return ActionOkResponse(ok=True)


# ─────────────────────────────────────────────────────────────
# 频道绑定
# ─────────────────────────────────────────────────────────────


@router.get("/{workspace_id}/channels", summary="获取已绑定频道", response_model=BoundChannelsResponse)
@require_role(Role.Admin)
async def get_bound_channels(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> BoundChannelsResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    channels = await WorkspaceService.get_bound_channels(workspace_id)
    annotations = WorkspaceService.get_channel_annotations(ws)
    bound_chat_keys = [ch.chat_key for ch in channels]
    primary_key = WorkspaceService.get_primary_channel_chat_key(ws, bound_chat_keys)
    items: List[BoundChannelInfo] = []
    for ch in channels:
        ann = annotations.get(ch.chat_key)
        items.append(
            BoundChannelInfo(
                chat_key=ch.chat_key,
                description=ann.description if ann else "",
                is_primary=(ch.chat_key == primary_key),
            )
        )
    return BoundChannelsResponse(channels=items)


@router.put("/{workspace_id}/channel-annotations", summary="更新频道注解", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def update_channel_annotation(
    workspace_id: int,
    body: ChannelAnnotationUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    # 验证 chat_key 确实绑定到此工作区
    channels = await WorkspaceService.get_bound_channels(workspace_id)
    bound_keys = {ch.chat_key for ch in channels}
    if body.chat_key not in bound_keys:
        from nekro_agent.schemas.errors import ValidationError as AppValidationError

        raise AppValidationError(reason=f"频道 {body.chat_key} 未绑定到此工作区")
    await WorkspaceService.update_channel_annotation(ws, body.chat_key, body.description, body.is_primary)
    return ActionOkResponse(ok=True)


@router.post("/{workspace_id}/channels", summary="绑定频道到工作区", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def bind_channel(
    workspace_id: int,
    body: ChannelBindRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    await WorkspaceService.bind_channel(ws, body.chat_key)
    return ActionOkResponse(ok=True)


@router.delete(
    "/{workspace_id}/channels/{chat_key}",
    summary="解绑频道",
    response_model=ActionOkResponse,
)
@require_role(Role.Admin)
async def unbind_channel(
    workspace_id: int,
    chat_key: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    await WorkspaceService.unbind_channel(ws, chat_key)
    return ActionOkResponse(ok=True)


# ─────────────────────────────────────────────────────────────
# 沙盒生命周期
# ─────────────────────────────────────────────────────────────


@router.post("/{workspace_id}/sandbox/start", summary="启动沙盒容器", response_model=WorkspaceDetail)
@require_role(Role.Admin)
async def start_sandbox(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceDetail:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if ws.status == "active":
        raise ValidationError(reason="工作区容器已在运行中")
    try:
        ws = await SandboxContainerManager.create_and_start(ws)
    except ImageNotFoundError as e:
        raise ValidationError(reason=f"镜像 {e.image} 在本地不存在，请先在概览页拉取镜像后再启动容器")
    await publish_system_event(
        WorkspaceStatusEvent(
            workspace_id=ws.id,
            status=ws.status,  # type: ignore[arg-type]
            name=ws.name,
            container_name=ws.container_name,
            host_port=ws.host_port,
        )
    )
    return await _detail_async(ws)


@router.post("/{workspace_id}/sandbox/stop", summary="停止沙盒容器", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def stop_sandbox(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    await SandboxContainerManager.stop(ws)
    await ws.refresh_from_db()
    await publish_system_event(
        WorkspaceStatusEvent(
            workspace_id=ws.id,
            status=ws.status,  # type: ignore[arg-type]
            name=ws.name,
            container_name=ws.container_name,
            host_port=ws.host_port,
        )
    )
    return ActionOkResponse(ok=True)


@router.post("/{workspace_id}/sandbox/restart", summary="重启沙盒容器", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def restart_sandbox(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if not ws.container_name:
        raise ValidationError(reason="工作区尚无运行中的容器")
    await SandboxContainerManager.restart(ws)
    # restart() 内部会在健康检查失败时修改 status，需要重新查询
    await ws.refresh_from_db()
    await publish_system_event(
        WorkspaceStatusEvent(
            workspace_id=ws.id,
            status=ws.status,  # type: ignore[arg-type]
            name=ws.name,
            container_name=ws.container_name,
            host_port=ws.host_port,
        )
    )
    return ActionOkResponse(ok=True)


@router.post("/{workspace_id}/sandbox/rebuild", summary="重建沙盒容器", response_model=WorkspaceDetail)
@require_role(Role.Admin)
async def rebuild_sandbox(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceDetail:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    try:
        ws = await SandboxContainerManager.rebuild(ws)
    except ImageNotFoundError as e:
        raise ValidationError(reason=f"镜像 {e.image} 在本地不存在，请先在概览页拉取镜像后再重建容器")
    await publish_system_event(
        WorkspaceStatusEvent(
            workspace_id=ws.id,
            status=ws.status,  # type: ignore[arg-type]
            name=ws.name,
            container_name=ws.container_name,
            host_port=ws.host_port,
        )
    )
    return await _detail_async(ws)


# ─────────────────────────────────────────────────────────────
# 沙盒镜像管理
# ─────────────────────────────────────────────────────────────


class ImageCheckResponse(BaseModel):
    image: str
    exists: bool


@router.get("/{workspace_id}/sandbox/image/check", summary="检查沙盒镜像是否存在", response_model=ImageCheckResponse)
@require_role(Role.Admin)
async def check_sandbox_image(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ImageCheckResponse:
    from nekro_agent.core.config import config as app_config

    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    image_name = ws.sandbox_image or app_config.CC_SANDBOX_IMAGE
    image_tag = ws.sandbox_version or app_config.CC_SANDBOX_IMAGE_TAG
    image = f"{image_name}:{image_tag}"
    exists = await SandboxContainerManager.check_image_exists(image)
    return ImageCheckResponse(image=image, exists=exists)


@router.post("/{workspace_id}/sandbox/image/pull/stream", summary="拉取沙盒镜像（SSE 流式进度）")
@require_role(Role.Admin)
async def pull_sandbox_image_stream(
    request: Request,
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> EventSourceResponse:
    from nekro_agent.core.config import config as app_config

    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    image_name = ws.sandbox_image or app_config.CC_SANDBOX_IMAGE
    image_tag = ws.sandbox_version or app_config.CC_SANDBOX_IMAGE_TAG
    image = f"{image_name}:{image_tag}"

    async def event_generator() -> AsyncGenerator[str, None]:
        docker = aiodocker.Docker()
        # 记录每个 layer 当前状态，避免重复推送相同状态
        layer_status: dict[str, str] = {}
        # 需要立即推送的终态/关键状态
        _TERMINAL_STATUSES = {"Pull complete", "Already exists", "Download complete", "Verifying Checksum"}
        try:
            async for progress in docker.images.pull(image, stream=True):
                if is_shutting_down() or await request.is_disconnected():
                    return
                if not isinstance(progress, dict):
                    continue
                status: str = progress.get("status", "")
                layer_id: str = progress.get("id", "")
                # 无 layer ID 的全局消息（Digest、Status）直接推送
                if not layer_id:
                    if status:
                        yield json.dumps({"type": "progress", "layer": "", "status": status})
                    continue
                prev = layer_status.get(layer_id)
                # 状态未变化且不是终态，跳过
                if prev == status and status not in _TERMINAL_STATUSES:
                    continue
                layer_status[layer_id] = status
                yield json.dumps({"type": "progress", "layer": layer_id, "status": status})
            if is_shutting_down() or await request.is_disconnected():
                return
            yield json.dumps({"type": "done", "data": f"镜像 {image} 拉取完成"})
        except aiodocker.exceptions.DockerError as e:
            yield json.dumps({"type": "error", "data": f"拉取失败：{e}"})
        except Exception as e:
            yield json.dumps({"type": "error", "data": f"拉取异常：{e}"})
        finally:
            try:
                await docker.close()
            except Exception:
                pass

    return EventSourceResponse(event_generator())


@router.get("/{workspace_id}/sandbox/status", summary="获取沙盒状态", response_model=SandboxStatus)
@require_role(Role.Admin)
async def get_sandbox_status(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> SandboxStatus:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    sandbox_info: Dict[str, Any] = {}
    cc_version: Optional[str] = None
    claude_code_version: Optional[str] = None
    if ws.status == "active":
        client = CCSandboxClient(ws)
        try:
            sandbox_info = await client.get_sandbox_status()
        except Exception as e:
            logger.debug(f"获取沙盒状态失败（容器可能未就绪）: {ws.container_name}: {e}")
        try:
            versions = await client.get_sandbox_versions()
            cc_version = versions.get("cc_version")
            claude_code_version = versions.get("claude_code_version")
        except Exception as e:
            logger.debug(f"获取沙盒版本失败: {ws.container_name}: {e}")

    return SandboxStatus(
        workspace_id=ws.id,
        status=ws.status,
        container_name=ws.container_name,
        container_id=ws.container_id,
        host_port=ws.host_port,
        session_id=sandbox_info.get("session_id"),
        tools=sandbox_info.get("tools"),
        cc_version=cc_version,
        claude_code_version=claude_code_version,
    )


@router.get("/{workspace_id}/sandbox/logs", summary="获取沙盒容器日志", response_model=LogsOkResponse)
@require_role(Role.Admin)
async def get_sandbox_logs(
    workspace_id: int,
    tail: int = Query(default=100, ge=1, le=1000),
    _current_user: DBUser = Depends(get_current_active_user),
) -> LogsOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    logs = await SandboxContainerManager.get_logs(ws, tail=tail)
    return LogsOkResponse(logs=logs)


# ─────────────────────────────────────────────────────────────
# 会话管理
# ─────────────────────────────────────────────────────────────


@router.post("/{workspace_id}/session/reset", summary="重置会话", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def reset_session(
    workspace_id: int,
    session_id: str = "default",
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if ws.status != "active":
        raise ValidationError(reason="工作区未运行，无法重置会话")
    client = CCSandboxClient(ws)
    try:
        await client.reset_session(session_id)
    except CCSandboxError as e:
        raise OperationFailedError(operation="重置会话", detail=str(e)) from e

    # 清理 NA 侧的对话上下文缓存，避免 Agent 误以为 CC 仍保留之前的会话记录
    # 1. 写入 SYSTEM CommLog 标记会话已重置（让 get_cc_context 近期记录中包含此通知）
    from nekro_agent.models.db_workspace_comm_log import DBWorkspaceCommLog
    from nekro_agent.services.workspace import comm_broadcast

    try:
        sys_log = await DBWorkspaceCommLog.create(
            workspace_id=workspace_id,
            direction="SYSTEM",
            source_chat_key="",
            content=(
                "[会话重置] CC Workspace 的会话已被用户重置。"
                "CC 不再保留此前任何对话记录和上下文，"
                "后续委托请视为全新会话。"
            ),
            is_streaming=False,
            task_id=None,
        )
        await comm_broadcast.publish(
            workspace_id,
            _comm_log_to_entry(sys_log),
        )
    except Exception as e:
        logger.warning(f"写入会话重置 CommLog 失败: {e}")

    # 2. 清理所有绑定频道的 last_cc_task_prompt 缓存
    from nekro_agent.models.db_chat_channel import DBChatChannel
    from nekro_agent.models.db_plugin_data import DBPluginData

    try:
        bound_channels = await DBChatChannel.filter(workspace_id=workspace_id).all()
        if bound_channels:
            chat_keys = [ch.chat_key for ch in bound_channels]
            # plugin_key 格式为 "author.module_name"，cc_workspace 插件的 key 是 "KroMiose.cc_workspace"
            deleted_count = await DBPluginData.filter(
                plugin_key="KroMiose.cc_workspace",
                target_chat_key__in=chat_keys,
                data_key="last_cc_task_prompt",
            ).delete()
            if deleted_count:
                logger.info(f"会话重置：已清理 {deleted_count} 条 last_cc_task_prompt 缓存 " f"workspace_id={workspace_id}")
    except Exception as e:
        logger.warning(f"清理 last_cc_task_prompt 缓存失败: {e}")

    return ActionOkResponse(ok=True)


# ─────────────────────────────────────────────────────────────
# 工具管理
# ─────────────────────────────────────────────────────────────


@router.get("/{workspace_id}/tools", summary="获取工具列表", response_model=ToolsResponse)
@require_role(Role.Admin)
async def get_tools(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ToolsResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if ws.status != "active":
        raise ValidationError(reason="工作区未运行，无法获取工具列表")
    client = CCSandboxClient(ws)
    try:
        tools = await client.get_tools()
    except CCSandboxError as e:
        raise OperationFailedError(operation="获取工具列表", detail=str(e)) from e
    return ToolsResponse(tools=tools)


@router.post("/{workspace_id}/tools/refresh", summary="刷新工具列表", response_model=ToolsResponse)
@require_role(Role.Admin)
async def refresh_tools(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ToolsResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if ws.status != "active":
        raise ValidationError(reason="工作区未运行，无法刷新工具")
    client = CCSandboxClient(ws)
    try:
        tools = await client.refresh_tools()
    except CCSandboxError as e:
        raise OperationFailedError(operation="刷新工具列表", detail=str(e)) from e
    return ToolsResponse(tools=tools)


# ─────────────────────────────────────────────────────────────
# Skills 管理
# ─────────────────────────────────────────────────────────────


@router.get("/{workspace_id}/skills", summary="获取工作区已选 skills", response_model=WorkspaceSkillsResponse)
@require_role(Role.Admin)
async def get_workspace_skills(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceSkillsResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    skills: List[str] = ws.metadata.get("skills", [])
    return WorkspaceSkillsResponse(skills=skills)


@router.put("/{workspace_id}/skills", summary="更新工作区 skills", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def update_workspace_skills(
    workspace_id: int,
    body: WorkspaceSkillsUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    metadata = dict(ws.metadata)
    metadata["skills"] = body.skills
    ws.metadata = metadata
    await ws.save(update_fields=["metadata", "update_time"])

    await WorkspaceService.sync_skills(ws)
    return ActionOkResponse(ok=True)


@router.post(
    "/{workspace_id}/skills/{skill_name:path}/sync", summary="从全局库重新同步单个 skill", response_model=ActionOkResponse
)
@require_role(Role.Admin)
async def sync_workspace_skill(
    workspace_id: int,
    skill_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    ok = await WorkspaceService.sync_single_skill(ws, skill_name)
    if not ok:
        raise OperationFailedError(operation=f"同步技能 {skill_name}（未选中或源目录不存在）")
    return ActionOkResponse(ok=True)


# ─────────────────────────────────────────────────────────────
# CLAUDE.md 查看与自定义追加
# ─────────────────────────────────────────────────────────────


@router.get("/{workspace_id}/claude-md", summary="获取 CLAUDE.md 内容及自定义追加", response_model=ClaudeMdResponse)
@require_role(Role.Admin)
async def get_claude_md(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ClaudeMdResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    content = WorkspaceService._generate_claude_md_content(ws)
    extra: str = (ws.metadata or {}).get("claude_md_extra") or ""
    return ClaudeMdResponse(content=content, extra=extra)


@router.put("/{workspace_id}/claude-md-extra", summary="更新自定义追加提示词", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def update_claude_md_extra(
    workspace_id: int,
    body: ClaudeMdExtraUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    metadata = dict(ws.metadata or {})
    metadata["claude_md_extra"] = body.extra
    ws.metadata = metadata
    await ws.save(update_fields=["metadata", "update_time"])
    WorkspaceService.update_claude_md(ws)
    return ActionOkResponse(ok=True)


@router.get("/{workspace_id}/prompt-composer", summary="获取工作区提示词编排信息", response_model=PromptComposerResponse)
@require_role(Role.Admin)
async def get_prompt_composer(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> PromptComposerResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    prompt_layers = _get_prompt_layers_metadata(ws)
    claude_md_extra: str = (ws.metadata or {}).get("claude_md_extra") or ""
    na_context_body, na_context_updated = WorkspaceService.read_na_context(workspace_id)

    shared_layer = prompt_layers.get("shared_manual_rules") if isinstance(prompt_layers.get("shared_manual_rules"), dict) else {}
    na_layer = prompt_layers.get("na_manual_rules") if isinstance(prompt_layers.get("na_manual_rules"), dict) else {}
    na_context_meta = prompt_layers.get("na_context_meta") if isinstance(prompt_layers.get("na_context_meta"), dict) else {}

    return PromptComposerResponse(
        claude_md_content=WorkspaceService._generate_claude_md_content(ws),
        claude_md_extra=claude_md_extra,
        na_context=_build_prompt_layer_item(
            key="na_context",
            title="协作现状摘要",
            target="na",
            maintainer="manual+cc",
            content=na_context_body,
            description="给 NA 理解 CC 当前工作区状态使用，CC 在后续任务中可能继续维护。",
            editable_by_cc=True,
            auto_inject=True,
            updated_at=na_context_updated or na_context_meta.get("last_manual_override_at"),
            updated_by=na_context_meta.get("last_editor") or "cc",
        ),
        shared_manual_rules=_build_prompt_layer_item(
            key="shared_manual_rules",
            title="共享固定事实",
            target="shared",
            maintainer="manual",
            content=str(shared_layer.get("content") or ""),
            description="同时提供给 NA 与 CC 的稳定知识、明确约束和人工确认事实。",
            editable_by_cc=False,
            auto_inject=True,
            updated_at=shared_layer.get("updated_at"),
            updated_by=shared_layer.get("updated_by") or "manual",
        ),
        na_manual_rules=_build_prompt_layer_item(
            key="na_manual_rules",
            title="NA 专属规则",
            target="na",
            maintainer="manual",
            content=str(na_layer.get("content") or ""),
            description="仅提供给 NA 的长期提示或纠偏规则，不会暴露给 CC。",
            editable_by_cc=False,
            auto_inject=True,
            updated_at=na_layer.get("updated_at"),
            updated_by=na_layer.get("updated_by") or "manual",
        ),
    )


@router.put("/{workspace_id}/prompt-composer/na-context", summary="更新协作现状摘要", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def update_prompt_composer_na_context(
    workspace_id: int,
    body: PromptLayerUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    WorkspaceService.write_na_context(workspace_id, body.content, updated_by="manual")
    metadata = dict(ws.metadata or {})
    prompt_layers = _get_prompt_layers_metadata(ws)
    prompt_layers["na_context_meta"] = {
        **(prompt_layers.get("na_context_meta") if isinstance(prompt_layers.get("na_context_meta"), dict) else {}),
        "last_editor": "manual",
        "last_manual_override_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata["prompt_layers"] = prompt_layers
    ws.metadata = metadata
    await ws.save(update_fields=["metadata", "update_time"])
    return ActionOkResponse(ok=True)


@router.put("/{workspace_id}/prompt-composer/shared-manual-rules", summary="更新共享固定事实", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def update_prompt_composer_shared_rules(
    workspace_id: int,
    body: PromptLayerUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    metadata = dict(ws.metadata or {})
    prompt_layers = _get_prompt_layers_metadata(ws)
    prompt_layers["shared_manual_rules"] = {
        "content": body.content,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": "manual",
    }
    metadata["prompt_layers"] = prompt_layers
    ws.metadata = metadata
    await ws.save(update_fields=["metadata", "update_time"])
    return ActionOkResponse(ok=True)


@router.put("/{workspace_id}/prompt-composer/na-manual-rules", summary="更新 NA 专属规则", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def update_prompt_composer_na_rules(
    workspace_id: int,
    body: PromptLayerUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    metadata = dict(ws.metadata or {})
    prompt_layers = _get_prompt_layers_metadata(ws)
    prompt_layers["na_manual_rules"] = {
        "content": body.content,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": "manual",
    }
    metadata["prompt_layers"] = prompt_layers
    ws.metadata = metadata
    await ws.save(update_fields=["metadata", "update_time"])
    return ActionOkResponse(ok=True)


# ─────────────────────────────────────────────────────────────
# 动态 Skill 管理
# ─────────────────────────────────────────────────────────────


class DynamicSkillItem(BaseModel):
    dir_name: str
    name: str
    description: str


class DynamicSkillListResponse(BaseModel):
    total: int
    items: List[DynamicSkillItem]


class DynamicSkillContent(BaseModel):
    dir_name: str
    content: str


class DynamicSkillWriteBody(BaseModel):
    content: str


@router.get("/{workspace_id}/dynamic-skills", summary="列出工作区动态 skill", response_model=DynamicSkillListResponse)
@require_role(Role.Admin)
async def list_dynamic_skills(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> DynamicSkillListResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    raw = WorkspaceService.list_dynamic_skills(workspace_id)
    items = [DynamicSkillItem(dir_name=s["dir_name"], name=s["name"], description=s["description"]) for s in raw]
    return DynamicSkillListResponse(total=len(items), items=items)


@router.get("/{workspace_id}/dynamic-skills/{dir_name}", summary="获取动态 skill 内容", response_model=DynamicSkillContent)
@require_role(Role.Admin)
async def get_dynamic_skill(
    workspace_id: int,
    dir_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> DynamicSkillContent:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    content = WorkspaceService.read_dynamic_skill(workspace_id, dir_name)
    if content is None:
        raise NotFoundError(resource=f"动态 skill '{dir_name}'")
    return DynamicSkillContent(dir_name=dir_name, content=content)


@router.put("/{workspace_id}/dynamic-skills/{dir_name}", summary="创建/更新动态 skill", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def put_dynamic_skill(
    workspace_id: int,
    dir_name: str,
    body: DynamicSkillWriteBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if not dir_name or "/" in dir_name or ".." in dir_name or dir_name.startswith("."):
        raise ValidationError(reason=f"非法 skill 名称: {dir_name!r}")
    try:
        WorkspaceService.write_dynamic_skill(workspace_id, dir_name, body.content)
    except ValueError as e:
        raise ValidationError(reason=str(e)) from e
    return ActionOkResponse(ok=True)


@router.delete("/{workspace_id}/dynamic-skills/{dir_name}", summary="删除动态 skill", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def delete_dynamic_skill(
    workspace_id: int,
    dir_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    deleted = WorkspaceService.delete_dynamic_skill(workspace_id, dir_name)
    if not deleted:
        raise NotFoundError(resource=f"动态 skill '{dir_name}'")
    return ActionOkResponse(ok=True)


class PromoteBody(BaseModel):
    force: bool = False


@router.post(
    "/{workspace_id}/dynamic-skills/{dir_name}/promote",
    summary="晋升动态 skill 为全局用户 skill",
    response_model=ActionOkResponse,
)
@require_role(Role.Admin)
async def promote_dynamic_skill(
    workspace_id: int,
    dir_name: str,
    body: Optional[PromoteBody] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    force = body.force if body else False
    try:
        WorkspaceService.promote_dynamic_skill(workspace_id, dir_name, force=force)
    except ValueError as e:
        raise ValidationError(reason=str(e)) from e
    return ActionOkResponse(ok=True, message=f"已晋升 '{dir_name}' 为全局用户 skill")


# ── 动态 skill 目录/文件浏览 ──────────────────────────────────


class DynamicSkillDirEntry(BaseModel):
    name: str
    rel_path: str
    type: Literal["file", "dir"]
    size: Optional[int] = None


class DynamicSkillDirResponse(BaseModel):
    entries: List[DynamicSkillDirEntry]


class DynamicSkillFileBody(BaseModel):
    rel_path: str
    content: str


def _list_dynamic_dir(root: Any, current: Any, max_depth: int = 5) -> List[DynamicSkillDirEntry]:
    """递归列出目录内所有文件和子目录（跳过 .git 等隐藏目录）"""
    entries: List[DynamicSkillDirEntry] = []
    if max_depth <= 0:
        return entries
    try:
        items = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return entries
    for item in items:
        if item.name.startswith("."):
            continue
        rel = str(item.relative_to(root))
        if item.is_dir():
            entries.append(DynamicSkillDirEntry(name=item.name, rel_path=rel, type="dir"))
            entries.extend(_list_dynamic_dir(root, item, max_depth - 1))
        elif item.is_file():
            try:
                size = item.stat().st_size
            except OSError:
                size = None
            entries.append(DynamicSkillDirEntry(name=item.name, rel_path=rel, type="file", size=size))
    return entries


@router.get(
    "/{workspace_id}/dynamic-skills/{dir_name}/dir",
    summary="列出动态 skill 目录内所有文件",
    response_model=DynamicSkillDirResponse,
)
@require_role(Role.Admin)
async def list_dynamic_skill_dir(
    workspace_id: int,
    dir_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> DynamicSkillDirResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    skill_dir = WorkspaceService.get_workspace_skills_dir(workspace_id) / dir_name
    if not WorkspaceService._is_workspace_local_dynamic_skill(skill_dir):
        raise NotFoundError(resource=f"动态 skill '{dir_name}'")
    entries = await asyncio.to_thread(_list_dynamic_dir, skill_dir, skill_dir)
    return DynamicSkillDirResponse(entries=entries)


@router.get(
    "/{workspace_id}/dynamic-skills/{dir_name}/file",
    summary="读取动态 skill 目录内指定文件",
    response_model=DynamicSkillContent,
)
@require_role(Role.Admin)
async def get_dynamic_skill_file(
    workspace_id: int,
    dir_name: str,
    rel_path: str = Query(..., description="相对于 skill 根目录的文件路径"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> DynamicSkillContent:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if ".." in rel_path.split("/"):
        raise ValidationError(reason="路径不合法")
    skill_dir = WorkspaceService.get_workspace_skills_dir(workspace_id) / dir_name
    if not WorkspaceService._is_workspace_local_dynamic_skill(skill_dir):
        raise NotFoundError(resource=f"动态 skill '{dir_name}'")
    target = skill_dir / rel_path
    if not target.exists() or not target.is_file():
        raise NotFoundError(resource=f"文件 '{rel_path}'")
    content = await asyncio.to_thread(target.read_text, "utf-8")
    return DynamicSkillContent(dir_name=dir_name, content=content)


@router.put(
    "/{workspace_id}/dynamic-skills/{dir_name}/file",
    summary="保存动态 skill 目录内指定文件",
    response_model=ActionOkResponse,
)
@require_role(Role.Admin)
async def save_dynamic_skill_file(
    workspace_id: int,
    dir_name: str,
    body: DynamicSkillFileBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if ".." in body.rel_path.split("/"):
        raise ValidationError(reason="路径不合法")
    skill_dir = WorkspaceService.get_workspace_skills_dir(workspace_id) / dir_name
    if not WorkspaceService._is_workspace_local_dynamic_skill(skill_dir):
        raise NotFoundError(resource=f"动态 skill '{dir_name}'")
    target = skill_dir / body.rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(target.write_text, body.content, "utf-8")
    return ActionOkResponse(ok=True)


# ─────────────────────────────────────────────────────────────
# MCP 配置
# ─────────────────────────────────────────────────────────────
@router.get("/{workspace_id}/mcp", summary="获取工作区 MCP 配置", response_model=McpConfigResponse)
@require_role(Role.Admin)
async def get_mcp_config(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> McpConfigResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    mcp_config: Dict[str, Any] = ws.metadata.get("mcp_config", {"mcpServers": {}})
    return McpConfigResponse(mcp_config=mcp_config)


@router.put("/{workspace_id}/mcp", summary="更新工作区 MCP 配置", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def update_mcp_config(
    workspace_id: int,
    body: McpConfigUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    await WorkspaceService.update_mcp_config(ws, body.mcp_config)
    return ActionOkResponse(ok=True)


class McpServersResponse(BaseModel):
    servers: List[McpServerConfig]


@router.get("/{workspace_id}/mcp/servers", summary="获取结构化 MCP 服务器列表", response_model=McpServersResponse)
@require_role(Role.Admin)
async def list_mcp_servers(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> McpServersResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    servers = WorkspaceService.list_mcp_servers(ws)
    return McpServersResponse(servers=servers)


@router.post("/{workspace_id}/mcp/servers", summary="添加 MCP 服务器", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def add_mcp_server(
    workspace_id: int,
    server: McpServerConfig,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    await WorkspaceService.add_mcp_server(ws, server)
    return ActionOkResponse(ok=True)


@router.put("/{workspace_id}/mcp/servers/{server_name}", summary="更新 MCP 服务器", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def update_mcp_server(
    workspace_id: int,
    server_name: str,
    server: McpServerConfig,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    await WorkspaceService.update_mcp_server(ws, server_name, server)
    return ActionOkResponse(ok=True)


@router.delete("/{workspace_id}/mcp/servers/{server_name}", summary="删除 MCP 服务器", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def delete_mcp_server(
    workspace_id: int,
    server_name: str,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    await WorkspaceService.remove_mcp_server(ws, server_name)
    return ActionOkResponse(ok=True)


@router.post("/{workspace_id}/mcp/sync", summary="同步 MCP 配置到沙盒", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def sync_mcp_to_sandbox(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    """将数据库中的 MCP 配置重新写入工作区目录的 .mcp.json，无需重启容器即可生效"""
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    mcp_config = (ws.metadata or {}).get("mcp_config", {"mcpServers": {}})
    await WorkspaceService.update_mcp_config(ws, mcp_config)
    return ActionOkResponse(ok=True)


# ─────────────────────────────────────────────────────────────
# CC 模型预设
# ─────────────────────────────────────────────────────────────


class WorkspaceCCPresetBody(BaseModel):
    cc_model_preset_id: Optional[int] = None


@router.put("/{workspace_id}/cc-model-preset", summary="设置工作区 CC 模型预设")
@require_role(Role.Admin)
async def set_workspace_cc_preset(
    workspace_id: int,
    body: WorkspaceCCPresetBody,
    _current_user: DBUser = Depends(get_current_active_user),
):
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    metadata = dict(ws.metadata or {})
    metadata["cc_model_preset_id"] = body.cc_model_preset_id
    ws.metadata = metadata
    await ws.save(update_fields=["metadata", "update_time"])

    # 解析预设并立刻刷新磁盘配置文件，使运行中的容器下一条消息即可生效（无需重建）
    from nekro_agent.core.cc_model_presets import cc_presets_store

    cc_preset = cc_presets_store.get_by_id(body.cc_model_preset_id) if body.cc_model_preset_id else None
    if cc_preset is None:
        cc_preset = cc_presets_store.get_default()
    WorkspaceService.update_workspace_settings(ws, cc_preset)

    return {"ok": True}


@router.get("/{workspace_id}/cc-model-preset", summary="获取工作区 CC 模型预设配置")
@require_role(Role.Admin)
async def get_workspace_cc_preset(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
):
    from nekro_agent.core.cc_model_presets import cc_presets_store

    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    preset_id = (ws.metadata or {}).get("cc_model_preset_id")
    if not preset_id:
        default = cc_presets_store.get_default()
        if default:
            return {"preset_id": default.id, "config_json": default.to_config_json()}
        return {"preset_id": None, "config_json": None}
    p = cc_presets_store.get_by_id(int(preset_id))
    if not p:
        return {"preset_id": None, "config_json": None}
    return {"preset_id": p.id, "config_json": p.to_config_json()}


# ─────────────────────────────────────────────────────────────
# 容器日志 SSE 流
# ─────────────────────────────────────────────────────────────


@router.get("/{workspace_id}/sandbox/logs/stream", summary="流式推送容器日志")
@require_role(Role.Admin)
async def stream_sandbox_logs(
    request: Request,
    workspace_id: int,
    tail: int = Query(default=200, ge=1, le=2000),
    _current_user: DBUser = Depends(get_current_active_user),
) -> EventSourceResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    # _SENTINEL 用于通知生成器日志 Task 已结束
    _SENTINEL = object()

    async def _pump_docker_logs(
        container_name: str,
        current_tail: int,
        queue: "asyncio.Queue[object]",
    ) -> None:
        """在独立 Task 中消费 Docker log stream，将数据写入 Queue。
        Task 被取消时，aiodocker 的 async for 会收到 CancelledError 并退出。
        """
        docker = aiodocker.Docker()
        try:
            container = await docker.containers.get(container_name)
            async for chunk in container.log(stdout=True, stderr=True, follow=True, tail=current_tail):
                await queue.put(json.dumps({"type": "log", "data": chunk}))
        except asyncio.CancelledError:
            raise
        except aiodocker.exceptions.DockerError as e:
            err_msg = str(e)
            if "No such container" in err_msg or "404" in err_msg:
                await queue.put(json.dumps({"type": "info", "data": "[容器已被删除，等待重建...]\n"}))
            else:
                await queue.put(json.dumps({"type": "error", "data": f"[Docker 错误: {e}]\n"}))
        except Exception as e:
            await queue.put(json.dumps({"type": "error", "data": f"[错误: {e}]\n"}))
        finally:
            try:
                await docker.close()
            except Exception:
                pass
            # 通知消费方本次 Task 已结束
            await queue.put(_SENTINEL)

    async def event_generator() -> AsyncGenerator[str, None]:
        # 记录上一次跟踪的容器名，用于检测容器切换
        last_container_name: Optional[str] = None
        # 是否已提示过"等待容器"
        waiting_notified = False
        # 首次连接时使用 tail 参数，容器切换后从头跟踪新容器
        current_tail = tail

        while True:
            # 检查客户端是否已断开
            if await request.is_disconnected():
                return

            # 每次循环都重新查询数据库，获取最新容器名
            ws_current = await DBWorkspace.get_or_none(id=workspace_id)
            if not ws_current:
                yield json.dumps({"type": "error", "data": "[工作区已不存在，日志流终止]\n"})
                return

            current_container = ws_current.container_name

            if not current_container:
                # 容器不存在（可能正在重建），等待并提示
                if not waiting_notified:
                    msg = (
                        "[容器正在重建，等待新容器启动...]\n"
                        if last_container_name is not None
                        else "[容器未运行，等待启动...]\n"
                    )
                    yield json.dumps({"type": "info", "data": msg})
                    waiting_notified = True
                    last_container_name = None
                await asyncio.sleep(2)
                continue

            waiting_notified = False  # 容器出现后重置提示标志

            if current_container != last_container_name:
                # 检测到新容器（首次或切换），提示用户
                if last_container_name is not None:
                    yield json.dumps({"type": "info", "data": f"[检测到新容器 {current_container}，开始跟踪日志...]\n"})
                    current_tail = 50  # 新容器只取最近 50 行，避免刷屏
                last_container_name = current_container

            # 启动独立 Task 消费 Docker log stream，通过 Queue 传递数据
            queue: asyncio.Queue[object] = asyncio.Queue(maxsize=256)
            log_task = asyncio.create_task(_pump_docker_logs(current_container, current_tail, queue))
            try:
                while True:
                    # 检查客户端是否已断开
                    if await request.is_disconnected():
                        return
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=2.0)
                    except asyncio.TimeoutError:
                        continue
                    if item is _SENTINEL:
                        # Task 正常结束（容器停止）
                        break
                    yield str(item)
            finally:
                # 无论何种退出原因（断连、CancelledError、正常结束）都取消 Task
                if not log_task.done():
                    log_task.cancel()
                    try:
                        await log_task
                    except (asyncio.CancelledError, Exception):
                        pass

            # 容器停止后等待重启
            yield json.dumps({"type": "info", "data": "[容器已停止，等待重启...]\n"})
            last_container_name = None
            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())


# ─────────────────────────────────────────────────────────────
# 容器终端 WebSocket
# ─────────────────────────────────────────────────────────────


@router.websocket("/{workspace_id}/sandbox/terminal")
async def workspace_terminal(
    websocket: WebSocket,
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> None:
    await websocket.accept()

    if _current_user.perm_level < Role.Admin:
        await websocket.send_text(json.dumps({"type": "error", "data": "权限不足\r\n"}))
        await websocket.close(code=4003)
        return
    ws_db = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws_db or not ws_db.container_name:
        await websocket.send_text(json.dumps({"type": "error", "data": "容器未运行\r\n"}))
        await websocket.close(code=4004)
        return

    master_fd, slave_fd = pty.openpty()
    # 设置初始终端大小
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))

    # 尝试 bash，不存在则用 sh；-w 指定初始工作目录为工作区目录
    shell_cmd = ["docker", "exec", "-it", "-w", "/workspace/default", ws_db.container_name, "/bin/bash"]
    proc = subprocess.Popen(
        shell_cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    os.close(slave_fd)

    # 使用事件循环的 add_reader 实现非阻塞异步读取
    loop = asyncio.get_event_loop()
    output_queue: asyncio.Queue[bytes] = asyncio.Queue()

    def _on_readable() -> None:
        try:
            data = os.read(master_fd, 4096)
            if data:
                output_queue.put_nowait(data)
        except OSError:
            loop.remove_reader(master_fd)

    loop.add_reader(master_fd, _on_readable)

    async def _send_output() -> None:
        while True:
            data = await output_queue.get()
            try:
                await websocket.send_text(json.dumps({"type": "output", "data": data.decode("utf-8", errors="replace")}))
            except Exception:
                break

    sender_task = asyncio.create_task(_send_output())

    try:
        while not is_shutting_down():
            try:
                text = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                if proc.poll() is not None:
                    break
                continue
            msg = json.loads(text)
            if msg["type"] == "input":
                os.write(master_fd, msg["data"].encode("utf-8"))
            elif msg["type"] == "resize":
                fcntl.ioctl(
                    master_fd,
                    termios.TIOCSWINSZ,
                    struct.pack("HHHH", msg.get("rows", 24), msg.get("cols", 80), 0, 0),
                )
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        with contextlib.suppress(Exception):
            await websocket.close(code=1012, reason="Server restarting")
        with contextlib.suppress(Exception):
            loop.remove_reader(master_fd)
        sender_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await sender_task
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass
        try:
            os.close(master_fd)
        except OSError:
            pass


# ── 记忆系统端点 ────────────────────────────────────────────────────────────

class MemoryParagraphData(BaseModel):
    id: int
    summary: str
    content: str
    memory_source: str
    cognitive_type: str
    knowledge_type: str
    base_weight: float
    effective_weight: float
    event_time: Optional[str] = None
    origin_kind: str
    origin_chat_key: Optional[str] = None
    create_time: str


class MemoryEntityData(BaseModel):
    id: int
    entity_type: str
    canonical_name: str
    appearance_count: int
    source_hint: str
    update_time: str


class MemoryRelationData(BaseModel):
    id: int
    subject_entity_id: int
    subject_name: str
    predicate: str
    object_entity_id: int
    object_name: str
    memory_source: str
    cognitive_type: str
    base_weight: float
    effective_weight: float
    paragraph_id: Optional[int] = None
    update_time: str


class MemoryDataStats(BaseModel):
    paragraph_count: int
    episodic_count: int
    semantic_count: int
    episode_count: int
    entity_count: int
    relation_count: int
    reinforcement_count_7d: int


class MemoryDataResponse(BaseModel):
    stats: MemoryDataStats
    paragraphs: List[MemoryParagraphData]
    entities: List[MemoryEntityData]
    relations: List[MemoryRelationData]


class MemoryListItem(BaseModel):
    id: int
    memory_type: str
    title: str
    subtitle: str = ""
    status: str
    cognitive_type: Optional[str] = None
    base_weight: Optional[float] = None
    effective_weight: Optional[float] = None
    event_time: Optional[str] = None
    create_time: str
    update_time: str


class MemoryListResponse(BaseModel):
    total: int
    items: List[MemoryListItem]


def _compute_episode_effective_weight(episode: "DBMemEpisode", now_ts: float) -> float:
    base = max(0.1, float(episode.base_weight or 0.0))
    event_time = episode.time_end or episode.time_start
    if event_time is None:
        return base
    age_seconds = max(0.0, now_ts - event_time.timestamp())
    half_life_seconds = max(1.0, 30 * 24 * 3600)
    decay_factor = 2 ** (-age_seconds / half_life_seconds)
    return base * decay_factor


class MemoryDetailResponse(BaseModel):
    memory_type: str
    data: Dict[str, Any]


class MemoryEditBody(BaseModel):
    summary: Optional[str] = None
    content: Optional[str] = None


class MemoryTraceMessage(BaseModel):
    id: int
    message_id: str
    sender_nickname: str
    content_text: str
    send_timestamp: int


class MemoryTraceResponse(BaseModel):
    paragraph: Dict[str, Any]
    messages: List[MemoryTraceMessage]
    entities: List[MemoryEntityData]
    relations: List[MemoryRelationData]


class MemoryPruneResponse(BaseModel):
    paragraphs_pruned: int
    relations_pruned: int
    entities_pruned: int


class MemoryRebuildChannelStatusResponse(BaseModel):
    chat_key: str
    status: str
    upper_bound_message_db_id: int
    initial_cursor_db_id: int
    last_cursor_db_id: int
    message_count_total: int
    messages_processed: int
    completed: bool
    progress_ratio: float
    last_error: Optional[str] = None


class MemoryRebuildStartResponse(BaseModel):
    job_id: str
    reused: bool
    status: str
    message: str


class MemoryRebuildStatusResponse(BaseModel):
    workspace_id: int
    job_id: Optional[str] = None
    is_running: bool
    status: str
    phase: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    cutoff: Optional[str] = None
    semantic_replayed: bool
    cancel_requested: bool = False
    current_chat_key: Optional[str] = None
    last_heartbeat_at: Optional[str] = None
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    overall_progress_percent: float = 0.0
    total_channels: int
    completed_channels: int
    total_messages_processed: int
    channels: List[MemoryRebuildChannelStatusResponse]


class MemoryGraphNode(BaseModel):
    id: str
    memory_type: str
    ref_id: int
    label: str
    subtitle: str = ""
    status: str
    cognitive_type: Optional[str] = None
    weight: float = 0.0
    size: float = 1.0
    importance: float = 0.0
    paragraph_id: Optional[int] = None
    metadata: Dict[str, Any] = {}


class MemoryGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str
    label: str = ""
    weight: float = 0.0
    strength: float = 0.0
    status: str = "active"
    cognitive_type: Optional[str] = None
    metadata: Dict[str, Any] = {}


class MemoryGraphResponse(BaseModel):
    generated_at: str
    node_count: int
    edge_count: int
    nodes: List[MemoryGraphNode]
    edges: List[MemoryGraphEdge]


class MemoryEpisodeDetailResponse(BaseModel):
    id: int
    title: str
    narrative_summary: str
    origin_chat_key: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    paragraph_ids: List[int]
    participant_entity_ids: List[int]
    phase_mapping: Dict[str, List[int]]


async def _ensure_workspace_exists(workspace_id: int) -> DBWorkspace:
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    return workspace


async def _get_memory_target(workspace_id: int, memory_type: str, memory_id: int) -> Any:
    from nekro_agent.models.db_mem_entity import DBMemEntity
    from nekro_agent.models.db_mem_episode import DBMemEpisode
    from nekro_agent.models.db_mem_paragraph import DBMemParagraph
    from nekro_agent.models.db_mem_relation import DBMemRelation

    mapping = {
        "paragraph": DBMemParagraph,
        "entity": DBMemEntity,
        "relation": DBMemRelation,
        "episode": DBMemEpisode,
    }
    model = mapping.get(memory_type)
    if model is None:
        raise ValidationError(reason=f"不支持的记忆类型: {memory_type}")
    target = await model.get_or_none(id=memory_id, workspace_id=workspace_id)
    if target is None:
        raise NotFoundError(resource=f"{memory_type} {memory_id}")
    return target


@router.post("/{workspace_id}/memory/reset", summary="清空工作区记忆库", response_model=ActionOkResponse)
async def reset_memory(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    from nekro_agent.models.db_mem_entity import DBMemEntity
    from nekro_agent.models.db_mem_episode import DBMemEpisode
    from nekro_agent.models.db_mem_paragraph import DBMemParagraph
    from nekro_agent.models.db_mem_reinforcement_log import DBMemReinforcementLog
    from nekro_agent.models.db_mem_relation import DBMemRelation
    from nekro_agent.services.memory.qdrant_manager import memory_qdrant_manager

    await _ensure_workspace_exists(workspace_id)
    paragraph_count = await DBMemParagraph.filter(workspace_id=workspace_id).count()

    await DBMemReinforcementLog.filter(workspace_id=workspace_id).delete()
    await DBMemRelation.filter(workspace_id=workspace_id).delete()
    await DBMemEntity.filter(workspace_id=workspace_id).delete()
    await DBMemEpisode.filter(workspace_id=workspace_id).delete()
    await DBMemParagraph.filter(workspace_id=workspace_id).delete()
    await memory_qdrant_manager.delete_by_workspace(workspace_id)
    return ActionOkResponse(message=f"结构化记忆已清空，共删除 {paragraph_count} 条段落记忆")


@router.post("/{workspace_id}/memory/rebuild", summary="清空并重建工作区记忆库", response_model=MemoryRebuildStartResponse)
async def rebuild_memory(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryRebuildStartResponse:
    from nekro_agent.services.memory.rebuild import start_workspace_memory_rebuild

    await _ensure_workspace_exists(workspace_id)
    ensure_memory_system_enabled(MemoryOperation.REBUILD)
    result = start_workspace_memory_rebuild(
        workspace_id,
        requested_by=str(_current_user.username or _current_user.id),
        request_id=f"workspace:{workspace_id}:user:{_current_user.id}",
    )
    return MemoryRebuildStartResponse(
        job_id=result.job_id,
        reused=result.reused,
        status=result.status,
        message=result.message,
    )


@router.post("/{workspace_id}/memory/rebuild/cancel", summary="取消工作区记忆重建", response_model=MemoryRebuildStartResponse)
async def cancel_memory_rebuild(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryRebuildStartResponse:
    from nekro_agent.services.memory.rebuild import cancel_workspace_memory_rebuild

    await _ensure_workspace_exists(workspace_id)
    ensure_memory_system_enabled(MemoryOperation.REBUILD)
    result = cancel_workspace_memory_rebuild(workspace_id)
    return MemoryRebuildStartResponse(
        job_id=result.job_id,
        reused=result.reused,
        status=result.status,
        message=result.message,
    )


@router.get(
    "/{workspace_id}/memory/rebuild/status",
    summary="获取工作区记忆重建状态",
    response_model=MemoryRebuildStatusResponse,
)
async def get_memory_rebuild_status(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryRebuildStatusResponse:
    from nekro_agent.services.memory.rebuild import get_workspace_memory_rebuild_status

    await _ensure_workspace_exists(workspace_id)
    status = await get_workspace_memory_rebuild_status(workspace_id)
    return MemoryRebuildStatusResponse(
        workspace_id=status.workspace_id,
        job_id=status.job_id,
        is_running=status.is_running,
        status=status.status,
        phase=status.phase,
        started_at=status.started_at,
        finished_at=status.finished_at,
        cutoff=status.cutoff,
        semantic_replayed=status.semantic_replayed,
        cancel_requested=status.cancel_requested,
        current_chat_key=status.current_chat_key,
        last_heartbeat_at=status.last_heartbeat_at,
        failure_code=status.failure_code,
        failure_reason=status.failure_reason,
        overall_progress_percent=status.overall_progress_percent,
        total_channels=status.total_channels,
        completed_channels=status.completed_channels,
        total_messages_processed=status.total_messages_processed,
        channels=[
            MemoryRebuildChannelStatusResponse(
                chat_key=item.chat_key,
                status=item.status,
                upper_bound_message_db_id=item.upper_bound_message_db_id,
                initial_cursor_db_id=item.initial_cursor_db_id,
                last_cursor_db_id=item.last_cursor_db_id,
                message_count_total=item.message_count_total,
                messages_processed=item.messages_processed,
                completed=item.completed,
                progress_ratio=item.progress_ratio,
                last_error=item.last_error,
            )
            for item in status.channels
        ],
    )


@router.post("/{workspace_id}/memory/prune", summary="清理低价值结构化记忆", response_model=MemoryPruneResponse)
async def prune_memory(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryPruneResponse:
    await _ensure_workspace_exists(workspace_id)
    ensure_memory_system_enabled(MemoryOperation.PRUNE)
    result: MemoryPruneResult = await prune_workspace_memories(workspace_id)
    return MemoryPruneResponse(
        paragraphs_pruned=result.paragraphs_pruned,
        relations_pruned=result.relations_pruned,
        entities_pruned=result.entities_pruned,
    )


@router.get("/{workspace_id}/memory/data", summary="获取结构化记忆数据视图", response_model=MemoryDataResponse)
async def get_memory_data(
    workspace_id: int,
    limit: int = Query(default=20, ge=5, le=100),
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryDataResponse:
    from datetime import timedelta

    from nekro_agent.models.db_mem_entity import DBMemEntity
    from nekro_agent.models.db_mem_episode import DBMemEpisode
    from nekro_agent.models.db_mem_paragraph import CognitiveType, DBMemParagraph
    from nekro_agent.models.db_mem_reinforcement_log import DBMemReinforcementLog
    from nekro_agent.models.db_mem_relation import DBMemRelation

    await _ensure_workspace_exists(workspace_id)

    now_ts = time.time()
    paragraph_count = await DBMemParagraph.filter(workspace_id=workspace_id).count()
    episodic_count = await DBMemParagraph.filter(
        workspace_id=workspace_id,
        cognitive_type=CognitiveType.EPISODIC,
    ).count()
    semantic_count = await DBMemParagraph.filter(
        workspace_id=workspace_id,
        cognitive_type=CognitiveType.SEMANTIC,
    ).count()
    episode_count = await DBMemEpisode.filter(workspace_id=workspace_id, is_inactive=False).count()
    entity_count = await DBMemEntity.filter(workspace_id=workspace_id).count()
    relation_count = await DBMemRelation.filter(workspace_id=workspace_id).count()
    reinforcement_count_7d = await DBMemReinforcementLog.filter(
        workspace_id=workspace_id,
        create_time__gte=datetime.now() - timedelta(days=7),
    ).count()

    paragraphs = await DBMemParagraph.filter(
        workspace_id=workspace_id,
    ).order_by("-create_time").limit(limit)
    entities = await DBMemEntity.filter(
        workspace_id=workspace_id,
        is_inactive=False,
    ).order_by("-appearance_count", "-update_time").limit(20)
    relations = await DBMemRelation.filter(
        workspace_id=workspace_id,
        is_inactive=False,
    ).order_by("-update_time").limit(20)
    entity_map = {
        entity.id: entity
        for entity in await DBMemEntity.filter(
            workspace_id=workspace_id,
            id__in=[r.subject_entity_id for r in relations] + [r.object_entity_id for r in relations],
        )
    }

    return MemoryDataResponse(
        stats=MemoryDataStats(
            paragraph_count=paragraph_count,
            episodic_count=episodic_count,
            semantic_count=semantic_count,
            episode_count=episode_count,
            entity_count=entity_count,
            relation_count=relation_count,
            reinforcement_count_7d=reinforcement_count_7d,
        ),
        paragraphs=[
            MemoryParagraphData(
                id=paragraph.id,
                summary=paragraph.summary or "",
                content=paragraph.content,
                memory_source=paragraph.memory_source,
                cognitive_type=paragraph.cognitive_type.value,
                knowledge_type=paragraph.knowledge_type.value,
                base_weight=paragraph.base_weight,
                effective_weight=paragraph.compute_effective_weight(now_ts),
                event_time=paragraph.event_time.isoformat() if paragraph.event_time else None,
                origin_kind=paragraph.origin_kind.value,
                origin_chat_key=paragraph.origin_chat_key,
                create_time=paragraph.create_time.isoformat(),
            )
            for paragraph in paragraphs
        ],
        entities=[
            MemoryEntityData(
                id=entity.id,
                entity_type=entity.entity_type.value,
                canonical_name=entity.canonical_name,
                appearance_count=entity.appearance_count,
                source_hint=entity.source_hint.value,
                update_time=entity.update_time.isoformat(),
            )
            for entity in entities
        ],
        relations=[
            MemoryRelationData(
                id=relation.id,
                subject_entity_id=relation.subject_entity_id,
                subject_name=entity_map[relation.subject_entity_id].canonical_name
                if relation.subject_entity_id in entity_map else str(relation.subject_entity_id),
                predicate=relation.predicate,
                object_entity_id=relation.object_entity_id,
                object_name=entity_map[relation.object_entity_id].canonical_name
                if relation.object_entity_id in entity_map else str(relation.object_entity_id),
                memory_source=relation.memory_source,
                cognitive_type=relation.cognitive_type,
                base_weight=relation.base_weight,
                effective_weight=relation.compute_effective_weight(now_ts),
                paragraph_id=relation.paragraph_id,
                update_time=relation.update_time.isoformat(),
            )
            for relation in relations
        ],
    )


@router.post("/{workspace_id}/memory/episode/aggregate", summary="手动触发 Episode 聚合", response_model=ActionOkResponse)
async def aggregate_memory_episode(
    workspace_id: int,
    chat_key: Optional[str] = Query(default=None),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    from nekro_agent.services.memory.episode_aggregator import aggregate_workspace_episodes

    await _ensure_workspace_exists(workspace_id)
    ensure_memory_system_enabled(MemoryOperation.EPISODE_AGGREGATION)
    result = await aggregate_workspace_episodes(workspace_id, chat_key)
    return ActionOkResponse(
        message=f"Episode 聚合完成，新增 {result.episodes_created} 个事件，绑定 {result.paragraphs_bound} 条段落"
    )


@router.get("/{workspace_id}/memory/graph", summary="获取结构化记忆图谱", response_model=MemoryGraphResponse)
async def get_memory_graph(
    workspace_id: int,
    limit: int = Query(default=240, ge=50, le=600),
    include_inactive: bool = Query(default=False),
    time_from: Optional[str] = Query(default=None),
    time_to: Optional[str] = Query(default=None),
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryGraphResponse:
    from nekro_agent.models.db_mem_entity import DBMemEntity
    from nekro_agent.models.db_mem_episode import DBMemEpisode
    from nekro_agent.models.db_mem_paragraph import DBMemParagraph
    from nekro_agent.models.db_mem_relation import DBMemRelation

    await _ensure_workspace_exists(workspace_id)
    now_ts = time.time()
    parsed_time_from: Optional[datetime] = None
    parsed_time_to: Optional[datetime] = None

    try:
        if time_from:
            parsed_time_from = datetime.fromisoformat(time_from.replace("Z", "+00:00"))
        if time_to:
            parsed_time_to = datetime.fromisoformat(time_to.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValidationError(reason=f"时间参数格式无效: {e}") from e

    paragraph_qs = DBMemParagraph.filter(workspace_id=workspace_id)
    entity_qs = DBMemEntity.filter(workspace_id=workspace_id)
    relation_qs = DBMemRelation.filter(workspace_id=workspace_id)
    if not include_inactive:
        paragraph_qs = paragraph_qs.filter(is_inactive=False)
        entity_qs = entity_qs.filter(is_inactive=False)
        relation_qs = relation_qs.filter(is_inactive=False)
    if parsed_time_from:
        paragraph_qs = paragraph_qs.filter(event_time__gte=parsed_time_from)
    if parsed_time_to:
        paragraph_qs = paragraph_qs.filter(event_time__lte=parsed_time_to)

    paragraphs = await paragraph_qs.order_by("-update_time").limit(limit)
    paragraph_ids = [paragraph.id for paragraph in paragraphs]

    if parsed_time_from or parsed_time_to:
        if paragraph_ids:
            relation_qs = relation_qs.filter(paragraph_id__in=paragraph_ids)
        else:
            relation_qs = relation_qs.filter(paragraph_id=-1)
    relations = await relation_qs.order_by("-update_time").limit(limit)
    episode_qs = DBMemEpisode.filter(workspace_id=workspace_id)
    if not include_inactive:
        episode_qs = episode_qs.filter(is_inactive=False)
    if parsed_time_from:
        episode_qs = episode_qs.filter(time_end__gte=parsed_time_from)
    if parsed_time_to:
        episode_qs = episode_qs.filter(time_start__lte=parsed_time_to)
    episodes = await episode_qs.order_by("-time_end", "-update_time").limit(max(20, limit // 2))
    episode_entity_ids = [entity_id for episode in episodes for entity_id in (episode.participant_entity_ids or [])]

    relation_entity_ids = [relation.subject_entity_id for relation in relations] + [relation.object_entity_id for relation in relations]
    paragraph_relation_entity_ids = [
        entity_id
        for relation in relations
        if relation.paragraph_id in paragraph_ids
        for entity_id in (relation.subject_entity_id, relation.object_entity_id)
    ]
    entity_ids = list(set(relation_entity_ids + paragraph_relation_entity_ids + episode_entity_ids))
    entities = []
    if entity_ids:
        entities = await entity_qs.filter(id__in=entity_ids).limit(limit)
    entity_map = {entity.id: entity for entity in entities}

    nodes: List[MemoryGraphNode] = []
    edges: List[MemoryGraphEdge] = []
    paragraph_entity_edges: set[tuple[int, int]] = set()

    for paragraph in paragraphs:
        effective_weight = paragraph.compute_effective_weight(now_ts)
        nodes.append(
            MemoryGraphNode(
                id=f"paragraph-{paragraph.id}",
                memory_type="paragraph",
                ref_id=paragraph.id,
                label=paragraph.summary or paragraph.content[:28],
                subtitle=paragraph.knowledge_type.value,
                status="inactive" if paragraph.is_inactive else "active",
                cognitive_type=paragraph.cognitive_type.value,
                weight=effective_weight,
                size=min(1.8, 0.9 + max(0.0, effective_weight) * 0.45),
                importance=effective_weight,
                metadata={
                    "memory_source": paragraph.memory_source,
                    "is_frozen": paragraph.is_frozen,
                    "is_protected": paragraph.is_protected,
                    "origin_kind": paragraph.origin_kind.value,
                    "episode_id": paragraph.episode_id,
                    "episode_phase": paragraph.episode_phase.value if paragraph.episode_phase else None,
                    "create_time": paragraph.create_time.isoformat(),
                    "update_time": paragraph.update_time.isoformat(),
                },
            )
        )

    for episode in episodes:
        episode_effective_weight = _compute_episode_effective_weight(episode, now_ts)
        nodes.append(
            MemoryGraphNode(
                id=f"episode-{episode.id}",
                memory_type="episode",
                ref_id=episode.id,
                label=episode.title,
                subtitle=episode.narrative_summary[:80],
                status="inactive" if episode.is_inactive else "active",
                cognitive_type="episodic",
                weight=episode_effective_weight,
                size=min(2.0, 1.0 + len(episode.paragraph_ids or []) * 0.08),
                importance=episode_effective_weight + len(episode.paragraph_ids or []) * 0.15,
                metadata={
                    "origin_chat_key": episode.origin_chat_key,
                    "time_start": episode.time_start.isoformat() if episode.time_start else None,
                    "time_end": episode.time_end.isoformat() if episode.time_end else None,
                    "paragraph_ids": episode.paragraph_ids,
                    "participant_entity_ids": episode.participant_entity_ids,
                },
            )
        )

    for entity in entities:
        importance = float(entity.appearance_count)
        nodes.append(
            MemoryGraphNode(
                id=f"entity-{entity.id}",
                memory_type="entity",
                ref_id=entity.id,
                label=entity.canonical_name,
                subtitle=entity.entity_type.value,
                status="inactive" if entity.is_inactive else "active",
                weight=importance,
                size=min(1.6, 0.85 + min(entity.appearance_count, 10) * 0.06),
                importance=importance,
                metadata={
                    "appearance_count": entity.appearance_count,
                    "source_hint": entity.source_hint.value,
                    "create_time": entity.create_time.isoformat(),
                    "update_time": entity.update_time.isoformat(),
                },
            )
        )

    for relation in relations:
        effective_weight = relation.compute_effective_weight(now_ts)
        status = "inactive" if relation.is_inactive else "active"
        subject = entity_map.get(relation.subject_entity_id)
        obj = entity_map.get(relation.object_entity_id)
        relation_node_id = f"relation-{relation.id}"
        nodes.append(
            MemoryGraphNode(
                id=relation_node_id,
                memory_type="relation",
                ref_id=relation.id,
                label=relation.predicate,
                subtitle=f"{subject.canonical_name if subject else relation.subject_entity_id} -> {obj.canonical_name if obj else relation.object_entity_id}",
                status=status,
                cognitive_type=relation.cognitive_type,
                weight=effective_weight,
                size=min(1.5, 0.75 + max(0.0, effective_weight) * 0.4),
                importance=effective_weight,
                paragraph_id=relation.paragraph_id,
                metadata={
                    "memory_source": relation.memory_source,
                    "paragraph_id": relation.paragraph_id,
                    "create_time": relation.create_time.isoformat(),
                    "update_time": relation.update_time.isoformat(),
                },
            )
        )

        if subject:
            edges.append(
                MemoryGraphEdge(
                    id=f"relation-subject-{relation.id}-{subject.id}",
                    source=relation_node_id,
                    target=f"entity-{subject.id}",
                    edge_type="relation_subject",
                    label="主语",
                    weight=effective_weight,
                    strength=min(1.0, 0.25 + max(0.0, effective_weight) * 0.35),
                    status=status,
                    cognitive_type=relation.cognitive_type,
                )
            )
        if obj:
            edges.append(
                MemoryGraphEdge(
                    id=f"relation-object-{relation.id}-{obj.id}",
                    source=relation_node_id,
                    target=f"entity-{obj.id}",
                    edge_type="relation_object",
                    label="宾语",
                    weight=effective_weight,
                    strength=min(1.0, 0.25 + max(0.0, effective_weight) * 0.35),
                    status=status,
                    cognitive_type=relation.cognitive_type,
                )
            )
        if relation.paragraph_id and relation.paragraph_id in paragraph_ids:
            edges.append(
                MemoryGraphEdge(
                    id=f"relation-paragraph-{relation.id}-{relation.paragraph_id}",
                    source=relation_node_id,
                    target=f"paragraph-{relation.paragraph_id}",
                    edge_type="relation_paragraph",
                    label="来源段落",
                    weight=effective_weight,
                    strength=min(1.0, 0.2 + max(0.0, effective_weight) * 0.25),
                    status=status,
                    cognitive_type=relation.cognitive_type,
                )
            )
            if subject:
                paragraph_entity_edges.add((relation.paragraph_id, subject.id))
            if obj:
                paragraph_entity_edges.add((relation.paragraph_id, obj.id))

    for paragraph_id, entity_id in paragraph_entity_edges:
        edges.append(
            MemoryGraphEdge(
                id=f"paragraph-entity-{paragraph_id}-{entity_id}",
                source=f"paragraph-{paragraph_id}",
                target=f"entity-{entity_id}",
                edge_type="paragraph_entity",
                label="提及",
                weight=0.5,
                strength=0.35,
                status="active",
            )
        )

    paragraph_id_set = set(paragraph_ids)
    for episode in episodes:
        for paragraph_id in episode.paragraph_ids or []:
            if paragraph_id in paragraph_id_set:
                edges.append(
                    MemoryGraphEdge(
                        id=f"episode-paragraph-{episode.id}-{paragraph_id}",
                        source=f"episode-{episode.id}",
                        target=f"paragraph-{paragraph_id}",
                        edge_type="episode_paragraph",
                        label="包含段落",
                        weight=episode.base_weight,
                        strength=0.45,
                        status="inactive" if episode.is_inactive else "active",
                        cognitive_type="episodic",
                    )
                )
        for entity_id in episode.participant_entity_ids or []:
            if entity_id in entity_map:
                edges.append(
                    MemoryGraphEdge(
                        id=f"episode-entity-{episode.id}-{entity_id}",
                        source=f"episode-{episode.id}",
                        target=f"entity-{entity_id}",
                        edge_type="episode_entity",
                        label="参与者",
                        weight=episode.base_weight,
                        strength=0.35,
                        status="inactive" if episode.is_inactive else "active",
                        cognitive_type="episodic",
                    )
                )

    return MemoryGraphResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        node_count=len(nodes),
        edge_count=len(edges),
        nodes=nodes,
        edges=edges,
    )


@router.get("/{workspace_id}/memory/list", summary="获取结构化记忆列表", response_model=MemoryListResponse)
async def list_memories(
    workspace_id: int,
    memory_type: Optional[str] = Query(default=None, pattern="^(paragraph|entity|relation|episode)?$"),
    status: Optional[str] = Query(default=None, pattern="^(active|inactive)?$"),
    cognitive_type: Optional[str] = Query(default=None, pattern="^(episodic|semantic)?$"),
    time_from: Optional[str] = Query(default=None),
    time_to: Optional[str] = Query(default=None),
    sort_by: str = Query(default="event_time"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryListResponse:
    from nekro_agent.models.db_mem_entity import DBMemEntity
    from nekro_agent.models.db_mem_episode import DBMemEpisode
    from nekro_agent.models.db_mem_paragraph import DBMemParagraph
    from nekro_agent.models.db_mem_relation import DBMemRelation

    await _ensure_workspace_exists(workspace_id)
    now_ts = time.time()
    items: List[MemoryListItem] = []
    active_filter = None if status is None else (status == "inactive")
    parsed_time_from: Optional[datetime] = None
    parsed_time_to: Optional[datetime] = None

    try:
        if time_from:
            parsed_time_from = datetime.fromisoformat(time_from.replace("Z", "+00:00"))
        if time_to:
            parsed_time_to = datetime.fromisoformat(time_to.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValidationError(reason=f"时间参数格式无效: {e}") from e

    if memory_type in (None, "paragraph"):
        paragraph_qs = DBMemParagraph.filter(workspace_id=workspace_id)
        if active_filter is not None:
            paragraph_qs = paragraph_qs.filter(is_inactive=active_filter)
        if cognitive_type:
            paragraph_qs = paragraph_qs.filter(cognitive_type=cognitive_type)
        if parsed_time_from:
            paragraph_qs = paragraph_qs.filter(event_time__gte=parsed_time_from)
        if parsed_time_to:
            paragraph_qs = paragraph_qs.filter(event_time__lte=parsed_time_to)
        paragraphs = await paragraph_qs.order_by("-event_time", "-update_time").offset(offset).limit(limit)
        items.extend(
            MemoryListItem(
                id=paragraph.id,
                memory_type="paragraph",
                title=paragraph.summary or paragraph.content[:60],
                subtitle=paragraph.knowledge_type.value,
                status="inactive" if paragraph.is_inactive else "active",
                cognitive_type=paragraph.cognitive_type.value,
                base_weight=paragraph.base_weight,
                effective_weight=paragraph.compute_effective_weight(now_ts),
                event_time=paragraph.event_time.isoformat() if paragraph.event_time else None,
                create_time=paragraph.create_time.isoformat(),
                update_time=paragraph.update_time.isoformat(),
            )
            for paragraph in paragraphs
        )

    if memory_type in (None, "entity"):
        entity_qs = DBMemEntity.filter(workspace_id=workspace_id)
        if active_filter is not None:
            entity_qs = entity_qs.filter(is_inactive=active_filter)
        entities = await entity_qs.order_by("-update_time").offset(offset).limit(limit)
        items.extend(
            MemoryListItem(
                id=entity.id,
                memory_type="entity",
                title=entity.canonical_name,
                subtitle=entity.entity_type.value,
                status="inactive" if entity.is_inactive else "active",
                create_time=entity.create_time.isoformat(),
                update_time=entity.update_time.isoformat(),
            )
            for entity in entities
        )

    if memory_type in (None, "relation"):
        relation_qs = DBMemRelation.filter(workspace_id=workspace_id)
        if active_filter is not None:
            relation_qs = relation_qs.filter(is_inactive=active_filter)
        if cognitive_type:
            relation_qs = relation_qs.filter(cognitive_type=cognitive_type)
        if parsed_time_from or parsed_time_to:
            paragraph_time_qs = DBMemParagraph.filter(workspace_id=workspace_id)
            if parsed_time_from:
                paragraph_time_qs = paragraph_time_qs.filter(event_time__gte=parsed_time_from)
            if parsed_time_to:
                paragraph_time_qs = paragraph_time_qs.filter(event_time__lte=parsed_time_to)
            paragraph_ids = await paragraph_time_qs.values_list("id", flat=True)
            if paragraph_ids:
                relation_qs = relation_qs.filter(paragraph_id__in=list(paragraph_ids))
            else:
                relation_qs = relation_qs.filter(paragraph_id=-1)
        relations = await relation_qs.order_by("-update_time").offset(offset).limit(limit)
        relation_paragraph_map = {
            paragraph.id: paragraph
            for paragraph in await DBMemParagraph.filter(
                workspace_id=workspace_id,
                id__in=[relation.paragraph_id for relation in relations if relation.paragraph_id],
            )
        }
        entity_map = {
            entity.id: entity
            for entity in await DBMemEntity.filter(
                workspace_id=workspace_id,
                id__in=[r.subject_entity_id for r in relations] + [r.object_entity_id for r in relations],
            )
        }
        items.extend(
            MemoryListItem(
                id=relation.id,
                memory_type="relation",
                title=(
                    f"{entity_map[relation.subject_entity_id].canonical_name if relation.subject_entity_id in entity_map else relation.subject_entity_id} "
                    f"- {relation.predicate} - "
                    f"{entity_map[relation.object_entity_id].canonical_name if relation.object_entity_id in entity_map else relation.object_entity_id}"
                ),
                subtitle=relation.memory_source,
                status="inactive" if relation.is_inactive else "active",
                cognitive_type=relation.cognitive_type,
                base_weight=relation.base_weight,
                effective_weight=relation.compute_effective_weight(now_ts),
                event_time=(
                    relation_paragraph_map[relation.paragraph_id].event_time.isoformat()
                    if relation.paragraph_id and relation.paragraph_id in relation_paragraph_map and relation_paragraph_map[relation.paragraph_id].event_time
                    else None
                ),
                create_time=relation.create_time.isoformat(),
                update_time=relation.update_time.isoformat(),
            )
            for relation in relations
        )

    if memory_type in (None, "episode"):
        episode_qs = DBMemEpisode.filter(workspace_id=workspace_id)
        if active_filter is not None:
            episode_qs = episode_qs.filter(is_inactive=active_filter)
        if parsed_time_from:
            episode_qs = episode_qs.filter(time_end__gte=parsed_time_from)
        if parsed_time_to:
            episode_qs = episode_qs.filter(time_start__lte=parsed_time_to)
        episodes = await episode_qs.order_by("-time_end", "-update_time").offset(offset).limit(limit)
        items.extend(
            MemoryListItem(
                id=episode.id,
                memory_type="episode",
                title=episode.title,
                subtitle=f"{len(episode.paragraph_ids or [])} 段落",
                status="inactive" if episode.is_inactive else "active",
                cognitive_type="episodic",
                base_weight=episode.base_weight,
                effective_weight=_compute_episode_effective_weight(episode, now_ts),
                event_time=(episode.time_end or episode.time_start).isoformat() if (episode.time_end or episode.time_start) else None,
                create_time=episode.create_time.isoformat(),
                update_time=episode.update_time.isoformat(),
            )
            for episode in episodes
        )

    reverse = order != "asc"
    if sort_by == "create_time":
        items.sort(key=lambda item: item.create_time, reverse=reverse)
    elif sort_by == "event_time":
        items.sort(key=lambda item: item.event_time or item.update_time, reverse=reverse)
    elif sort_by == "effective_weight":
        items.sort(key=lambda item: item.effective_weight or 0.0, reverse=reverse)
    else:
        items.sort(key=lambda item: item.update_time, reverse=reverse)
    return MemoryListResponse(total=len(items), items=items[:limit])


@router.get("/{workspace_id}/memory/{memory_type}/{memory_id}", summary="获取结构化记忆详情", response_model=MemoryDetailResponse)
async def get_memory_detail(
    workspace_id: int,
    memory_type: str,
    memory_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryDetailResponse:
    from nekro_agent.models.db_mem_entity import DBMemEntity
    from nekro_agent.models.db_mem_episode import DBMemEpisode
    from nekro_agent.models.db_mem_paragraph import DBMemParagraph
    from nekro_agent.models.db_mem_relation import DBMemRelation

    target = await _get_memory_target(workspace_id, memory_type, memory_id)
    data = target.to_dict()
    if memory_type == "paragraph":
        data["effective_weight"] = target.compute_effective_weight(time.time())
    elif memory_type == "relation":
        relation: DBMemRelation = target
        subject = await DBMemEntity.get_or_none(id=relation.subject_entity_id)
        obj = await DBMemEntity.get_or_none(id=relation.object_entity_id)
        data["subject_name"] = subject.canonical_name if subject else None
        data["object_name"] = obj.canonical_name if obj else None
        data["effective_weight"] = relation.compute_effective_weight(time.time())
    elif memory_type == "episode":
        episode: DBMemEpisode = target
        paragraphs = await DBMemParagraph.filter(
            workspace_id=workspace_id,
            id__in=episode.paragraph_ids or [],
        ).order_by("event_time", "id")
        entities = await DBMemEntity.filter(
            workspace_id=workspace_id,
            id__in=episode.participant_entity_ids or [],
        )
        data["participant_entities"] = [
            {
                "id": entity.id,
                "name": entity.canonical_name,
                "entity_type": entity.entity_type.value,
            }
            for entity in entities
        ]
        data["paragraphs"] = [
            {
                "id": paragraph.id,
                "summary": paragraph.summary or paragraph.content[:72],
                "knowledge_type": paragraph.knowledge_type.value,
                "event_time": paragraph.event_time.isoformat() if paragraph.event_time else None,
                "episode_phase": paragraph.episode_phase.value if paragraph.episode_phase else None,
            }
            for paragraph in paragraphs
        ]
    return MemoryDetailResponse(memory_type=memory_type, data=data)


@router.get("/{workspace_id}/memory/paragraph/{memory_id}/trace", summary="获取段落记忆追溯", response_model=MemoryTraceResponse)
async def get_memory_trace(
    workspace_id: int,
    memory_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryTraceResponse:
    from nekro_agent.models.db_chat_message import DBChatMessage
    from nekro_agent.models.db_mem_entity import DBMemEntity
    from nekro_agent.models.db_mem_relation import DBMemRelation

    paragraph = await _get_memory_target(workspace_id, "paragraph", memory_id)
    message_ids = [msg_id for msg_id in [paragraph.anchor_msg_id, paragraph.anchor_msg_id_start, paragraph.anchor_msg_id_end] if msg_id]
    messages = await DBChatMessage.filter(chat_key=paragraph.origin_chat_key, message_id__in=message_ids).order_by("send_timestamp")
    relations = await DBMemRelation.filter(workspace_id=workspace_id, paragraph_id=paragraph.id, is_inactive=False).all()
    entity_ids = list({
        relation.subject_entity_id for relation in relations
    } | {
        relation.object_entity_id for relation in relations
    })
    entities = await DBMemEntity.filter(workspace_id=workspace_id, id__in=entity_ids).all()
    entity_map = {entity.id: entity for entity in entities}

    return MemoryTraceResponse(
        paragraph=paragraph.to_dict() | {"effective_weight": paragraph.compute_effective_weight(time.time())},
        messages=[
            MemoryTraceMessage(
                id=message.id,
                message_id=message.message_id,
                sender_nickname=message.sender_nickname,
                content_text=message.content_text,
                send_timestamp=message.send_timestamp,
            )
            for message in messages
        ],
        entities=[
            MemoryEntityData(
                id=entity.id,
                entity_type=entity.entity_type.value,
                canonical_name=entity.canonical_name,
                appearance_count=entity.appearance_count,
                source_hint=entity.source_hint.value,
                update_time=entity.update_time.isoformat(),
            )
            for entity in entities
        ],
        relations=[
            MemoryRelationData(
                id=relation.id,
                subject_entity_id=relation.subject_entity_id,
                subject_name=entity_map[relation.subject_entity_id].canonical_name if relation.subject_entity_id in entity_map else str(relation.subject_entity_id),
                predicate=relation.predicate,
                object_entity_id=relation.object_entity_id,
                object_name=entity_map[relation.object_entity_id].canonical_name if relation.object_entity_id in entity_map else str(relation.object_entity_id),
                memory_source=relation.memory_source,
                cognitive_type=relation.cognitive_type,
                base_weight=relation.base_weight,
                effective_weight=relation.compute_effective_weight(time.time()),
                paragraph_id=relation.paragraph_id,
                update_time=relation.update_time.isoformat(),
            )
            for relation in relations
        ],
    )


@router.post("/{workspace_id}/memory/{memory_type}/{memory_id}/reinforce", summary="强化记忆", response_model=ActionOkResponse)
async def reinforce_memory(
    workspace_id: int,
    memory_type: str,
    memory_id: int,
    boost: float = Query(default=0.2, ge=0.05, le=1.0),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    target = await _get_memory_target(workspace_id, memory_type, memory_id)
    if memory_type == "paragraph":
        await target.reinforce(boost)
    elif memory_type == "relation":
        await target.reinforce(boost)
    else:
        raise ValidationError(reason="实体暂不支持强化，请强化相关段落或关系")
    return ActionOkResponse(message="记忆已强化")


@router.post("/{workspace_id}/memory/{memory_type}/{memory_id}/demote", summary="降低记忆权重", response_model=ActionOkResponse)
async def demote_memory(
    workspace_id: int,
    memory_type: str,
    memory_id: int,
    delta: float = Query(default=0.2, ge=0.05, le=1.0),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    target = await _get_memory_target(workspace_id, memory_type, memory_id)
    if memory_type == "paragraph":
        target.manual_weight_delta -= delta
        target.last_manual_action = "demote"
        target.last_manual_action_at = datetime.now(timezone.utc)
        await target.save(update_fields=["manual_weight_delta", "last_manual_action", "last_manual_action_at", "update_time"])
    elif memory_type == "relation":
        target.base_weight = max(0.0, target.base_weight - delta)
        await target.save(update_fields=["base_weight", "update_time"])
    else:
        raise ValidationError(reason="实体暂不支持降权，请调整相关段落或关系")
    return ActionOkResponse(message="记忆权重已降低")


@router.post("/{workspace_id}/memory/{memory_type}/{memory_id}/freeze", summary="冻结记忆", response_model=ActionOkResponse)
async def freeze_memory(
    workspace_id: int,
    memory_type: str,
    memory_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    target = await _get_memory_target(workspace_id, memory_type, memory_id)
    if memory_type != "paragraph":
        raise ValidationError(reason="当前仅段落记忆支持冻结")
    target.is_frozen = True
    target.last_manual_action = "freeze"
    target.last_manual_action_at = datetime.now(timezone.utc)
    await target.save(update_fields=["is_frozen", "last_manual_action", "last_manual_action_at", "update_time"])
    return ActionOkResponse(message="记忆已冻结")


@router.post("/{workspace_id}/memory/{memory_type}/{memory_id}/unfreeze", summary="解冻记忆", response_model=ActionOkResponse)
async def unfreeze_memory(
    workspace_id: int,
    memory_type: str,
    memory_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    target = await _get_memory_target(workspace_id, memory_type, memory_id)
    if memory_type != "paragraph":
        raise ValidationError(reason="当前仅段落记忆支持解冻")
    target.is_frozen = False
    target.last_manual_action = "unfreeze"
    target.last_manual_action_at = datetime.now(timezone.utc)
    await target.save(update_fields=["is_frozen", "last_manual_action", "last_manual_action_at", "update_time"])
    return ActionOkResponse(message="记忆已解冻")


@router.post("/{workspace_id}/memory/{memory_type}/{memory_id}/protect", summary="保护或取消保护记忆", response_model=ActionOkResponse)
async def protect_memory(
    workspace_id: int,
    memory_type: str,
    memory_id: int,
    protected: bool = Query(default=True),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    target = await _get_memory_target(workspace_id, memory_type, memory_id)
    if memory_type != "paragraph":
        raise ValidationError(reason="当前仅段落记忆支持保护")
    target.is_protected = protected
    target.last_manual_action = "protect" if protected else "unprotect"
    target.last_manual_action_at = datetime.now(timezone.utc)
    await target.save(update_fields=["is_protected", "last_manual_action", "last_manual_action_at", "update_time"])
    return ActionOkResponse(message="记忆保护状态已更新")


@router.put("/{workspace_id}/memory/{memory_type}/{memory_id}", summary="编辑结构化记忆", response_model=ActionOkResponse)
async def edit_memory(
    workspace_id: int,
    memory_type: str,
    memory_id: int,
    body: MemoryEditBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    from nekro_agent.services.memory.embedding_service import embed_text
    from nekro_agent.services.memory.qdrant_manager import memory_qdrant_manager

    target = await _get_memory_target(workspace_id, memory_type, memory_id)
    if memory_type != "paragraph":
        raise ValidationError(reason="当前仅段落记忆支持编辑")

    update_fields = ["update_time"]
    content_updated = False
    if body.summary is not None:
        target.summary = body.summary[:512]
        update_fields.append("summary")
    if body.content is not None:
        target.content = body.content
        update_fields.append("content")
        content_updated = True

    target.last_manual_action = "edit"
    target.last_manual_action_at = datetime.now(timezone.utc)
    update_fields.extend(["last_manual_action", "last_manual_action_at"])
    await target.save(update_fields=update_fields)
    if target.embedding_ref and content_updated:
        try:
            embedding = await embed_text(target.content)
            await memory_qdrant_manager.upsert_paragraph(
                paragraph_id=target.id,
                embedding=embedding,
                payload=target.to_qdrant_payload(),
            )
        except Exception as e:
            logger.warning(f"编辑后刷新段落向量失败: paragraph_id={target.id}, error={e}")
    return ActionOkResponse(message="记忆已更新")


@router.delete("/{workspace_id}/memory/{memory_type}/{memory_id}", summary="删除结构化记忆", response_model=ActionOkResponse)
async def delete_memory(
    workspace_id: int,
    memory_type: str,
    memory_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    from nekro_agent.models.db_mem_paragraph import DBMemParagraph
    from nekro_agent.services.memory.qdrant_manager import memory_qdrant_manager

    target = await _get_memory_target(workspace_id, memory_type, memory_id)
    target.is_inactive = True
    await target.save(update_fields=["is_inactive", "update_time"])
    if memory_type == "paragraph":
        await memory_qdrant_manager.delete_paragraph(memory_id)
    elif memory_type == "episode":
        await DBMemParagraph.filter(workspace_id=workspace_id, episode_id=memory_id).update(
            episode_id=None,
            episode_phase=None,
        )
    return ActionOkResponse(message="记忆已删除")


# ── 沙盒通讯 ────────────────────────────────────────────────────────────────


def _comm_log_to_entry(log: Any) -> CommLogEntry:
    """将 DBWorkspaceCommLog 实例转换为 CommLogEntry Pydantic 模型。"""
    return CommLogEntry.from_orm(log)


@router.get("/{workspace_id}/comm/stream", summary="实时推送沙盒通讯事件（SSE）")
@require_role(Role.Admin)
async def stream_comm_log(
    request: Request,
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> EventSourceResponse:
    from nekro_agent.services.runtime_state import is_shutting_down
    from nekro_agent.services.workspace import comm_broadcast

    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    async def event_generator() -> AsyncGenerator[str, None]:
        q = comm_broadcast.subscribe(workspace_id)
        try:
            while not is_shutting_down():
                if await request.is_disconnected():
                    return
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=1.0)
                    yield payload
                except asyncio.TimeoutError:
                    yield {"comment": "ping"}  # SSE keep-alive，防止 nginx/浏览器空闲断连
        finally:
            comm_broadcast.unsubscribe(workspace_id, q)

    return EventSourceResponse(event_generator())


@router.get("/{workspace_id}/comm/history", summary="获取沙盒通讯历史记录", response_model=CommHistoryResponse)
@require_role(Role.Admin)
async def get_comm_history(
    workspace_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    before_id: Optional[int] = Query(default=None),
    _current_user: DBUser = Depends(get_current_active_user),
) -> CommHistoryResponse:
    from nekro_agent.models.db_workspace_comm_log import DBWorkspaceCommLog

    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    qs = DBWorkspaceCommLog.filter(workspace_id=workspace_id)
    if before_id is not None:
        qs = qs.filter(id__lt=before_id)

    total = await DBWorkspaceCommLog.filter(workspace_id=workspace_id).count()
    # 取最新 limit 条（倒序），再翻转恢复时序（最旧在前、最新在后）
    logs_desc = await qs.order_by("-create_time").limit(limit).all()
    logs = list(reversed(logs_desc))

    return CommHistoryResponse(
        total=total,
        items=[_comm_log_to_entry(log) for log in logs],
    )


@router.post("/{workspace_id}/comm/send", summary="用户直接向 CC 发送指令")
@require_role(Role.Admin)
async def user_send_to_cc(
    workspace_id: int,
    body: CommSendBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> dict:
    from nekro_agent.models.db_workspace_comm_log import DBWorkspaceCommLog
    from nekro_agent.services.workspace import comm_broadcast

    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if ws.status != "active":
        raise ValidationError(reason="工作区未运行，无法发送指令")

    # 1. 构建 prompt 封装（含记忆握手和时间注入），持久化 USER_TO_CC 并立即广播
    envelope = await _build_cc_memory_handshake(workspace_id, body.content)
    user_log = await DBWorkspaceCommLog.create(
        workspace_id=workspace_id,
        direction="USER_TO_CC",
        source_chat_key="__user__",
        content=body.content,
        extra_data=envelope.to_metadata_json(),
    )
    await comm_broadcast.publish(workspace_id, _comm_log_to_entry(user_log))

    delegated_content = envelope.to_prompt()

    # 2. fire-and-forget：CC 通信在后台 Task 完成，HTTP 请求立即返回
    #    所有后续事件（TOOL_CALL、TOOL_RESULT、CC_TO_NA、SYSTEM 错误）均通过 SSE 推送
    #    注意：这里不额外落库/广播 NA_TO_CC。用户直发模式不经过 NA，
    #    delegated_content 仅作为发给 CC 的内部上下文增强，前端应只看到 USER_TO_CC。
    async def _cc_task() -> None:
        started_at = int(time.time() * 1000)
        current_tool_name: Optional[str] = None
        operation_block_count = 0

        async def _runtime_status(
            *,
            phase: Literal["queued", "running", "responding", "completed", "failed", "cancelled"],
            current_tool: Optional[str] = None,
            queue_length: int = 0,
            last_block_kind: Optional[Literal["tool_call", "tool_result", "text_chunk"]] = None,
            last_block_summary: Optional[str] = None,
            error_summary: Optional[str] = None,
        ) -> None:
            try:
                await publish_system_event(
                    WorkspaceCcRuntimeStatusEvent(
                        workspace_id=workspace_id,
                        active=True,
                        name=ws.name,
                        started_at=started_at,
                        updated_at=int(time.time() * 1000),
                        phase=phase,
                        current_tool=current_tool,
                        source_chat_key="__user__",
                        queue_length=queue_length,
                        operation_block_count=operation_block_count,
                        last_block_kind=last_block_kind,
                        last_block_summary=last_block_summary,
                        error_summary=error_summary,
                    )
                )
            except Exception as e:
                logger.warning(f"广播 workspace_cc_runtime_status 失败: {e}")

        async def _status(running: bool) -> None:
            try:
                await comm_broadcast.publish(
                    workspace_id,
                    _build_cc_status_entry(
                        workspace_id,
                        running=running,
                        started_at=started_at,
                    ),
                )
            except Exception as e:
                logger.warning(f"广播 CC_STATUS 失败: {e}")
            try:
                await publish_system_event(
                    WorkspaceCcActiveEvent(
                        workspace_id=workspace_id,
                        active=running,
                        name=ws.name,
                        started_at=started_at,
                    )
                )
            except Exception as e:
                logger.warning(f"广播 workspace_cc_active 失败: {e}")
            if not running:
                try:
                    await publish_system_event(
                        WorkspaceCcRuntimeStatusEvent(
                            workspace_id=workspace_id,
                            active=False,
                            name=ws.name,
                            started_at=started_at,
                            updated_at=int(time.time() * 1000),
                        )
                    )
                except Exception as e:
                    logger.warning(f"广播 workspace_cc_runtime_status false 失败: {e}")

        await _status(True)
        await _runtime_status(phase="running")
        client = CCSandboxClient(ws)
        chunks: List[str] = []
        try:
            async for chunk in client.stream_message(
                delegated_content,
                source_chat_key="__user__",
                on_queued=lambda data: _runtime_status(
                    phase="queued",
                    current_tool=current_tool_name,
                    queue_length=SandboxQueuedChunk.model_validate(data).queue_length,
                ),
                env_vars=await _resolve_workspace_runtime_env(ws),
            ):
                if isinstance(chunk, dict):
                    tool_chunk = SandboxToolChunk.model_validate(chunk)
                    if tool_chunk.type in ("tool_call", "tool_result"):
                        try:
                            import json as _json

                            operation_block_count += 1
                            direction = "TOOL_CALL" if tool_chunk.type == "tool_call" else "TOOL_RESULT"
                            log = await DBWorkspaceCommLog.create(
                                workspace_id=workspace_id,
                                direction=direction,
                                source_chat_key="__user__",
                                content=_json.dumps(chunk, ensure_ascii=False),
                            )
                            await comm_broadcast.publish(workspace_id, _comm_log_to_entry(log))
                            if tool_chunk.type == "tool_call":
                                current_tool_name = tool_chunk.name
                                await _runtime_status(
                                    phase="running",
                                    current_tool=current_tool_name,
                                    last_block_kind="tool_call",
                                    last_block_summary=current_tool_name,
                                )
                            elif current_tool_name is not None:
                                await _runtime_status(
                                    phase="running",
                                    current_tool=None,
                                    last_block_kind="tool_result",
                                    last_block_summary=current_tool_name,
                                )
                                current_tool_name = None
                            else:
                                await _runtime_status(
                                    phase="running",
                                    current_tool=None,
                                    last_block_kind="tool_result",
                                    last_block_summary=tool_chunk.name,
                                )
                        except Exception:
                            pass
                else:
                    operation_block_count += 1
                    if current_tool_name is not None:
                        current_tool_name = None
                    await _runtime_status(
                        phase="responding",
                        last_block_kind="text_chunk",
                        last_block_summary=_summarize_comm_block_text(chunk),
                    )
                    chunks.append(chunk)
        except CCSandboxError as e:
            err_log = await DBWorkspaceCommLog.create(
                workspace_id=workspace_id,
                direction="SYSTEM",
                source_chat_key="__user__",
                content=f"[错误] CC 返回错误: {e}",
            )
            await comm_broadcast.publish(workspace_id, _comm_log_to_entry(err_log))
            await _runtime_status(phase="failed", error_summary=str(e)[:180])
            await _status(False)
            return
        except Exception as e:
            err_log = await DBWorkspaceCommLog.create(
                workspace_id=workspace_id,
                direction="SYSTEM",
                source_chat_key="__user__",
                content=f"[错误] 任务异常: {e}",
            )
            await comm_broadcast.publish(workspace_id, _comm_log_to_entry(err_log))
            await _runtime_status(phase="failed", error_summary=str(e)[:180])
            await _status(False)
            return

        full_result = "".join(chunks)
        reply_log = await DBWorkspaceCommLog.create(
            workspace_id=workspace_id,
            direction="CC_TO_NA",
            source_chat_key="__user__",
            content=full_result,
        )
        await comm_broadcast.publish(workspace_id, _comm_log_to_entry(reply_log))
        try:
            await persist_cc_task_memory(
                workspace_id=workspace_id,
                task_content=body.content,
                result_content=full_result,
                source_chat_key="__user__",
                origin_ref=str(reply_log.id),
                event_time=reply_log.create_time,
            )
        except Exception as e:
            logger.warning(f"CC 结果沉淀为语义记忆失败（可忽略）: {e}")
        await _runtime_status(phase="completed")
        await _status(False)

    asyncio.create_task(_cc_task())
    return {"ok": True}


@router.get("/{workspace_id}/comm/queue", summary="查询 CC 工作区当前任务队列状态", response_model=WorkspaceCommQueueResponse)
@require_role(Role.Admin)
async def get_comm_queue(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceCommQueueResponse:
    """代理 CC 沙盒的真实队列状态，供前端判断 CC 是否真正在处理任务。

    返回字段：
    - current_task: 当前正在执行的任务（None 表示 CC 空闲）
    - queued_tasks: 等待队列
    - queue_length: 等待数量
    """
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if ws.status != "active":
        return WorkspaceCommQueueResponse()
    try:
        client = CCSandboxClient(ws)
        return _parse_comm_queue_response(await client.get_workspace_queue(workspace_id="default"))
    except Exception:
        return WorkspaceCommQueueResponse()


@router.delete("/{workspace_id}/comm/queue/current", summary="强制中止 CC 工作区当前任务")
@require_role(Role.Admin)
async def force_cancel_comm_task(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> dict:
    """向 CC 沙盒发送 SIGKILL 终止当前运行任务，并向 CommTab 广播系统通知。

    适用于 CC 任务卡死或用户需要手动中断的场景。
    CC 进程被杀后会触发 SSE error 事件，NA 侧 _cc_delegate_task 会捕获并终止。
    """
    from nekro_agent.services.workspace import comm_broadcast

    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    if ws.status != "active":
        raise ValidationError(reason="工作区未运行，无法执行取消操作")

    client = CCSandboxClient(ws)

    # 先查当前任务，记录来源频道
    try:
        queue_info = await client.get_workspace_queue(workspace_id="default")
        current = queue_info.get("current_task")
        source_chat_key = (current or {}).get("source_chat_key", "__user__")
    except Exception:
        source_chat_key = "__user__"

    cancelled = await client.force_cancel_current_task(workspace_id="default")

    # 如果任务来自某个 NA 频道（非用户直发），同步取消 NA 侧的后台任务
    # 使任务以 cancel 状态结束，避免 fail 路径触发 NA 侧 AI 误以为是异常并盲目重试
    if source_chat_key and source_chat_key != "__user__":
        try:
            from nekro_agent.services.plugin.task import task as task_api

            na_cancelled = await task_api.cancel("cc_delegate", source_chat_key)
            if na_cancelled:
                logger.info(
                    f"[force_cancel_comm_task] 已同步取消 NA 侧 cc_delegate 任务: chat_key={source_chat_key}"
                )
        except Exception as e:
            logger.warning(f"[force_cancel_comm_task] 取消 NA 侧任务失败: {e}")

    # 向 CommTab 广播 SYSTEM 通知，让前端状态及时复位
    try:
        from nekro_agent.models.db_workspace_comm_log import DBWorkspaceCommLog

        notice = "[强制中止] 用户通过管理界面手动中止了 CC 当前任务。"
        notice_log = await DBWorkspaceCommLog.create(
            workspace_id=workspace_id,
            direction="SYSTEM",
            source_chat_key=source_chat_key,
            content=notice,
            is_streaming=False,
        )
        await comm_broadcast.publish(workspace_id, _comm_log_to_entry(notice_log))
    except Exception as e:
        logger.warning(f"广播强制中止通知失败: {e}")

    # 广播 CC_STATUS False，驱动前端状态指示条立即隐藏
    # （_cc_delegate_task 的 except 路径也会广播，此处确保后台任务场景下也能及时更新）
    try:
        started_at = int(time.time() * 1000)
        await publish_system_event(
            WorkspaceCcRuntimeStatusEvent(
                workspace_id=workspace_id,
                active=True,
                name=ws.name,
                started_at=started_at,
                updated_at=started_at,
                phase="cancelled",
                source_chat_key=source_chat_key,
            )
        )
        await comm_broadcast.publish(
            workspace_id,
            _build_cc_status_entry(
                workspace_id,
                running=False,
                started_at=started_at,
            ),
        )
        await publish_system_event(
            WorkspaceCcActiveEvent(
                workspace_id=workspace_id,
                active=False,
                name=ws.name,
                started_at=started_at,
            )
        )
        await publish_system_event(
            WorkspaceCcRuntimeStatusEvent(
                workspace_id=workspace_id,
                active=False,
                name=ws.name,
                started_at=started_at,
                updated_at=started_at,
            )
        )
    except Exception as e:
        logger.warning(f"广播 CC_STATUS false 失败: {e}")

    return {"cancelled": cancelled, "workspace_id": workspace_id}
