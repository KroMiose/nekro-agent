import asyncio
import fcntl
import json
import os
import pty
import struct
import subprocess
import termios
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional

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
    SandboxStatus,
    ToolsResponse,
    WorkspaceCreate,
    WorkspaceDetail,
    WorkspaceEnvVar,
    WorkspaceEnvVarsResponse,
    WorkspaceEnvVarsUpdate,
    WorkspaceListResponse,
    WorkspaceSkillsUpdate,
    WorkspaceSummary,
    WorkspaceUpdate,
)
from nekro_agent.services.system_broadcast import WorkspaceStatusEvent, publish_system_event
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role
from nekro_agent.services.workspace.client import CCSandboxClient, CCSandboxError
from nekro_agent.services.workspace.container import ImageNotFoundError, SandboxContainerManager
from nekro_agent.services.workspace.manager import WorkspaceService

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


# ─────────────────────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────────────────────


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


def _get_env_vars_dict(workspace: DBWorkspace) -> "Dict[str, str]":
    """从 workspace.metadata["env_vars"] 提取 {key: value} 字典，用于注入 CC 请求。"""
    env_list: List[Dict[str, str]] = (workspace.metadata or {}).get("env_vars", [])
    return {item["key"]: item["value"] for item in env_list if item.get("key") and item.get("value")}


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
    channels_all = await DBChatChannel.filter(workspace_id__in=ws_ids).values(
        "workspace_id", "chat_key", "channel_name"
    )
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
        items.append(BoundChannelInfo(
            chat_key=ch.chat_key,
            description=ann.description if ann else "",
            is_primary=(ch.chat_key == primary_key),
        ))
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
    await publish_system_event(WorkspaceStatusEvent(
        workspace_id=ws.id,
        status=ws.status,  # type: ignore[arg-type]
        name=ws.name,
        container_name=ws.container_name,
        host_port=ws.host_port,
    ))
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
    await publish_system_event(WorkspaceStatusEvent(
        workspace_id=ws.id,
        status=ws.status,  # type: ignore[arg-type]
        name=ws.name,
        container_name=ws.container_name,
        host_port=ws.host_port,
    ))
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
    await publish_system_event(WorkspaceStatusEvent(
        workspace_id=ws.id,
        status=ws.status,  # type: ignore[arg-type]
        name=ws.name,
        container_name=ws.container_name,
        host_port=ws.host_port,
    ))
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
    await publish_system_event(WorkspaceStatusEvent(
        workspace_id=ws.id,
        status=ws.status,  # type: ignore[arg-type]
        name=ws.name,
        container_name=ws.container_name,
        host_port=ws.host_port,
    ))
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
        await comm_broadcast.publish(workspace_id, {
            "id": sys_log.id,
            "workspace_id": sys_log.workspace_id,
            "direction": sys_log.direction,
            "source_chat_key": sys_log.source_chat_key,
            "content": sys_log.content,
            "is_streaming": sys_log.is_streaming,
            "task_id": sys_log.task_id,
            "create_time": sys_log.create_time.isoformat(),
        })
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
                logger.info(
                    f"会话重置：已清理 {deleted_count} 条 last_cc_task_prompt 缓存 "
                    f"workspace_id={workspace_id}"
                )
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


@router.post("/{workspace_id}/skills/{skill_name:path}/sync", summary="从全局库重新同步单个 skill", response_model=ActionOkResponse)
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
# 环境变量管理
# ─────────────────────────────────────────────────────────────


@router.get("/{workspace_id}/env-vars", summary="获取工作区环境变量列表", response_model=WorkspaceEnvVarsResponse)
@require_role(Role.Admin)
async def get_workspace_env_vars(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> WorkspaceEnvVarsResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    env_list = (ws.metadata or {}).get("env_vars", [])
    return WorkspaceEnvVarsResponse(
        env_vars=[WorkspaceEnvVar(**item) for item in env_list if item.get("key")]
    )


@router.put("/{workspace_id}/env-vars", summary="更新工作区环境变量列表", response_model=ActionOkResponse)
@require_role(Role.Admin)
async def update_workspace_env_vars(
    workspace_id: int,
    body: WorkspaceEnvVarsUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    metadata = dict(ws.metadata or {})
    metadata["env_vars"] = [item.model_dump() for item in body.env_vars]
    ws.metadata = metadata
    await ws.save(update_fields=["metadata", "update_time"])
    # 即时刷新 CLAUDE.md（bind mount，CC 下次对话时直接读到最新内容）
    WorkspaceService.update_claude_md(ws)
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
    WorkspaceService.write_dynamic_skill(workspace_id, dir_name, body.content)
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


@router.post("/{workspace_id}/dynamic-skills/{dir_name}/promote", summary="晋升动态 skill 为全局用户 skill", response_model=ActionOkResponse)
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
    skill_dir = WorkspaceService.get_dynamic_skills_dir(workspace_id) / dir_name
    if not skill_dir.exists() or not skill_dir.is_dir():
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
    skill_dir = WorkspaceService.get_dynamic_skills_dir(workspace_id) / dir_name
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
    skill_dir = WorkspaceService.get_dynamic_skills_dir(workspace_id) / dir_name
    if not skill_dir.exists() or not skill_dir.is_dir():
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
                    msg = "[容器正在重建，等待新容器启动...]\n" if last_container_name is not None else "[容器未运行，等待启动...]\n"
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
                await websocket.send_text(
                    json.dumps({"type": "output", "data": data.decode("utf-8", errors="replace")})
                )
            except Exception:
                break

    sender_task = asyncio.create_task(_send_output())

    try:
        while True:
            text = await websocket.receive_text()
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
        loop.remove_reader(master_fd)
        sender_task.cancel()
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


class MemoryFileMeta(BaseModel):
    path: str
    title: str
    category: str
    tags: List[str]
    shared: bool
    updated: str


class MemoryTreeNode(BaseModel):
    name: str
    type: str  # "file" | "dir"
    path: str
    meta: Optional[MemoryFileMeta] = None
    children: Optional[List["MemoryTreeNode"]] = None


MemoryTreeNode.model_rebuild()


class MemoryTreeResponse(BaseModel):
    nodes: List[MemoryTreeNode]


class MemoryFileContent(BaseModel):
    path: str
    raw: str
    content: str
    meta: MemoryFileMeta


class MemoryWriteBody(BaseModel):
    path: str
    raw: str  # 含 frontmatter 的完整内容


class MemoryNaContextBody(BaseModel):
    content: str  # 纯正文，不含 frontmatter


@router.get("/{workspace_id}/memory/tree", summary="获取记忆目录树", response_model=MemoryTreeResponse)
async def get_memory_tree(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryTreeResponse:
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    nodes_raw = WorkspaceService.list_memory_tree(workspace_id)

    def _to_node(d: Dict[str, Any]) -> MemoryTreeNode:
        meta = MemoryFileMeta(**d["meta"]) if d.get("meta") else None
        children = [_to_node(c) for c in d["children"]] if d.get("children") is not None else None
        return MemoryTreeNode(name=d["name"], type=d["type"], path=d["path"], meta=meta, children=children)

    return MemoryTreeResponse(nodes=[_to_node(n) for n in nodes_raw])


@router.get("/{workspace_id}/memory/file", summary="读取记忆文件", response_model=MemoryFileContent)
async def get_memory_file(
    workspace_id: int,
    path: str = Query(..., description="相对于 memory/ 的文件路径"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> MemoryFileContent:
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    result = WorkspaceService.read_memory_file(workspace_id, path)
    if result is None:
        raise NotFoundError(resource=f"记忆文件 {path}")
    return MemoryFileContent(
        path=result["path"],
        raw=result["raw"],
        content=result["content"],
        meta=MemoryFileMeta(**result["meta"]),
    )


@router.put("/{workspace_id}/memory/file", summary="创建/更新记忆文件", response_model=ActionOkResponse)
async def put_memory_file(
    workspace_id: int,
    body: MemoryWriteBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    try:
        WorkspaceService.write_memory_file(workspace_id, body.path, body.raw)
    except ValueError as e:
        raise ValidationError(message=str(e))
    return ActionOkResponse(message="记忆文件已保存")


@router.delete("/{workspace_id}/memory/file", summary="删除记忆文件", response_model=ActionOkResponse)
async def delete_memory_file(
    workspace_id: int,
    path: str = Query(..., description="相对于 memory/ 的文件路径"),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    deleted = WorkspaceService.delete_memory_file(workspace_id, path)
    if not deleted:
        raise NotFoundError(resource=f"记忆文件 {path}")
    return ActionOkResponse(message="记忆文件已删除")


@router.post("/{workspace_id}/memory/reset", summary="清空工作区记忆库", response_model=ActionOkResponse)
async def reset_memory(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    deleted_count = WorkspaceService.reset_memory(workspace_id)
    return ActionOkResponse(message=f"记忆库已清空，共删除 {deleted_count} 个文件")


@router.get("/{workspace_id}/memory/na-context", summary="读取 NA 上下文摘要", response_model=Dict[str, Any])
async def get_na_context(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Dict[str, Any]:
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    content = WorkspaceService.read_na_context(workspace_id)
    return {"content": content, "workspace_id": workspace_id}


@router.put("/{workspace_id}/memory/na-context", summary="更新 NA 上下文摘要", response_model=ActionOkResponse)
async def put_na_context(
    workspace_id: int,
    body: MemoryNaContextBody,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionOkResponse:
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        raise NotFoundError(resource=f"工作区 {workspace_id}")
    raw = f"---\ntitle: \"NA 上下文摘要\"\ncategory: context\nshared: true\nupdated: \"{__import__('datetime').date.today()}\"\n---\n\n{body.content}"
    try:
        WorkspaceService.write_memory_file(workspace_id, "_na_context.md", raw)
    except ValueError as e:
        raise ValidationError(message=str(e))
    return ActionOkResponse(message="NA 上下文摘要已更新")


# ── 沙盒通讯 ────────────────────────────────────────────────────────────────


def _comm_log_to_dict(log: Any) -> dict:
    """将 DBWorkspaceCommLog 实例转换为 CommLogEntry 字典。"""
    return {
        "id": log.id,
        "workspace_id": log.workspace_id,
        "direction": log.direction,
        "source_chat_key": log.source_chat_key,
        "content": log.content,
        "is_streaming": log.is_streaming,
        "task_id": log.task_id,
        "create_time": log.create_time.isoformat(),
    }


@router.get("/{workspace_id}/comm/stream", summary="实时推送沙盒通讯事件（SSE）")
@require_role(Role.Admin)
async def stream_comm_log(
    request: Request,
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> EventSourceResponse:
    from nekro_agent.services.workspace import comm_broadcast

    ws = await DBWorkspace.get_or_none(id=workspace_id)
    if not ws:
        raise NotFoundError(resource=f"工作区 {workspace_id}")

    async def event_generator() -> AsyncGenerator[str, None]:
        q = comm_broadcast.subscribe(workspace_id)
        try:
            while True:
                if await request.is_disconnected():
                    return
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=20.0)
                    yield payload
                except asyncio.TimeoutError:
                    yield ": ping\n\n"  # SSE keep-alive，防止 nginx/浏览器空闲断连
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
        items=[CommLogEntry(**_comm_log_to_dict(log)) for log in logs],
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

    # 1. 持久化 USER_TO_CC 并立即广播 → 前端 SSE 立即看到消息
    user_log = await DBWorkspaceCommLog.create(
        workspace_id=workspace_id,
        direction="USER_TO_CC",
        source_chat_key="__user__",
        content=body.content,
    )
    await comm_broadcast.publish(workspace_id, _comm_log_to_dict(user_log))

    # 2. fire-and-forget：CC 通信在后台 Task 完成，HTTP 请求立即返回
    #    所有后续事件（TOOL_CALL、TOOL_RESULT、CC_TO_NA、SYSTEM 错误）均通过 SSE 推送
    async def _cc_task() -> None:
        async def _status(running: bool) -> None:
            try:
                await comm_broadcast.publish(workspace_id, {
                    "id": 0,
                    "workspace_id": workspace_id,
                    "direction": "CC_STATUS",
                    "source_chat_key": "",
                    "content": json.dumps({"running": running}),
                    "is_streaming": False,
                    "task_id": None,
                    "create_time": datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                pass

        await _status(True)
        client = CCSandboxClient(ws)
        chunks: List[str] = []
        try:
            async for chunk in client.stream_message(body.content, source_chat_key="__user__", env_vars=_get_env_vars_dict(ws)):
                if isinstance(chunk, dict):
                    item_type = chunk.get("type")
                    if item_type in ("tool_call", "tool_result"):
                        try:
                            import json as _json
                            direction = "TOOL_CALL" if item_type == "tool_call" else "TOOL_RESULT"
                            log = await DBWorkspaceCommLog.create(
                                workspace_id=workspace_id,
                                direction=direction,
                                source_chat_key="__user__",
                                content=_json.dumps(chunk, ensure_ascii=False),
                            )
                            await comm_broadcast.publish(workspace_id, _comm_log_to_dict(log))
                        except Exception:
                            pass
                else:
                    chunks.append(chunk)
        except CCSandboxError as e:
            err_log = await DBWorkspaceCommLog.create(
                workspace_id=workspace_id,
                direction="SYSTEM",
                source_chat_key="__user__",
                content=f"[错误] CC 返回错误: {e}",
            )
            await comm_broadcast.publish(workspace_id, _comm_log_to_dict(err_log))
            await _status(False)
            return
        except Exception as e:
            err_log = await DBWorkspaceCommLog.create(
                workspace_id=workspace_id,
                direction="SYSTEM",
                source_chat_key="__user__",
                content=f"[错误] 任务异常: {e}",
            )
            await comm_broadcast.publish(workspace_id, _comm_log_to_dict(err_log))
            await _status(False)
            return

        full_result = "".join(chunks)
        reply_log = await DBWorkspaceCommLog.create(
            workspace_id=workspace_id,
            direction="CC_TO_NA",
            source_chat_key="__user__",
            content=full_result,
        )
        await comm_broadcast.publish(workspace_id, _comm_log_to_dict(reply_log))
        await _status(False)

    asyncio.create_task(_cc_task())
    return {"ok": True}


@router.get("/{workspace_id}/comm/queue", summary="查询 CC 工作区当前任务队列状态")
@require_role(Role.Admin)
async def get_comm_queue(
    workspace_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> dict:
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
        return {"current_task": None, "queued_tasks": [], "queue_length": 0}
    try:
        client = CCSandboxClient(ws)
        return await client.get_workspace_queue(workspace_id="default")
    except Exception:
        return {"current_task": None, "queued_tasks": [], "queue_length": 0}


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
        await comm_broadcast.publish(workspace_id, _comm_log_to_dict(notice_log))
    except Exception as e:
        logger.warning(f"广播强制中止通知失败: {e}")

    # 广播 CC_STATUS False，驱动前端状态指示条立即隐藏
    # （_cc_delegate_task 的 except 路径也会广播，此处确保后台任务场景下也能及时更新）
    try:
        await comm_broadcast.publish(workspace_id, {
            "id": 0,
            "workspace_id": workspace_id,
            "direction": "CC_STATUS",
            "source_chat_key": "",
            "content": json.dumps({"running": False}),
            "is_streaming": False,
            "task_id": None,
            "create_time": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"广播 CC_STATUS false 失败: {e}")

    return {"cancelled": cancelled, "workspace_id": workspace_id}

