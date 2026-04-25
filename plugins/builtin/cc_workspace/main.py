"""CC 工作区协作插件 — 主逻辑

提供以下能力：
- **prompt 注入**：在主 Agent 系统提示词中注入当前频道绑定的 CC Workspace 状态
- **插件命令**：提供 `cc_status` / `cc_context` / `cc_recent` / `cc_abort` /
  `cc_reset_session` / `cc_restart` / `cc_stop` 便于用户直接查看和控制协作状态
- **create_and_bind_workspace**（AGENT 类型）：为当前频道创建 CC Workspace 并自动绑定
- **start_cc_sandbox**（AGENT 类型）：启动绑定工作区的 CC 沙盒容器
- **delegate_to_cc**（BEHAVIOR 类型）：异步委托任务给 CC Workspace 执行，完成后自动将结果推送回主 Agent
- **cancel_cc_task**（BEHAVIOR 类型）：取消正在后台运行的 CC 委托任务
- **reset_cc_session**（BEHAVIOR 类型）：重置 CC 会话并清理旧委托摘要缓存
- **restart_cc_sandbox**（BEHAVIOR 类型）：重启沙盒容器并尝试先终止运行中任务
- **get_cc_context**（AGENT 类型）：查询当前频道 CC 协作上下文（任务状态 + 原始任务摘要 + 通讯历史）
- **upload_file_to_cc**（BEHAVIOR 类型）：将主沙盒文件上传/共享至 CC Workspace 数据目录
- **download_file_from_cc**（TOOL 类型）：将 CC Workspace 数据目录中的文件引入主沙盒

方法可见性根据工作区状态动态调整（三态）：
- 未绑定工作区：仅展示 create_and_bind_workspace
- 已绑定但沙盒未运行：仅展示 start_cc_sandbox
- 正常运行：展示所有工作方法，屏蔽创建/启动方法
"""

import asyncio
import json
import secrets
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, AsyncGenerator, Dict, List, Literal, Optional, Set, Tuple

import aiodocker
from pydantic import BaseModel

from nekro_agent.api import schemas
from nekro_agent.api.plugin import (
    Arg,
    CmdCtl,
    CommandExecutionContext,
    CommandPermission,
    CommandResponse,
    SandboxMethodType,
)
from nekro_agent.core.config import config as app_config
from nekro_agent.core.logger import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.models.db_plugin_data import DBPluginData
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.models.db_workspace_comm_log import DBWorkspaceCommLog
from nekro_agent.services.message_service import message_service
from nekro_agent.services.plugin.task import AsyncTaskHandle, TaskCtl
from nekro_agent.services.plugin.task import task as task_api
from nekro_agent.services.resources import workspace_resource_service
from nekro_agent.services.system_broadcast import (
    WorkspaceCcActiveEvent,
    WorkspaceCcRuntimeStatusEvent,
    publish_system_event,
)
from nekro_agent.services.workspace import comm_broadcast
from nekro_agent.services.workspace.client import CCSandboxClient, CCSandboxError
from nekro_agent.services.workspace.container import SandboxContainerManager
from nekro_agent.services.workspace.manager import WorkspaceService
from nekro_agent.schemas.workspace import CommLogEntry

from .plugin import cc_config, plugin
from .prompt_envelope import CcPromptEnvelope

_TASK_TYPE = "cc_delegate"
_CC_COMMAND_PERMISSION = CommandPermission.SUPER_USER

# 已投递结果去重：(workspace_id, source_chat_key, result_id) → 投递时间
# 防止 SSE 实时路径和 Watcher 轮询路径重复投递同一结果
_delivered_results: Dict[Tuple[int, str, str], float] = {}
_DELIVERED_RESULTS_TTL: float = 300.0  # 去重记录保留 5 分钟


class SandboxQueuedChunk(BaseModel):
    type: Literal["queued"] = "queued"
    queue_length: int = 0


class SandboxToolChunk(BaseModel):
    type: Literal["tool_call", "tool_result"]
    name: Optional[str] = None
    tool_use_id: Optional[str] = None


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------


async def _check_sandbox_image_exists(image: str) -> bool:
    """检查本地 Docker 是否已缓存指定镜像。"""
    docker = aiodocker.Docker()
    try:
        await docker.images.get(image)
        return True
    except Exception:
        return False
    finally:
        await docker.close()


def _format_workspace_status(status: str) -> str:
    return {
        "active": "运行中",
        "stopped": "已停止",
        "failed": "启动失败",
        "deleting": "删除中",
    }.get(status, status or "未知")


def _summarize_runtime_block_text(value: str, max_length: int = 48) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        return ""
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 1]}…"


async def _get_agent_ctx_from_command(context: CommandExecutionContext) -> schemas.AgentCtx:
    return await schemas.AgentCtx.create_by_chat_key(context.chat_key)


async def _require_bound_workspace(_ctx: schemas.AgentCtx) -> DBWorkspace:
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        raise ValueError("当前频道未绑定任何 CC Workspace。")
    return workspace


async def _build_cc_status_message(_ctx: schemas.AgentCtx) -> tuple[str, dict]:
    """生成面向用户的 CC 协作状态摘要。"""
    workspace = await _ctx.get_bound_workspace()
    base_data: dict = {
        "chat_key": _ctx.chat_key,
        "bound": bool(workspace),
    }

    if workspace is None:
        return (
            "当前频道未绑定 CC 工作区。\n"
            "可在工作区管理页面手动绑定，或让 Agent 调用 `create_and_bind_workspace` 自动创建。",
            base_data,
        )

    metadata = workspace.metadata or {}
    selected_skills = metadata.get("skills") or []
    mcp_servers = ((metadata.get("mcp_config") or {}).get("mcpServers") or {})
    status_lines = [
        "[CC 协作状态]",
        f"工作区: {workspace.name}（ID: {workspace.id}）",
        f"状态: {_format_workspace_status(workspace.status)}",
        f"运行策略: {workspace.runtime_policy}",
    ]
    data: dict = {
        **base_data,
        "workspace_id": workspace.id,
        "workspace_name": workspace.name,
        "workspace_status": workspace.status,
        "runtime_policy": workspace.runtime_policy,
        "skills": selected_skills,
        "mcp_servers": list(mcp_servers.keys()),
    }

    if selected_skills:
        status_lines.append(f"已启用技能: {', '.join(selected_skills)}")
    if mcp_servers:
        status_lines.append(f"MCP 服务: {', '.join(mcp_servers.keys())}")
    if workspace.last_error:
        status_lines.append(f"最近错误: {workspace.last_error[:200]}")

    if workspace.status != "active":
        status_lines.append("提示: 启动容器后才能使用完整的 CC 沙盒协作能力。")
        return "\n".join(status_lines), data

    client = CCSandboxClient(workspace)
    healthy = False
    queue_status: dict = {"current_task": None, "queue_length": 0, "queued_tasks": []}
    health_error = ""

    try:
        healthy = await client.health_check()
    except Exception as e:
        health_error = str(e)

    try:
        queue_status = await client.get_workspace_queue(workspace_id="default")
    except Exception as e:
        status_lines.append(f"队列查询失败: {e}")

    task_id = _ctx.from_chat_key or _ctx.chat_key
    task_state = task_api.get_state(_TASK_TYPE, task_id)
    is_running = task_api.is_running(_TASK_TYPE, task_id)
    current_task = queue_status.get("current_task") or {}
    queue_length = int(queue_status.get("queue_length") or 0)
    queued_tasks = queue_status.get("queued_tasks") or []

    status_lines.append(f"容器健康: {'正常' if healthy else '异常'}")
    if health_error:
        status_lines.append(f"健康检查错误: {health_error[:200]}")

    if current_task:
        source_chat_key = current_task.get("source_chat_key") or "未知频道"
        elapsed = int(current_task.get("elapsed_seconds") or 0)
        preview = (current_task.get("prompt_preview") or "").strip()
        preview_text = preview[:120] + ("..." if len(preview) > 120 else "")
        status_lines.append(f"当前任务频道: {source_chat_key}")
        status_lines.append(f"当前任务耗时: {elapsed}s")
        if preview_text:
            status_lines.append(f"当前任务摘要: {preview_text}")
    else:
        status_lines.append("当前任务: 空闲")

    status_lines.append(f"排队数量: {queue_length}")
    if queued_tasks:
        queue_sources = [item.get("source_chat_key", "未知频道") for item in queued_tasks[:5]]
        status_lines.append(f"排队频道: {', '.join(queue_sources)}")

    if is_running and task_state:
        latest_msg = task_state.message[:160] + ("..." if len(task_state.message) > 160 else "")
        status_lines.append("本频道任务: 执行中")
        if latest_msg:
            status_lines.append(f"最新进度: {latest_msg}")
    elif task_state is not None:
        signal_map = {"progress": "进行中", "success": "已完成", "fail": "失败", "cancel": "已取消"}
        status_lines.append(f"本频道最近任务: {signal_map.get(task_state.signal.value, task_state.signal.value)}")
        if task_state.message:
            latest_msg = task_state.message[:160] + ("..." if len(task_state.message) > 160 else "")
            status_lines.append(f"最近结果摘要: {latest_msg}")
    else:
        status_lines.append("本频道最近任务: 暂无记录")

    data.update({
        "healthy": healthy,
        "health_error": health_error,
        "queue_length": queue_length,
        "current_task": current_task or None,
        "queued_tasks": queued_tasks[:5],
        "channel_task_running": is_running,
    })
    return "\n".join(status_lines), data


async def _build_cc_recent_logs_message(_ctx: schemas.AgentCtx, limit: int) -> tuple[str, dict]:
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        return (
            "当前频道未绑定 CC 工作区，暂无可查看的协作记录。",
            {"chat_key": _ctx.chat_key, "bound": False, "logs": []},
        )

    logs = await DBWorkspaceCommLog.filter(
        workspace_id=workspace.id,
        direction__in=["NA_TO_CC", "CC_TO_NA", "SYSTEM"],
        source_chat_key=_ctx.chat_key,
    ).order_by("-create_time").limit(limit).all()

    if not logs:
        return (
            f"当前频道在工作区 {workspace.name} 中还没有 CC 协作记录。",
            {
                "chat_key": _ctx.chat_key,
                "bound": True,
                "workspace_id": workspace.id,
                "logs": [],
            },
        )

    lines = [f"[CC 最近协作记录] 工作区: {workspace.name}（最近 {len(logs)} 条）"]
    payload_logs: list[dict] = []
    direction_map = {
        "NA_TO_CC": "NA→CC",
        "CC_TO_NA": "CC→NA",
        "SYSTEM": "系统",
    }
    for log in reversed(logs):
        content = log.content
        preview = content[:200] + ("..." if len(content) > 200 else "")
        label = direction_map.get(log.direction, log.direction)
        time_str = log.create_time.strftime("%m-%d %H:%M")
        lines.append(f"[{time_str}] {label}: {preview}")
        payload_logs.append({
            "id": log.id,
            "direction": log.direction,
            "time": log.create_time.isoformat(),
            "content": preview,
            "task_id": log.task_id,
        })

    return "\n".join(lines), {
        "chat_key": _ctx.chat_key,
        "bound": True,
        "workspace_id": workspace.id,
        "logs": payload_logs,
    }


# ---------------------------------------------------------------------------
# NA 重启后恢复 CC 待投递结果 + 运行时后台监听器
# ---------------------------------------------------------------------------

# 全局 Watcher 任务句柄（模块级单例）
_cc_result_watcher_task: "asyncio.Task[None] | None" = None

_WATCHER_INTERVAL: int = 30  # 秒；CC 结果最大投递延迟 ≈ 此值




async def _broadcast_error_comm_log(workspace_id: int, source_chat_key: str, content: str) -> None:
    """将错误信息写入 SYSTEM 方向 CommLog 并广播，使前端 CommTab 可以实时看到错误详情。"""
    try:
        err_log = await DBWorkspaceCommLog.create(
            workspace_id=workspace_id,
            direction="SYSTEM",
            source_chat_key=source_chat_key,
            content=content,
            is_streaming=False,
            task_id=f"cc_delegate:{source_chat_key}",
        )
        await comm_broadcast.publish(workspace_id, CommLogEntry.from_orm(err_log))
    except Exception as e:
        logger.warning("[cc_workspace] 写入错误 CommLog 失败（不影响主流程）: %s", e)


async def _broadcast_system_comm_log(
    workspace_id: int,
    content: str,
    *,
    source_chat_key: str = "",
    task_id: str | None = None,
) -> None:
    """写入并广播 SYSTEM CommLog，供控制类操作复用。"""
    try:
        sys_log = await DBWorkspaceCommLog.create(
            workspace_id=workspace_id,
            direction="SYSTEM",
            source_chat_key=source_chat_key,
            content=content,
            is_streaming=False,
            task_id=task_id,
        )
        await comm_broadcast.publish(workspace_id, CommLogEntry.from_orm(sys_log))
    except Exception as e:
        logger.warning("[cc_workspace] 写入 SYSTEM CommLog 失败（不影响主流程）: %s", e)


async def _clear_last_cc_task_prompts(workspace_id: int) -> int:
    """清理绑定到该工作区的频道 task prompt 缓存。"""
    try:
        bound_channels = await DBChatChannel.filter(workspace_id=workspace_id).all()
        if not bound_channels:
            return 0
        chat_keys = [ch.chat_key for ch in bound_channels]
        deleted_count = await DBPluginData.filter(
            plugin_key="KroMiose.cc_workspace",
            target_chat_key__in=chat_keys,
            data_key="last_cc_task_prompt",
        ).delete()
        if deleted_count:
            logger.info(
                "[cc_workspace] 已清理 %s 条 last_cc_task_prompt 缓存，workspace_id=%s",
                deleted_count,
                workspace_id,
            )
        return int(deleted_count)
    except Exception as e:
        logger.warning("[cc_workspace] 清理 last_cc_task_prompt 缓存失败: %s", e)
        return 0


async def _maybe_force_cancel_running_workspace_task(workspace: DBWorkspace) -> dict:
    """如工作区中存在运行中的任务则强制终止，并返回摘要。"""
    client = CCSandboxClient(workspace)
    queue_status = await client.get_workspace_queue(workspace_id="default")
    current_task = queue_status.get("current_task") or None
    if not current_task:
        return {"cancelled": False, "source_chat_key": None, "elapsed_seconds": 0}

    src = current_task.get("source_chat_key") or ""
    elapsed = int(current_task.get("elapsed_seconds") or 0)
    cancelled = await client.force_cancel_current_task(workspace_id="default")
    if cancelled:
        logger.info(
            "[cc_workspace] 已为工作区控制操作强制终止运行中任务，workspace=%s source=%s",
            workspace.id,
            src or "unknown",
        )
    return {"cancelled": bool(cancelled), "source_chat_key": src or None, "elapsed_seconds": elapsed}


async def _reset_workspace_session(workspace: DBWorkspace) -> dict:
    """重置 CC 会话并清理 NA 侧相关缓存。"""
    if workspace.status != "active":
        raise ValueError("当前工作区未运行，无法重置会话。")

    client = CCSandboxClient(workspace)
    await client.reset_session("default")
    await _broadcast_system_comm_log(
        workspace.id,
        "[会话重置] CC Workspace 会话已重置，后续委托将作为全新会话处理。",
    )
    deleted_count = await _clear_last_cc_task_prompts(workspace.id)
    return {"cleared_prompt_cache": deleted_count}


async def _broadcast_cc_status(
    workspace_id: int,
    running: bool,
    *,
    name: Optional[str] = None,
    started_at: Optional[int] = None,
) -> None:
    """通过 SSE 广播 CC 任务运行状态变化（不写入 DB）。

    前端 SSE handler 收到 direction='CC_STATUS' 后直接驱动状态指示条，
    无需轮询 /comm/queue 接口。同时推送全局系统事件供工作区列表页面实时刷新。
    """
    try:
        await comm_broadcast.publish(workspace_id, CommLogEntry(
            id=0,
            workspace_id=workspace_id,
            direction="CC_STATUS",
            source_chat_key="",
            content=json.dumps({"running": running}),
            is_streaming=False,
            task_id=None,
            create_time=datetime.now(timezone.utc).isoformat(),
        ))
    except Exception as _e:
        logger.warning("[cc_workspace] 广播 CC_STATUS 失败: %s", _e)

    # 同时推送全局系统事件（workspace_cc_active），供工作区列表页面实时指示 CC 活跃状态
    resolved_started_at = started_at if started_at is not None and started_at > 0 else int(time.time() * 1000)

    try:
        await publish_system_event(WorkspaceCcActiveEvent(
            workspace_id=workspace_id,
            active=running,
            name=name,
            started_at=resolved_started_at,
            max_duration_ms=300000,  # 最长 5 分钟；任务完成时会发送 active=false 主动关闭
        ))
    except Exception as _e:
        logger.warning("[cc_workspace] 全局 SSE 推送 CC_ACTIVE 失败: %s", _e)


async def _deliver_pending_result(workspace: "DBWorkspace", item: dict, *, source: str) -> None:
    """投递单条 CC 待处理结果：写通讯日志 + 广播 + 推送系统消息触发 Agent。

    内置去重机制：同一 (workspace_id, source_chat_key, result_id) 在 TTL 内不会重复投递，
    防止 SSE 实时路径和 Watcher 轮询路径的边缘时序导致重复触发 Agent。

    Args:
        workspace: 工作区 ORM 对象
        item:      CC /pending-results 返回的单条 dict
        source:    投递来源标识（"startup" 或 "watcher"），仅用于日志/消息区分
    """
    source_chat_key: str = item.get("source_chat_key", "")
    result: str = item.get("result", "")
    result_id: str = item.get("id", "")
    is_error: bool = item.get("is_error", False)
    error_code: str = item.get("error_code", "")

    if not source_chat_key or not result.strip():
        logger.debug(f"[cc_workspace] 跳过无效的待投递结果: id={result_id!r}")
        return

    # ── 去重检查 ─────────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).timestamp()
    dedup_key = (workspace.id, source_chat_key, result_id)

    # 清理过期记录
    expired_keys = [k for k, t in _delivered_results.items() if now - t > _DELIVERED_RESULTS_TTL]
    for k in expired_keys:
        _delivered_results.pop(k, None)

    if dedup_key in _delivered_results:
        logger.info(
            f"[cc_workspace] 跳过重复投递({source})：id={result_id!r} "
            f"chat_key={source_chat_key!r} workspace={workspace.id}"
        )
        return

    _delivered_results[dedup_key] = now

    # 写入通讯日志并广播
    try:
        direction = "SYSTEM" if is_error else "CC_TO_NA"
        cc_log = await DBWorkspaceCommLog.create(
            workspace_id=workspace.id,
            direction=direction,
            source_chat_key=source_chat_key,
            content=result if not is_error else f"[CC 错误] {result}",
            is_streaming=False,
            task_id=f"cc_delegate:{source_chat_key}",
        )
        await comm_broadcast.publish(workspace.id, CommLogEntry.from_orm(cc_log))
    except Exception as e:
        logger.warning(f"[cc_workspace] 投递({source})：写入通讯日志失败 (id={result_id!r}): {e}")

    # CC 后台任务完成，广播状态结束
    await _broadcast_cc_status(workspace.id, False, name=workspace.name)

    # 推送系统消息并触发 NA Agent
    try:
        if is_error:
            # 错误结果：明确告知 Agent 这是一个错误，不要盲目重试
            notify_msg = (
                f"[CC Workspace 任务失败] CC 执行委托任务时遇到错误"
                f"（来自工作区: {workspace.name}）。\n"
                f"错误信息: {result}\n"
                + (f"错误代码: {error_code}\n" if error_code else "")
                + "这通常表示 CC 模型服务暂时不可用（API 超时/网络异常/服务过载）。\n"
                "请告知用户 CC 当前不可用，建议稍后重试。不要立即自动重试。"
            )
        elif source == "startup":
            notify_msg = (
                f"[CC Workspace 恢复结果] NA 服务重启前，CC 已完成一个委托任务，"
                f"结果如下（来自工作区: {workspace.name}）：\n\n"
                f"[CC Workspace 执行结果]\n{result}"
            )
        else:
            notify_msg = (
                f"[CC Workspace 后台结果] CC 已完成一个后台委托任务，"
                f"结果如下（来自工作区: {workspace.name}）：\n\n"
                f"[CC Workspace 执行结果]\n{result}"
            )
        await message_service.push_system_message(
            chat_key=source_chat_key,
            agent_messages=notify_msg,
            trigger_agent=True,
        )
        logger.info(
            f"[cc_workspace] 投递成功({source})：chat_key={source_chat_key!r}，"
            f"workspace={workspace.id}，chars={len(result)}"
        )
    except Exception as e:
        logger.error(
            f"[cc_workspace] 投递({source})：推送消息失败 (chat_key={source_chat_key!r}): {e}"
        )


async def _cc_result_watcher_loop() -> None:
    """后台轮询所有 active 工作区的待投递结果，保证 CC 任务结果不丢失。

    设计说明：
    - 每 _WATCHER_INTERVAL 秒轮询一次，CC 结果最大延迟 ≈ _WATCHER_INTERVAL 秒
    - 消费语义：get_pending_results() 取回后 CC 侧自动删除，不会重复投递
    - 与 SSE 实时通道互补：SSE 连通时结果即时到达；SSE 断开/超时时由此兜底
    - 此循环在 NA 整个运行期内持续存在，不受单次 delegate_to_cc 调用影响
    """
    logger.info(f"[cc_workspace] 后台结果监听器已启动（轮询间隔: {_WATCHER_INTERVAL}s）")
    while True:
        await asyncio.sleep(_WATCHER_INTERVAL)
        try:
            active_workspaces = await DBWorkspace.filter(status="active")
        except Exception as e:
            logger.debug(f"[cc_workspace] Watcher：获取工作区列表失败: {e}")
            continue

        for workspace in active_workspaces:
            client = CCSandboxClient(workspace)
            try:
                pending = await client.get_pending_results(workspace_id="default")
            except Exception as e:
                logger.debug(f"[cc_workspace] Watcher：工作区 {workspace.id} 查询失败: {e}")
                continue

            if not pending:
                continue

            logger.info(
                f"[cc_workspace] Watcher 发现 {len(pending)} 条待投递结果，"
                f"工作区: {workspace.name}（ID: {workspace.id}）"
            )
            for item in pending:
                await _deliver_pending_result(workspace, item, source="watcher")


async def recover_pending_cc_results() -> None:
    """NA 启动时扫描所有 active 工作区，取回 CC 在断线期间完成的任务结果，
    并启动后台 Watcher 保证运行期间结果不丢失。

    调用方：nekro_agent/__init__.py on_startup（在 init_plugins 之后）。

    流程：
    1. 遍历所有状态为 active 的工作区
    2. 调用 CC sandbox GET /pending-results（消费语义，取回后自动删除）
    3. 对每条结果：写入 CC_TO_NA 通讯日志、广播到 SSE、推送系统消息并触发 NA Agent
    4. 启动后台 Watcher（_cc_result_watcher_loop），持续轮询保障结果不丢失
    """
    global _cc_result_watcher_task

    try:
        active_workspaces = await DBWorkspace.filter(status="active")
    except Exception as e:
        logger.warning(f"[cc_workspace] 恢复检查：获取工作区列表失败: {e}")
    else:
        for workspace in active_workspaces:
            client = CCSandboxClient(workspace)
            try:
                pending = await client.get_pending_results(workspace_id="default")
            except Exception as e:
                logger.debug(f"[cc_workspace] 恢复检查：工作区 {workspace.id} 查询失败: {e}")
                continue

            if not pending:
                continue

            logger.info(
                f"[cc_workspace] 发现 {len(pending)} 条待投递结果，工作区: {workspace.name}（ID: {workspace.id}）"
            )
            for item in pending:
                await _deliver_pending_result(workspace, item, source="startup")

    # 启动后台 Watcher（幂等：已运行则跳过）
    if _cc_result_watcher_task is None or _cc_result_watcher_task.done():
        _cc_result_watcher_task = asyncio.create_task(_cc_result_watcher_loop())
        logger.info("[cc_workspace] 后台结果监听器已创建")


async def shutdown_cc_result_watcher() -> None:
    """显式取消后台结果监听器，在 NA 关闭时调用，避免 'Task was destroyed' 警告。"""
    global _cc_result_watcher_task
    if _cc_result_watcher_task is not None and not _cc_result_watcher_task.done():
        _cc_result_watcher_task.cancel()
        try:
            await _cc_result_watcher_task
        except asyncio.CancelledError:
            pass
        logger.info("[cc_workspace] 后台结果监听器已停止")
    _cc_result_watcher_task = None


# ---------------------------------------------------------------------------
# 异步任务：后台执行 CC 委托
# ---------------------------------------------------------------------------


@plugin.mount_async_task(_TASK_TYPE)
async def _cc_delegate_task(
    handle: AsyncTaskHandle,
    workspace_id: int,
    task_prompt: str,
) -> AsyncGenerator[TaskCtl, None]:
    """后台通过 SSE 流式与 CC Sandbox 通信，完成后向主 Agent 推送结果"""
    workspace = await DBWorkspace.get_or_none(id=workspace_id)
    if workspace is None:
        yield TaskCtl.fail(f"工作区 {workspace_id} 不存在")
        return

    if workspace.status != "active":
        yield TaskCtl.fail(f"工作区 '{workspace.name}' 当前状态为 {workspace.status}，无法执行任务")
        return

    client = CCSandboxClient(workspace)
    _queued_messages: list[str] = []
    chunks: list[str] = []
    chunk_count = 0
    started_at = int(time.time() * 1000)
    current_tool_name: Optional[str] = None
    operation_block_count = 0

    _now_str = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    _envelope = CcPromptEnvelope.for_na_path(
        source_chat_key=handle.task_id,
        current_time=_now_str,
        task_body=task_prompt,
    )
    enriched_prompt = _envelope.to_prompt()

    async def _publish_runtime_status(
        *,
        active: bool,
        phase: Literal["queued", "running", "responding", "completed", "failed", "cancelled"] = "running",
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
                    active=active,
                    name=workspace.name,
                    started_at=started_at,
                    updated_at=int(time.time() * 1000),
                    phase=phase,
                    current_tool=current_tool,
                    source_chat_key=handle.task_id,
                    queue_length=queue_length,
                    operation_block_count=operation_block_count,
                    last_block_kind=last_block_kind,
                    last_block_summary=last_block_summary,
                    error_summary=error_summary,
                )
            )
        except Exception as e:
            logger.warning("[cc_workspace] 全局 SSE 推送 runtime_status 失败: %s", e)

    # 持久化 NA_TO_CC 日志并广播：content 存纯任务正文，extra_data 存结构化元信息
    try:
        _na_log = await DBWorkspaceCommLog.create(
            workspace_id=workspace_id,
            direction="NA_TO_CC",
            source_chat_key=handle.task_id,
            content=task_prompt,
            extra_data=_envelope.to_metadata_json(),
            task_id=f"cc_delegate:{handle.task_id}",
        )
        await comm_broadcast.publish(workspace_id, CommLogEntry.from_orm(_na_log))
    except Exception:
        pass

    # 广播 CC 任务开始状态（SSE 驱动前端状态指示条，避免轮询）
    await _broadcast_cc_status(workspace_id, True, name=workspace.name, started_at=started_at)
    await _publish_runtime_status(active=True, phase="running")

    try:
        yield TaskCtl.report_progress("CC Sandbox 任务已开始执行...", percent=0)
        logger.info(
            f"[cc_workspace] cc_delegate 开始: workspace={workspace_id} "
            f"chat_key={handle.task_id!r} prompt_len={len(task_prompt)}"
        )

        async def _on_queued(event: dict) -> None:
            queued_event = SandboxQueuedChunk.model_validate(event)
            current = event.get("current_task") or {}
            src = current.get("source_chat_key", "未知频道")
            elapsed = current.get("elapsed_seconds", 0)
            pos = event.get("position", "?")
            _queued_messages.append(
                f"CC 工作区被占用（来源: {src}，已运行 {elapsed:.0f}s），排队第 {pos} 位..."
            )
            await _publish_runtime_status(
                active=True,
                phase="queued",
                current_tool=current_tool_name,
                queue_length=queued_event.queue_length,
            )

        _env_vars = await workspace_resource_service.resolve_workspace_resources_to_env(workspace.id)
        # 使用 asyncio.wait_for 保护每次 __anext__() 等待：
        _cc_data_timeout = cc_config.CC_DATA_TIMEOUT
        # _cc_data_timeout 仅在"无任何 data: 事件"时触发，keep-alive (": ping") 不计入，
        # 避免 CC 一直发 keep-alive 导致 httpx read timeout 永远无法触发的永久挂死问题。
        _stream = client.stream_message(
            enriched_prompt,
            source_chat_key=handle.task_id,
            on_queued=_on_queued,
            env_vars=_env_vars or None,
        )
        while True:
            try:
                item = await asyncio.wait_for(_stream.__anext__(), timeout=_cc_data_timeout)
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                # 主动关闭 SSE 流
                try:
                    await asyncio.wait_for(_stream.aclose(), timeout=5.0)
                except Exception:
                    pass
                # 主动中止 CC 侧任务——不再让 CC 在后台继续空转
                try:
                    await client.force_cancel_current_task(workspace_id="default")
                except Exception:
                    pass
                logger.warning(
                    f"[cc_workspace] SSE 数据超时（{int(_cc_data_timeout)}s 无有效响应），"
                    f"已主动中止 CC 任务。workspace={workspace_id} chat_key={handle.task_id!r} "
                    f"received_chunks={chunk_count} received_chars={sum(len(c) for c in chunks)}"
                )
                # 写入 SYSTEM 方向 CommLog，前端 CommTab 可感知
                _timeout_notice = (
                    f"[CC 任务超时中止] {_cc_data_timeout:.0f}s 内未收到任何数据，"
                    "NA 已主动中止该 CC 任务。这通常意味着 CC 模型服务不可用或网络异常。"
                )
                try:
                    _sys_log = await DBWorkspaceCommLog.create(
                        workspace_id=workspace_id,
                        direction="SYSTEM",
                        source_chat_key=handle.task_id,
                        content=_timeout_notice,
                        is_streaming=False,
                        task_id=f"cc_delegate:{handle.task_id}",
                    )
                    await comm_broadcast.publish(workspace_id, CommLogEntry.from_orm(_sys_log))
                except Exception as _e:
                    logger.warning(f"[cc_workspace] 写入超时 SYSTEM CommLog 失败: {_e}")
                await _publish_runtime_status(
                    active=True,
                    phase="failed",
                    current_tool=current_tool_name,
                    error_summary=_summarize_runtime_block_text(_timeout_notice, max_length=96),
                )
                await _broadcast_cc_status(workspace_id, False, started_at=started_at)
                await _publish_runtime_status(active=False)
                yield TaskCtl.fail(
                    f"CC Sandbox 执行超时（{_cc_data_timeout:.0f}s 内无任何响应），任务已被中止。\n"
                    "这通常表示 CC 模型服务暂时不可用（API 超时/网络异常/服务过载）。\n"
                    "请告知用户 CC 当前不可用，建议稍后重试。不要立即自动重试，连续重试只会浪费时间。"
                )
                return

            if handle.is_cancelled:
                try:
                    await asyncio.wait_for(_stream.aclose(), timeout=5.0)
                except Exception:
                    pass
                await _publish_runtime_status(active=True, phase="cancelled", current_tool=current_tool_name)
                await _broadcast_cc_status(workspace_id, False, started_at=started_at)
                await _publish_runtime_status(active=False)
                yield TaskCtl.cancel("任务被用户取消")
                return

            # 检查并 flush 排队消息
            while _queued_messages:
                msg = _queued_messages.pop(0)
                yield TaskCtl.report_progress(msg, percent=0)

            if isinstance(item, dict):
                # tool_call / tool_result 事件 — 写入通讯日志并广播（失败不阻断）
                tool_chunk = SandboxToolChunk.model_validate(item)
                if tool_chunk.type in ("tool_call", "tool_result"):
                    try:
                        operation_block_count += 1
                        direction = "TOOL_CALL" if tool_chunk.type == "tool_call" else "TOOL_RESULT"
                        _tool_log = await DBWorkspaceCommLog.create(
                            workspace_id=workspace_id,
                            direction=direction,
                            source_chat_key=handle.task_id,
                            content=json.dumps(item, ensure_ascii=False),
                            task_id=f"cc_delegate:{handle.task_id}",
                        )
                        await comm_broadcast.publish(workspace_id, CommLogEntry.from_orm(_tool_log))
                        if tool_chunk.type == "tool_call":
                            current_tool_name = tool_chunk.name
                            await _publish_runtime_status(
                                active=True,
                                phase="running",
                                current_tool=current_tool_name,
                                last_block_kind="tool_call",
                                last_block_summary=current_tool_name,
                            )
                        elif current_tool_name is not None:
                            await _publish_runtime_status(
                                active=True,
                                phase="running",
                                current_tool=None,
                                last_block_kind="tool_result",
                                last_block_summary=current_tool_name,
                            )
                            current_tool_name = None
                        else:
                            await _publish_runtime_status(
                                active=True,
                                phase="running",
                                current_tool=None,
                                last_block_kind="tool_result",
                                last_block_summary=tool_chunk.name,
                            )
                    except Exception:
                        pass
            else:
                chunks.append(item)
                chunk_count += 1
                operation_block_count += 1
                # 每 20 个 chunk 汇报一次进度，避免过于频繁
                if chunk_count % 20 == 0:
                    yield TaskCtl.report_progress(f"执行中（已收到 {chunk_count} 个数据块）", percent=50)
                if current_tool_name is not None:
                    current_tool_name = None
                await _publish_runtime_status(
                    active=True,
                    phase="responding",
                    last_block_kind="text_chunk",
                    last_block_summary=_summarize_runtime_block_text(item),
                )

        full_result = "".join(chunks)

        # 持久化 CC_TO_NA 日志并广播（失败不阻断主流程）
        try:
            _cc_log = await DBWorkspaceCommLog.create(
                workspace_id=workspace_id,
                direction="CC_TO_NA",
                source_chat_key=handle.task_id,
                content=full_result,
                is_streaming=True,
                task_id=f"cc_delegate:{handle.task_id}",
            )
            await comm_broadcast.publish(workspace_id, CommLogEntry.from_orm(_cc_log))
        except Exception:
            pass

        # CC 已完成回复，任务将在此后 success/fail 结束，广播状态结束
        await _publish_runtime_status(
            active=True,
            phase="completed",
            last_block_kind="text_chunk" if full_result.strip() else None,
            last_block_summary=_summarize_runtime_block_text(full_result) if full_result.strip() else None,
        )
        await _broadcast_cc_status(workspace_id, False, started_at=started_at)
        await _publish_runtime_status(active=False)

        # 检测未登录状态：仅当响应内容极短（<300字符）且明确含有 auth 错误关键词时才判定
        # 不能用 "/login" 等宽泛字符串，CC 输出的正常内容（URL、路径等）会误触
        _result_lower = full_result.lower().strip()
        _is_auth_error = len(_result_lower) < 300 and (
            "not logged in" in _result_lower
            or _result_lower.startswith("error: not authenticated")
            or _result_lower.startswith("authentication required")
        )
        if _is_auth_error:
            logger.warning(f"[cc_workspace] CC Sandbox 未认证，workspace={workspace_id}")
            await _broadcast_error_comm_log(
                workspace_id, handle.task_id,
                "[CC 错误] CC Sandbox 未认证，无法执行任务。\n"
                "请在工作区「配置」页面关联有效的 CC 模型预设（需包含 auth_token），然后重建容器使配置生效。"
            )
            yield TaskCtl.fail(
                "CC Sandbox 未认证。请在工作区「配置」页面关联有效的 CC 模型预设（需包含 auth_token），然后重建容器使配置生效。"
            )
            return

        if not full_result.strip():
            await _broadcast_error_comm_log(workspace_id, handle.task_id, "[CC 错误] CC Sandbox 返回了空响应")
            yield TaskCtl.fail("CC Sandbox 返回了空响应")
            return

        logger.info(f"[cc_workspace] cc_delegate 完成，workspace={workspace_id}，响应长度={len(full_result)}")
        yield TaskCtl.success(f"[CC Workspace 执行结果]\n{full_result}", data=full_result)

    except CCSandboxError as e:
        logger.error(
            f"[cc_workspace] cc_delegate 流式执行失败: {e} "
            f"workspace={workspace_id} chat_key={handle.task_id!r} "
            f"received_chunks={chunk_count} received_chars={sum(len(c) for c in chunks)}"
        )
        await _broadcast_error_comm_log(workspace_id, handle.task_id, f"[CC 错误] CC Sandbox 执行失败: {e}")
        await _publish_runtime_status(
            active=True,
            phase="failed",
            current_tool=current_tool_name,
            error_summary=_summarize_runtime_block_text(str(e), max_length=96),
        )
        await _broadcast_cc_status(workspace_id, False, started_at=started_at)
        await _publish_runtime_status(active=False)
        yield TaskCtl.fail(f"CC Sandbox 执行失败: {e}")
    except Exception as e:
        logger.exception(
            f"[cc_workspace] cc_delegate 异常: {e} "
            f"workspace={workspace_id} chat_key={handle.task_id!r}"
        )
        await _broadcast_error_comm_log(workspace_id, handle.task_id, f"[CC 错误] CC Workspace 发生意外错误: {e}")
        await _publish_runtime_status(
            active=True,
            phase="failed",
            current_tool=current_tool_name,
            error_summary=_summarize_runtime_block_text(str(e), max_length=96),
        )
        await _broadcast_cc_status(workspace_id, False, started_at=started_at)
        await _publish_runtime_status(active=False)
        yield TaskCtl.fail(f"CC Workspace 发生意外错误: {e}")


# ---------------------------------------------------------------------------
# Prompt 注入
# ---------------------------------------------------------------------------


@plugin.mount_prompt_inject_method("cc_workspace_status")
async def cc_workspace_status(_ctx: schemas.AgentCtx) -> str:
    """向主 Agent 系统提示词注入当前频道绑定的 CC Workspace 信息"""
    workspace = await _ctx.get_bound_workspace()

    # ── 状态1：未绑定工作区 ──────────────────────────────────────────────────
    if workspace is None:
        return (
            "[CC Workspace] Unbound\n"
            "CC Workspace is an isolated Claude Code sandbox for persistent code execution, file handling, and command execution.\n"
            "Use `create_and_bind_workspace` to create and bind one, then `start_cc_sandbox` to start it.\n"
            "For special requirements such as custom images or runtime policies, guide the user to create it manually in the workspace management page.\n"
        )

    # ── 状态2：已绑定工作区，但沙盒未运行 ──────────────────────────────────
    if workspace.status != "active":
        status_label = {"stopped": "Stopped", "failed": "Start failed", "deleting": "Deleting"}.get(workspace.status, workspace.status)
        error_hint = f" (error: {workspace.last_error[:50]}...)" if workspace.last_error else ""
        return (
            f"[CC Workspace] {workspace.name} - {status_label}{error_hint}\n"
            f"{'Ask the user to check the workspace management page.' if workspace.last_error else 'It can be started with `start_cc_sandbox`.'}\n"
        )

    # ── 状态3：工作区正常运行 ────────────────────────────────────────────────

    client = CCSandboxClient(workspace)

    # 并发获取 CC 状态和队列信息（原串行调用最坏延迟 20s → 并发后 10s）
    _status_raw, _queue_raw = await asyncio.gather(
        client.get_sandbox_status(),
        client.get_workspace_queue(workspace_id="default"),
        return_exceptions=True,
    )
    _cc_unreachable = isinstance(_status_raw, BaseException)
    if _cc_unreachable:
        status_info: dict = {}
    else:
        status_info = _status_raw  # type: ignore[assignment]
    if isinstance(_queue_raw, BaseException):
        queue_status_raw: dict = {"workspace_id": "default", "current_task": None, "queued_tasks": [], "queue_length": 0}
    else:
        queue_status_raw = _queue_raw

    # 容器不可达
    if _cc_unreachable:
        return (
            f"[CC Workspace] {workspace.name} - Connection error\n"
            f"The container is unreachable. Ask the user to check the workspace management page and restart the container. CC tools are currently unavailable.\n"
        )

    # CC 应用状态：仅在异常时提示
    ws_status = status_info.get("status", "")
    _NORMAL_CC_STATES = {"idle", "busy", "running", "ready", ""}
    status_hint = "" if ws_status in _NORMAL_CC_STATES else f"CC application status is abnormal: {ws_status}\n"

    # 能力摘要（skills + MCP）— 只列名称，不列描述
    capability_hint = ""
    try:
        selected_skills: List[str] = workspace.metadata.get("skills", [])
        dynamic_skills = await asyncio.to_thread(WorkspaceService.list_dynamic_skills, workspace.id)
        mcp_servers = (workspace.metadata.get("mcp_config") or {}).get("mcpServers", {})
        parts = []
        if selected_skills:
            parts.append(f"Skills: {', '.join(selected_skills)}")
        if dynamic_skills:
            parts.append(f"Dynamic skills: {', '.join(s['name'] for s in dynamic_skills)}")
        if mcp_servers:
            parts.append(f"MCP: {', '.join(mcp_servers.keys())}")
        if parts:
            capability_hint = " | ".join(parts) + "\n"
    except Exception:
        pass

    # 记忆摘要（_na_context.md）— 可配置最大长度，超出时截断
    memory_hint = ""
    try:
        na_context, updated = await asyncio.to_thread(WorkspaceService.read_na_context, workspace.id)
        if na_context.strip():
            max_len = cc_config.MEMORY_SUMMARY_MAX_LENGTH
            time_str = f" (updated at {updated})" if updated else ""
            if len(na_context) > max_len:
                short_context = na_context[:max_len] + "..."
                memory_hint = f"\n[CC Workspace Memory Summary]{time_str}\n{short_context}\n"
            else:
                memory_hint = f"\n[CC Workspace Memory Summary]{time_str}\n{na_context}\n"
    except Exception:
        pass

    # 合并任务/队列状态
    task_hint = ""
    is_running = bool(_ctx.from_chat_key and task_api.is_running(_TASK_TYPE, _ctx.from_chat_key))
    try:
        current_task = queue_status_raw.get("current_task")
        queue_len = queue_status_raw.get("queue_length", 0)

        if current_task:
            src = current_task.get("source_chat_key", "")
            elapsed = current_task.get("elapsed_seconds", 0)
            preview = current_task.get("prompt_preview", "")
            preview_str = (preview[:50] + "...") if len(preview) > 50 else preview
            is_mine = is_running and src == _ctx.from_chat_key

            if is_mine:
                task_hint = (
                    f"\n[Task Running] Running for {elapsed:.0f}s. The result will be returned automatically when complete.\n"
                    f"Task: {preview_str}\n"
                    f"Use `cancel_cc_task` to cancel it or `get_cc_context` to inspect context.\n"
                )
            elif is_running:
                task_hint = (
                    f"\n[Queued] The workspace is busy ({elapsed:.0f}s). Queue length: {queue_len}\n"
                    f"Use `cancel_cc_task` to stop waiting, or `force_cancel_cc_workspace` to preempt.\n"
                )
            else:
                task_hint = (
                    f"\n[Workspace Busy] Another channel is running a task ({elapsed:.0f}s).\n"
                    f"Task: {preview_str}\n"
                    f"A new delegated task will be queued automatically. Use `force_cancel_cc_workspace` if you must preempt it.\n"
                )
        elif is_running:
            task_hint = "\n[Task Submitted] Waiting for CC to accept it. The result will be returned automatically when complete.\n"
    except Exception:
        if is_running:
            task_hint = "\n[Task Running] The result will be returned automatically when complete. Use `get_cc_context` to inspect it or `cancel_cc_task` to cancel it.\n"

    # 扫描 shared 目录 — 显示文件名、大小、更新时间
    shared_files_hint = ""
    try:
        shared_files = await asyncio.to_thread(
            WorkspaceService.scan_shared_dir,
            workspace.id, cc_config.SHARED_DIR_MAX_FILES,
        )
        if shared_files:
            lines = [f"  {f['rel_path']} ({f['size_human']}, {f['mtime_str']})" for f in shared_files]
            shared_files_hint = (
                f"\n[shared/ Directory] {len(shared_files)} most recently updated files:\n"
                + "\n".join(lines)
                + "\nUse `download_file_from_cc` to retrieve these files or any other file in the workspace.\n"
            )
    except Exception:
        pass

    # 多频道感知 — 显示频道列表和角色
    multi_channel_hint = ""
    try:
        from nekro_agent.models.db_chat_channel import DBChatChannel

        bound_channels = await DBChatChannel.filter(workspace_id=workspace.id).all()
        if len(bound_channels) >= 2:
            annotations = await asyncio.to_thread(WorkspaceService.get_channel_annotations, workspace)
            bound_keys = [ch.chat_key for ch in bound_channels]
            primary_key = WorkspaceService.get_primary_channel_chat_key(workspace, bound_keys)
            current_chat_key = _ctx.from_chat_key or ""

            channel_lines: List[str] = []
            for ch in bound_channels:
                ann = annotations.get(ch.chat_key)
                desc = f": {ann.description}" if ann and ann.description else ""
                role = "Primary" if ch.chat_key == primary_key else "Collaborative"
                marker = " <- current" if ch.chat_key == current_chat_key else ""
                channel_lines.append(f"  [{role}] {ch.channel_name or ch.chat_key}{desc}{marker}")

            multi_channel_hint = (
                f"\n[Multi-channel Workspace] {len(bound_channels)} channels are bound:\n"
                + "\n".join(channel_lines)
                + "\nTo message another channel, specify the target chat_key in task_prompt and NA will route it there.\n"
            )
    except Exception:
        pass

    result = (
        f"[CC Workspace]\n"
        f"The current channel is bound to CC Workspace: {workspace.name} (ID: {workspace.id})\n"
        f"Runtime policy: {workspace.runtime_policy}\n"
        f"{status_hint}"
        f"{capability_hint}"
        f"{memory_hint}"
        f"{multi_channel_hint}"
        f"{task_hint}"
        f"{shared_files_hint}"
        f"\n"
        f"[Delegation Preconditions]\n"
        f"- Use `delegate_to_cc` only for tasks that **you have already defined clearly**. Do not dump a vague problem onto CC and expect it to infer the task.\n"
        f"- Before delegating, make sure you know which project is being handled, what exactly needs to be investigated or changed, and what deliverable is expected.\n"
        f"- The current workspace is only an available execution environment. It does not mean the project, screenshot, PR, or error mentioned by the user already exists here.\n"
        f"- If the target project or materials are not in the current workspace, first specify how to obtain them, then ask CC to clone the repo, check out the branch, download files, or inspect the given path.\n"
        f"- If the project source, error source, or target version is unclear, ask the user to clarify first. Do not issue tasks that cannot be verified or completed.\n"
        f"\n"
        f"[CC Collaboration Rules]\n"
        f"**CC cannot see your conversation with the user.** `task_prompt` is CC's only source of context and must be self-contained:\n"
        f"- Include the full requirement, background, and constraints; quote key facts directly when useful, such as error logs and the user's description.\n"
        f"- The task target must be explicit: project name, repository source, branch or commit, and the relevant files or directories. Provide at least enough information for CC to start correctly.\n"
        f"- If the code is not in the current workspace, explicitly tell CC where to obtain it. Never assume it is already present.\n"
        f"- You cannot read CC's workspace. Do not assume specific files or functions exist there; let CC verify user-mentioned paths on its own.\n"
        f"- Describe the goal rather than prescribing every step, so CC can explore and choose the implementation path.\n"
        f"- If CC responds with `[Need Clarification]`, relay that to the user before deciding the next step.\n"
        f"\n"
        f"[Delivery Requirement - The user cannot access CC Workspace]\n"
        f"**The user cannot see CC's work process or raw response.** You must ensure the result reaches the user:\n"
        f"- **Code changes**: ask CC to create a PR or push a branch, then tell the user the link.\n"
        f"- **Generated files**: have CC write them into `shared/`, then use `download_file_from_cc` to retrieve and send them.\n"
        f"- **Analysis results**: relay them clearly to the user, or retrieve and send the report file.\n"
        f"When delegating, specify the delivery method, such as `create a PR and return the link` or `write the report to shared/report.md`.\n"
    )

    # ── 人设融合模式 ──────────────────────────────────
    if cc_config.MERGE_CC_AS_SELF:
        result += (
            "\n[Role Merge]\n"
            "Do not expose internal concepts such as CC Workspace, sandbox, or delegation to the user. From the user's perspective, you are a single capable assistant:\n"
            "- Say `I'll handle it` instead of `I'll delegate this to CC`.\n"
            "- Say `I've completed it` instead of `CC returned the result`.\n"
            "- Avoid terms like `workspace` or `container` in user-facing replies.\n"
        )

    return result


# ---------------------------------------------------------------------------
# Sandbox 方法
# ---------------------------------------------------------------------------


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "创建并绑定 CC Workspace",
    description=(
        "为当前会话创建专属的 CC Workspace 沙盒环境并自动绑定。"
        "创建后需调用 start_cc_sandbox 启动容器才能开始使用。"
        "如果用户有特殊需求（自定义镜像、运行策略等），建议引导其在工作区管理页面手动创建。"
    ),
)
async def create_and_bind_workspace(_ctx: schemas.AgentCtx, workspace_name: str = "") -> str:
    """Create a new CC Workspace and bind it to the current channel.

    This sets up a dedicated Claude Code sandbox environment for this channel.
    After creation, call `start_cc_sandbox` to launch the sandbox container.

    If the user has special requirements (custom image, specific runtime policy, etc.),
    inform them to create the workspace manually in the workspace management page instead.

    Args:
        workspace_name (str): Name for the new workspace. Leave empty to auto-generate.
            If a workspace with the same name already exists, a numeric suffix is added.

    Returns:
        str: Result message with workspace info and next steps.

    Example:
        ```python
        # Auto-generate a name
        create_and_bind_workspace()

        # Or provide a descriptive name based on user's intent
        create_and_bind_workspace("data-analysis")
        ```
    """
    chat_key = _ctx.from_chat_key

    # 当前频道已绑定工作区时，不允许重复创建
    existing = await _ctx.get_bound_workspace()
    if existing is not None:
        raise ValueError(
            f"当前频道已绑定工作区 '{existing.name}'（ID: {existing.id}，状态: {existing.status}）。"
            f"如果沙盒未运行，请调用 `start_cc_sandbox` 启动容器。"
        )

    # 生成唯一工作区名称
    base_name = workspace_name.strip() or f"workspace-{secrets.token_hex(3)}"
    final_name = base_name
    counter = 1
    while await DBWorkspace.get_or_none(name=final_name):
        final_name = f"{base_name}-{counter}"
        counter += 1

    # 创建工作区 DB 记录
    try:
        ws = await DBWorkspace.create(
            name=final_name,
            description=f"由 NA 自动为频道 {chat_key} 创建",
            runtime_policy="agent",
        )
        # 自动注入默认技能
        from nekro_agent.core.auto_inject_skills import get_auto_inject_skills

        auto_skills = get_auto_inject_skills()
        if auto_skills:
            valid_names = {s["name"] for s in WorkspaceService.list_all_skills()}
            injected = [n for n in auto_skills if n in valid_names]
            if injected:
                metadata = ws.metadata or {}
                metadata["skills"] = injected
                ws.metadata = metadata
                await ws.save(update_fields=["metadata"])
    except Exception as e:
        logger.error(f"[cc_workspace] 创建工作区失败: {e}")
        raise ValueError(f"创建工作区失败：{e}") from e

    # 绑定到当前频道
    try:
        await WorkspaceService.bind_channel(ws, chat_key)
    except Exception as e:
        logger.error(f"[cc_workspace] 绑定工作区到频道失败: {e}")
        try:
            await ws.delete()
        except Exception:
            pass
        raise ValueError(f"工作区创建成功但绑定到当前频道失败：{e}") from e

    logger.info(f"[cc_workspace] 已创建并绑定工作区: {final_name}（ID: {ws.id}），chat_key={chat_key}")
    return (
        f"工作区已创建并绑定到当前频道。\n"
        f"工作区名称: {final_name}（ID: {ws.id}）\n"
        f"运行策略: agent\n"
        f"下一步：调用 `start_cc_sandbox` 启动沙盒容器，即可开始使用 CC Workspace。"
    )


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "启动 CC 沙盒容器",
    description=(
        "启动绑定工作区的 CC 沙盒 Docker 容器，并等待健康检查通过（最长等待约 60 秒）。"
        "若本地缺少镜像，会返回 docker pull 命令供用户执行。"
        "容器运行后即可通过 delegate_to_cc 委托任务。"
    ),
)
async def start_cc_sandbox(_ctx: schemas.AgentCtx) -> str:
    """Start the CC sandbox container for the bound workspace.

    This launches a Docker container running the CC sandbox (claude-code sandbox).
    The method first checks if the sandbox Docker image is available locally.
    If the image is missing, it returns a `docker pull` command for the user to run.

    This is a blocking operation that waits for the container health check to pass
    (up to the configured startup timeout, typically 60 seconds).

    Returns:
        str: Success message, or error/guidance information.

    Example:
        ```python
        start_cc_sandbox()
        ```
    """
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        raise ValueError("当前频道未绑定工作区，请先调用 `create_and_bind_workspace` 创建工作区。")

    if workspace.status == "active":
        raise ValueError(
            f"工作区 '{workspace.name}' 的沙盒已在运行中，无需重复启动。可通过 `delegate_to_cc` 直接委托任务。"
        )

    # 确定镜像名称并检查本地是否存在
    image_name = workspace.sandbox_image or app_config.CC_SANDBOX_IMAGE
    image_tag = workspace.sandbox_version or app_config.CC_SANDBOX_IMAGE_TAG
    image = f"{image_name}:{image_tag}"

    image_exists = await _check_sandbox_image_exists(image)
    if not image_exists:
        raise ValueError(
            f"本地未找到沙盒镜像 `{image}`，无法启动容器。\n"
            f"请通知用户在宿主机（或 NA 容器内）执行以下命令拉取镜像：\n"
            f"docker pull {image}\n"
            f"拉取完成后，重新调用 `start_cc_sandbox` 即可启动。"
        )

    # 启动容器（等待健康检查通过）
    try:
        await SandboxContainerManager.create_and_start(workspace)
        logger.info(f"[cc_workspace] 沙盒已启动: workspace={workspace.name}（ID: {workspace.id}）")
        return (
            f"沙盒已成功启动！\n"
            f"工作区: {workspace.name}（ID: {workspace.id}）\n"
            f"现在可以通过 `delegate_to_cc` 向 CC Workspace 委托编程任务了。"
        )
    except RuntimeError as e:
        logger.error(f"[cc_workspace] 启动沙盒失败: {e}")
        raise ValueError(
            f"沙盒启动失败：{e}\n"
            f"可能原因：容器健康检查超时，或镜像/配置异常。"
            f"建议告知用户检查 Docker 日志，或在工作区管理页面查看详细错误信息。"
        ) from e
    except Exception as e:
        logger.error(f"[cc_workspace] 启动沙盒异常: {e}")
        raise ValueError(f"启动沙盒时发生意外错误：{e}") from e


@plugin.mount_sandbox_method(
    SandboxMethodType.BEHAVIOR,
    "委托任务给 CC Workspace 后台执行",
    description=(
        "将编程、文件处理、命令执行等复杂任务异步委托给 CC Workspace（claude-code 沙盒）后台运行，"
        "完成后自动将结果推送回本会话并触发 NA 继续响应。"
        "task_prompt 应描述目标和背景，而非假设具体文件路径或代码细节——CC 会自行探索工作区。"
        "每个频道同时只能有一个 CC 任务在运行。"
    ),
)
async def delegate_to_cc(_ctx: schemas.AgentCtx, task_prompt: str) -> str:
    """Delegate a task to the bound CC Workspace (claude-code sandbox) asynchronously.

    The task runs in the background via streaming. When complete, the result will be
    automatically pushed back to this conversation as a system message, and you will be
    triggered to respond with the CC result.

    **When to use**: Long coding tasks, shell commands, multi-step file processing, anything
    requiring a persistent tool environment.

    **Note**: Only one CC task can run per channel at a time. Use `cancel_cc_task` to
    cancel the current task before starting a new one.

    **CRITICAL — CC cannot see your conversation.**
    CC is a completely separate AI process. It has NO access to the chat history in this
    channel. The `task_prompt` you provide is the ONLY information CC will receive.
    You MUST write task_prompt as a **self-contained brief** that includes everything CC
    needs to know:

    1. **Include full context**: User's intent, relevant background, technical requirements,
       and constraints — do NOT assume CC already knows the current topic or anything
       discussed earlier in this conversation.
    2. **Quote key details verbatim**: If the user provided error messages, log snippets,
       specific requirements, or technical details, copy them into the task_prompt as-is.
       Do NOT summarize or omit them.
    3. **Do NOT assume workspace internals**: CC has direct access to the workspace files;
       you do NOT. Never assume specific file paths, function names, or code structure.
    4. **User-mentioned paths need verification**: If the user mentioned a file/function/path,
       phrase it as "the user mentioned X — please verify it exists", not as a fact.
    5. **Describe goals, not steps**: Tell CC WHAT to achieve and WHY, then let CC explore
       the workspace and decide HOW. Never give line-level code edit instructions.
    6. **Relay clarification requests**: If CC's response contains "[需要澄清]" questions,
       relay them to the user before delegating again.
    7. **Negotiate output format**: If the task produces substantial output (analysis, report,
       documentation), instruct CC to write the result to a file (e.g., `/workspace/default/shared/report.md`)
       so you can retrieve it via `download_file_from_cc`. For short results, CC can return
       them directly in its response text.

    Args:
        task_prompt (str): A self-contained task description including the user's full
            intent, all relevant context from the conversation, and any constraints.
            This is the ONLY information CC will receive — nothing else is available to it.

    Returns:
        str: Confirmation that the task has been started asynchronously (NOT the final result —
             the result will come back automatically when execution is complete).

    Example (CORRECT — self-contained, goal-oriented):
        ```python
        delegate_to_cc(
            "用户希望在项目中添加一个用户注册功能。具体需求：支持邮箱+密码注册，"
            "需要邮箱格式校验和密码强度检查（至少8位，含大小写和数字）。"
            "用户提到项目使用 FastAPI + SQLAlchemy（请自行确认技术栈）。"
            "请探索工作区了解项目结构后实现此功能。"
        )
        ```

    Example (WRONG — assumes CC knows the conversation context):
        ```python
        # 错误：CC 不知道「用户刚才说的那个 bug」是什么
        delegate_to_cc("修一下用户刚才说的那个 bug")
        ```

    Example (WRONG — assumes workspace internals):
        ```python
        # 错误：假设了不确定存在的路径和代码细节
        delegate_to_cc("请修改 ./src/utils.py 第42行的 calculate() 函数，将参数 n 改为 count")
        ```
    """
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        raise ValueError("当前频道未绑定任何 CC Workspace，无法委托任务。请先在工作区管理页面绑定频道。")

    if workspace.status != "active":
        raise ValueError(
            f"工作区 '{workspace.name}' 当前状态为 {workspace.status}，无法接受任务。请先启动工作区后重试。"
        )

    chat_key = _ctx.from_chat_key
    task_id = chat_key  # 每个频道同时只允许一个 CC 任务

    if task_api.is_running(_TASK_TYPE, task_id):
        raise ValueError(
            "当前频道已有 CC 任务在后台执行中。"
            "请等待当前任务完成，或使用 `cancel_cc_task` 取消后再委托新任务。"
        )

    # 持久化 task_prompt，供结果回传时提醒 NA 本次任务的原始目标
    await plugin.store.set(chat_key=chat_key, store_key="last_cc_task_prompt", value=task_prompt)

    # 检查记忆摘要是否超限，自动附加整理指令
    try:
        na_context, _ = await asyncio.to_thread(WorkspaceService.read_na_context, workspace.id)
        if na_context and len(na_context) > cc_config.MEMORY_SUMMARY_MAX_LENGTH:
            task_prompt = (
                f"{task_prompt}\n\n"
                f"---\n"
                f"[系统附加] 工作区记忆摘要 _na_context.md 已超限（{len(na_context)}/{cc_config.MEMORY_SUMMARY_MAX_LENGTH}字符），"
                f"请在完成主任务后整理该文件：精简历史记录，删除过时信息，保留关键上下文。"
            )
    except Exception:
        pass

    try:
        prompt_layers = (workspace.metadata or {}).get("prompt_layers") or {}
        na_context_meta = prompt_layers.get("na_context_meta") if isinstance(prompt_layers, dict) else {}
        if isinstance(na_context_meta, dict) and na_context_meta.get("last_editor") == "manual":
            task_prompt = (
                f"{task_prompt}\n\n"
                "---\n"
                "[系统附加] `_na_context.md` 最近由用户手动修订。请在开始任务前先查看该文件的最新版本，"
                "将其视为 NA 与 CC 的协作现状摘要；若其中信息与实际工作区状态不一致，以当前工作区现实为准并按需更新。"
                "如果某些内容应保持人工固定、不应继续改写，请提醒用户改写到固定事实层而不是 `_na_context.md`。"
            )
    except Exception:
        pass

    # on_terminal 异步辅助：在任务终态时读取存储的原始提示词并推送给主 Agent
    async def _push_result(ctl: TaskCtl) -> None:
        stored_prompt = await plugin.store.get(chat_key=chat_key, store_key="last_cc_task_prompt") or ""
        if stored_prompt:
            prompt_preview = stored_prompt[:300] + ("..." if len(stored_prompt) > 300 else "")
            task_ctx_section = f"\n\n[本次委托给 CC 的原始任务摘要]\n{prompt_preview}"
        else:
            task_ctx_section = ""

        if ctl.signal.value == "success":
            notify_msg = f"{ctl.message}{task_ctx_section}"
        elif ctl.signal.value == "fail":
            notify_msg = (
                f"[CC Workspace] CC 任务执行失败: {ctl.message}{task_ctx_section}\n\n"
                "如果这是由管理员手动中止或网络中断引起的，请告知用户任务已被终止，并等待指示，不要盲目重试。"
            )
        elif ctl.signal.value == "cancel":
            notify_msg = (
                f"[CC Workspace] CC 任务已被管理员手动中止。{task_ctx_section}\n\n"
                "此次任务是由管理员主动操作终止的，并非执行错误或异常。请不要盲目重试或重新委托！"
            )
        else:
            return

        await message_service.push_system_message(
            chat_key=chat_key,
            agent_messages=notify_msg,
            trigger_agent=True,
        )

    def on_terminal(ctl: TaskCtl) -> None:
        asyncio.create_task(_push_result(ctl))

    try:
        await task_api.start(
            _TASK_TYPE,
            task_id,
            chat_key,
            plugin,
            workspace_id=workspace.id,
            task_prompt=task_prompt,
            on_terminal=on_terminal,
        )
        logger.info(f"[cc_workspace] 已启动 CC 委托任务，chat_key={chat_key}，workspace={workspace.id}")
        return (
            f"[CC Workspace] 任务已提交给 CC Workspace 后台执行。\n"
            f"工作区: {workspace.name} | 运行策略: {workspace.runtime_policy}\n"
            f"CC Sandbox 正在执行中，完成后结果将自动推送回本会话并触发你继续响应。\n"
            f"现在你可以直接回复用户，告知任务已在后台执行。"
        )
    except ValueError as e:
        logger.error(f"[cc_workspace] 启动 CC 任务失败: {e}")
        raise ValueError(f"启动 CC 任务失败: {e}") from e


@plugin.mount_sandbox_method(
    SandboxMethodType.BEHAVIOR,
    "取消本频道的 CC 委托任务",
    description=(
        "取消本频道正在后台运行的 CC 委托任务。"
        "同时尝试终止 CC 沙盒中对应的运行进程（若当前正在执行本频道任务）。"
        "若任务已完成，取消操作无效。"
    ),
)
async def cancel_cc_task(_ctx: schemas.AgentCtx) -> str:
    """Cancel the currently running CC Workspace delegation task for this channel.

    Returns:
        str: Cancellation result message.

    Example:
        ```python
        cancel_cc_task()
        ```
    """
    task_id = _ctx.from_chat_key
    if not task_api.is_running(_TASK_TYPE, task_id):
        raise ValueError("当前没有正在运行的 CC 委托任务。")

    # 先取消 NA 侧异步任务
    cancelled = await task_api.cancel(_TASK_TYPE, task_id)

    # 同时强制终止 CC 侧正在运行的进程（仅当 current_task 属于本频道时）
    # 注意 TOCTOU：检查和 kill 之间存在时间窗口，通过缩短窗口 + 二次确认降低误杀风险
    cc_cancelled = False
    workspace = await _ctx.get_bound_workspace()
    if workspace is not None and workspace.status == "active":
        try:
            client = CCSandboxClient(workspace)
            queue_status = await client.get_workspace_queue(workspace_id="default")
            current_task = queue_status.get("current_task")
            if current_task and current_task.get("source_chat_key") == task_id:
                # 二次确认：紧接 kill 前再次校验，缩小 TOCTOU 窗口
                queue_status_2 = await client.get_workspace_queue(workspace_id="default")
                current_task_2 = queue_status_2.get("current_task")
                if current_task_2 and current_task_2.get("source_chat_key") == task_id:
                    cc_cancelled = await client.force_cancel_current_task(workspace_id="default")
                    if cc_cancelled:
                        logger.info(f"[cc_workspace] 已强制终止 CC 侧进程，chat_key={task_id}")
                    else:
                        logger.warning(f"[cc_workspace] CC 侧进程终止失败，chat_key={task_id}")
                else:
                    logger.info(
                        f"[cc_workspace] CC 侧任务已切换（二次确认不匹配），跳过 kill，chat_key={task_id}"
                    )
        except Exception as e:
            logger.warning(f"[cc_workspace] 取消 CC 侧进程失败（不影响 NA 侧取消）: {e}")

    if cancelled:
        cc_hint = (
            "（CC 沙盒进程已同步终止）" if cc_cancelled
            else "（NA 侧已取消，CC 沙盒进程可能仍在后台运行，可用 `force_cancel_cc_workspace` 手动终止）"
        )
        logger.info(f"[cc_workspace] 已取消 CC 任务，chat_key={task_id}")
        return f"CC 委托任务已成功取消 {cc_hint}。"
    raise ValueError("取消任务失败，任务可能已结束。")


@plugin.mount_sandbox_method(
    SandboxMethodType.AGENT,
    "查询 CC 协作上下文",
    description=(
        "查询本频道当前 CC 任务的完整协作上下文，包含：当前任务执行状态及最新进度、"
        "上次委托给 CC 的原始任务摘要（防止长对话中忘记任务目标）、"
        "近期 NA↔CC 主消息通讯记录（最近 6 条）、CC 容器健康状态。"
        "适用于长时任务中途想了解 CC 工作情况，或 CC 回传结果后需要回忆原始委托内容时。"
    ),
)
async def get_cc_context(_ctx: schemas.AgentCtx) -> str:
    """Get the full CC collaboration context for this channel.

    Use this to recall what task was delegated to CC, understand CC's current work
    situation, and review recent communication history with CC.

    This is especially valuable in long sessions where the original delegation may
    have scrolled out of context — it brings together:
    - Current task execution state
    - The original task prompt that was delegated to CC
    - Recent message exchange with CC (last 6 entries)
    - CC container health check

    Returns:
        str: Comprehensive CC collaboration context.

    Example:
        ```python
        context = get_cc_context()
        ```
    """
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        raise ValueError("当前频道未绑定任何 CC Workspace。")

    chat_key = _ctx.from_chat_key
    task_id = chat_key

    # ── NA 侧任务状态 ─────────────────────────────────────────────────────────
    is_running = task_api.is_running(_TASK_TYPE, task_id)
    state = task_api.get_state(_TASK_TYPE, task_id)

    signal_map = {"progress": "进行中", "success": "已完成 ✓", "fail": "失败 ✗", "cancel": "已取消"}
    if is_running:
        task_status_line = "任务状态: 执行中 ▶"
        if state:
            latest_preview = state.message[:200] + ("..." if len(state.message) > 200 else "")
            task_status_line += f"\n最新进度: {latest_preview}"
    elif state is not None:
        task_status_line = f"任务状态: {signal_map.get(state.signal.value, state.signal.value)}"
        if state.message:
            latest_preview = state.message[:200] + ("..." if len(state.message) > 200 else "")
            task_status_line += f"\n最终消息摘要: {latest_preview}"
    else:
        task_status_line = "任务状态: 无活跃任务记录"

    # ── 原始委托任务摘要（从 plugin.store 读取） ──────────────────────────────
    stored_prompt = await plugin.store.get(chat_key=chat_key, store_key="last_cc_task_prompt") or ""
    prompt_section = ""
    if stored_prompt.strip():
        preview = stored_prompt[:500] + ("..." if len(stored_prompt) > 500 else "")
        prompt_section = f"\n[上次委托给 CC 的原始任务]\n{preview}\n"

    # ── CC 容器健康检查 ───────────────────────────────────────────────────────
    if workspace.status == "active":
        client = CCSandboxClient(workspace)
        try:
            healthy = await client.health_check()
            health_line = "CC 容器健康: ✓ 正常" if healthy else "CC 容器健康: ✗ 不可达（容器可能已异常退出）"
        except Exception:
            health_line = "CC 容器健康: ✗ 查询失败"
    else:
        health_line = f"CC 容器状态: {workspace.status}（未运行）"

    # ── 近期 NA↔CC 通讯日志（排除工具调用细节，聚焦主消息） ──────────────────
    comm_section = ""
    try:
        logs = await DBWorkspaceCommLog.filter(
            workspace_id=workspace.id,
            direction__in=["NA_TO_CC", "CC_TO_NA"],
            source_chat_key=chat_key,
        ).order_by("-create_time").limit(6).all()

        if logs:
            lines = []
            for log in reversed(logs):
                role = "NA→CC" if log.direction == "NA_TO_CC" else "CC→NA"
                content = log.content
                preview = content[:200] + ("..." if len(content) > 200 else "")
                time_str = log.create_time.strftime("%m-%d %H:%M")
                lines.append(f"[{time_str}] {role}: {preview}")
            comm_section = "\n[近期 NA↔CC 通讯记录（最近 6 条）]\n" + "\n---\n".join(lines) + "\n"
    except Exception:
        pass

    return (
        f"[CC Workspace 协作上下文]\n"
        f"工作区: {workspace.name}（ID: {workspace.id}）\n"
        f"{task_status_line}\n"
        f"{health_line}\n"
        f"{prompt_section}"
        f"{comm_section}"
    )


@plugin.mount_command(
    name="cc_help",
    description="查看 CC 协作插件的使用帮助",
    aliases=["cc_guide"],
    permission=_CC_COMMAND_PERMISSION,
    usage="cc_help",
    category="CC 协作",
)
async def cc_help_cmd(context: CommandExecutionContext) -> CommandResponse:
    """查看 CC 协作插件的常用命令和排查指引。"""
    agent_ctx = await _get_agent_ctx_from_command(context)
    workspace = await agent_ctx.get_bound_workspace()

    status_hint = (
        "当前频道尚未绑定 CC 工作区。请先在工作区页面绑定，或让 Agent 调用 `create_and_bind_workspace`。"
        if workspace is None
        else f"当前绑定工作区: {workspace.name}（状态: {_format_workspace_status(workspace.status)}）。"
    )

    message = (
        "[CC 协作帮助]\n"
        f"{status_hint}\n"
        "\n常用命令:\n"
        "- `cc_status` 查看状态\n"
        "- `cc_context` 查看上下文\n"
        "- `cc_recent [数量]` 查看最近记录\n"
        "- `cc_abort` 强制中止当前运行任务\n"
        "- `cc_reset_session` 重置 CC 会话\n"
        "- `cc_restart` 重启当前沙盒\n"
        "- `cc_stop` 停止当前沙盒\n"
    )
    return CmdCtl.success(
        message,
        data={
            "chat_key": context.chat_key,
            "workspace_bound": bool(workspace),
            "workspace_id": workspace.id if workspace else None,
        },
    )


@plugin.mount_command(
    name="cc_status",
    description="查看当前频道的 CC 协作状态摘要",
    aliases=[],
    permission=_CC_COMMAND_PERMISSION,
    usage="cc_status",
    category="CC 协作",
)
async def cc_status_cmd(context: CommandExecutionContext) -> CommandResponse:
    """查看当前频道绑定的 CC 工作区、容器健康和队列状态。"""
    agent_ctx = await _get_agent_ctx_from_command(context)
    message, data = await _build_cc_status_message(agent_ctx)
    return CmdCtl.success(message, data=data)


@plugin.mount_command(
    name="cc_context",
    description="查看当前频道的 CC 协作上下文",
    aliases=[],
    permission=_CC_COMMAND_PERMISSION,
    usage="cc_context",
    category="CC 协作",
)
async def cc_context_cmd(context: CommandExecutionContext) -> CommandResponse:
    """查看当前频道最近一次委托摘要、任务状态和近期通讯记录。"""
    agent_ctx = await _get_agent_ctx_from_command(context)
    message = await get_cc_context(agent_ctx)
    return CmdCtl.success(
        message,
        data={
            "chat_key": context.chat_key,
            "workspace_bound": bool(await agent_ctx.get_bound_workspace()),
        },
    )


@plugin.mount_command(
    name="cc_recent",
    description="查看当前频道最近的 CC 协作记录",
    aliases=["cc_log"],
    permission=_CC_COMMAND_PERMISSION,
    usage="cc_recent [数量]",
    category="CC 协作",
)
async def cc_recent_cmd(
    context: CommandExecutionContext,
    limit: Annotated[int, Arg("查看最近几条记录，范围 1-20", positional=True)] = 6,
) -> CommandResponse:
    """查看当前频道最近的 NA↔CC 协作主记录。"""
    limit = max(1, min(limit, 20))
    agent_ctx = await _get_agent_ctx_from_command(context)
    message, data = await _build_cc_recent_logs_message(agent_ctx, limit)
    return CmdCtl.success(message, data=data)


@plugin.mount_command(
    name="cc_abort",
    description="强制中止当前绑定工作区正在运行的 CC 任务",
    aliases=["cc_kill"],
    permission=_CC_COMMAND_PERMISSION,
    usage="cc_abort",
    category="CC 协作",
)
async def cc_abort_cmd(context: CommandExecutionContext) -> CommandResponse:
    """强制终止当前工作区正在执行的任务。"""
    agent_ctx = await _get_agent_ctx_from_command(context)
    message = await force_cancel_cc_workspace(agent_ctx)
    workspace = await agent_ctx.get_bound_workspace()
    return CmdCtl.success(
        message,
        data={
            "chat_key": context.chat_key,
            "workspace_id": workspace.id if workspace else None,
            "action": "force_cancel_current_task",
        },
    )


@plugin.mount_command(
    name="cc_reset_session",
    description="重置当前绑定工作区的 CC 会话并清理旧委托摘要缓存",
    aliases=["cc_reset"],
    permission=_CC_COMMAND_PERMISSION,
    usage="cc_reset_session",
    category="CC 协作",
)
async def cc_reset_session_cmd(context: CommandExecutionContext) -> CommandResponse:
    """重置当前工作区的 CC 会话。"""
    agent_ctx = await _get_agent_ctx_from_command(context)
    message = await reset_cc_session(agent_ctx)
    workspace = await agent_ctx.get_bound_workspace()
    return CmdCtl.success(
        message,
        data={
            "chat_key": context.chat_key,
            "workspace_id": workspace.id if workspace else None,
            "action": "reset_session",
        },
    )


@plugin.mount_command(
    name="cc_restart",
    description="重启当前绑定工作区的 CC 沙盒容器",
    aliases=[],
    permission=_CC_COMMAND_PERMISSION,
    usage="cc_restart",
    category="CC 协作",
)
async def cc_restart_cmd(context: CommandExecutionContext) -> CommandResponse:
    """重启当前工作区的 CC 沙盒。"""
    agent_ctx = await _get_agent_ctx_from_command(context)
    message = await restart_cc_sandbox(agent_ctx)
    workspace = await agent_ctx.get_bound_workspace()
    return CmdCtl.success(
        message,
        data={
            "chat_key": context.chat_key,
            "workspace_id": workspace.id if workspace else None,
            "action": "restart_sandbox",
        },
    )


@plugin.mount_command(
    name="cc_stop",
    description="停止当前绑定工作区的 CC 沙盒容器",
    aliases=[],
    permission=_CC_COMMAND_PERMISSION,
    usage="cc_stop",
    category="CC 协作",
)
async def cc_stop_cmd(context: CommandExecutionContext) -> CommandResponse:
    """停止当前工作区的 CC 沙盒。"""
    agent_ctx = await _get_agent_ctx_from_command(context)
    workspace = await _require_bound_workspace(agent_ctx)
    if workspace.status != "active":
        raise ValueError("当前工作区未运行，无需停止。")

    cancelled = await _maybe_force_cancel_running_workspace_task(workspace)
    await SandboxContainerManager.stop(workspace)
    await workspace.refresh_from_db()
    await _broadcast_system_comm_log(
        workspace.id,
        "[沙盒停止] CC Workspace 沙盒容器已停止。",
    )
    cancel_note = ""
    if cancelled["cancelled"]:
        cancel_note = (
            f"\n停止前已强制终止来自频道 `{cancelled['source_chat_key']}` 的运行中任务"
            f"（已运行 {cancelled['elapsed_seconds']}s）。"
        )
    return CmdCtl.success(
        f"CC 沙盒已停止。\n工作区: {workspace.name}（ID: {workspace.id}）\n当前状态: {_format_workspace_status(workspace.status)}{cancel_note}",
        data={
            "chat_key": context.chat_key,
            "workspace_id": workspace.id,
            "action": "stop_sandbox",
            "force_cancelled_task": cancelled["cancelled"],
        },
    )


@plugin.mount_sandbox_method(
    SandboxMethodType.BEHAVIOR,
    "强制取消 CC Workspace 当前运行任务",
    description=(
        "强制终止 CC Workspace 中当前正在运行的任务，无论该任务来自哪个频道。"
        "操作不可逆，被中断的任务结果将丢失，对应频道会收到取消通知。"
        "仅在工作区被长时间占用、需要抢占执行时使用。"
    ),
)
async def force_cancel_cc_workspace(_ctx: schemas.AgentCtx) -> str:
    """Force-cancel the currently running task in the bound CC Workspace.

    This cancels the running Claude Code process regardless of which channel submitted it.
    Use with caution — the interrupted task will receive an error and its result will be lost.

    Returns:
        str: Cancellation result message.

    Example:
        ```python
        result = force_cancel_cc_workspace()
        ```
    """
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        raise ValueError("当前频道未绑定任何 CC Workspace，无法取消任务。")

    client = CCSandboxClient(workspace)
    queue_status = await client.get_workspace_queue(workspace_id="default")
    current_task = queue_status.get("current_task")

    if not current_task:
        raise ValueError("当前工作区没有正在运行的任务。")

    src = current_task.get("source_chat_key", "未知频道")
    elapsed = current_task.get("elapsed_seconds", 0)

    cancelled = await client.force_cancel_current_task(workspace_id="default")
    if cancelled:
        logger.info(f"[cc_workspace] force_cancel_cc_workspace: 已取消来自 {src} 的任务（workspace={workspace.id}）")
        return (
            f"已强制取消来自频道 `{src}` 的任务（已运行 {elapsed:.0f}s）。\n"
            f"该任务的执行结果将会丢失，频道 `{src}` 的委托任务将收到取消通知。"
        )
    raise ValueError("取消失败，任务可能已经执行完毕。")


@plugin.mount_sandbox_method(
    SandboxMethodType.BEHAVIOR,
    "重置 CC Workspace 会话",
    description=(
        "重置当前绑定工作区的 CC 会话，清空 CC 保留的对话上下文。"
        "同时清理 NA 侧缓存的最近一次委托摘要，避免后续误把旧会话当作仍然有效。"
        "适用于上下文污染、状态异常、需要从干净会话重新开始时。"
    ),
)
async def reset_cc_session(_ctx: schemas.AgentCtx) -> str:
    """Reset the bound CC Workspace session and clear related prompt cache."""
    workspace = await _require_bound_workspace(_ctx)
    result = await _reset_workspace_session(workspace)
    return (
        f"CC Workspace 会话已重置。\n"
        f"工作区: {workspace.name}（ID: {workspace.id}）\n"
        f"已清理 {result['cleared_prompt_cache']} 条委托摘要缓存。"
    )


@plugin.mount_sandbox_method(
    SandboxMethodType.BEHAVIOR,
    "重启 CC 沙盒容器",
    description=(
        "重启当前绑定工作区的 CC 沙盒容器。"
        "若当前存在运行中的任务，会先尝试强制终止，随后执行容器重启。"
        "适用于沙盒 API 卡死、健康检查异常或需要快速恢复服务时。"
    ),
)
async def restart_cc_sandbox(_ctx: schemas.AgentCtx) -> str:
    """Restart the bound CC sandbox container."""
    workspace = await _require_bound_workspace(_ctx)
    if workspace.status != "active":
        raise ValueError("当前工作区未运行，无法重启沙盒。")

    cancelled = await _maybe_force_cancel_running_workspace_task(workspace)
    await SandboxContainerManager.restart(workspace)
    await workspace.refresh_from_db()
    await _broadcast_system_comm_log(
        workspace.id,
        "[沙盒重启] CC Workspace 沙盒容器已重启。",
    )
    cancel_note = ""
    if cancelled["cancelled"]:
        cancel_note = (
            f"\n重启前已强制终止来自频道 `{cancelled['source_chat_key']}` 的运行中任务"
            f"（已运行 {cancelled['elapsed_seconds']}s）。"
        )
    return (
        f"CC 沙盒已重启。\n"
        f"工作区: {workspace.name}（ID: {workspace.id}）\n"
        f"当前状态: {_format_workspace_status(workspace.status)}"
        f"{cancel_note}"
    )


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    "上传文件到 CC Workspace",
    description=(
        "将主沙盒中的文件复制到 CC Workspace 的 shared/ 目录，供 CC 沙盒直接通过文件系统访问。"
        "返回 CC 容器内可访问的绝对路径（如 /workspace/default/shared/report.pdf），"
        "可直接将此路径写入 delegate_to_cc 的 task_prompt 中告知 CC 文件位置。"
    ),
)
async def upload_file_to_cc(_ctx: schemas.AgentCtx, sandbox_file_path: str, dest_name: str = "") -> str:
    """Copy a file from the current sandbox into the bound CC Workspace shared directory.

    Returns the CC-side absolute path that CC can use to access the file.
    Use this path directly in your task_prompt when delegating tasks to CC.

    Args:
        sandbox_file_path (str): Path to the file inside the current sandbox
            (e.g., `/app/uploads/result.csv` or `/app/shared/report.pdf`).
        dest_name (str): Optional destination filename. If empty, the original filename is kept.

    Returns:
        str: The CC-side absolute path (e.g., `/workspace/default/shared/result.csv`).

    Raises:
        ValueError: If the file path is invalid, file doesn't exist, or workspace is not bound.

    Example:
        ```python
        cc_path = upload_file_to_cc("/app/uploads/data.csv")
        # cc_path = "/workspace/default/shared/data.csv"
        # Use cc_path in delegate_to_cc task_prompt
        delegate_to_cc(f"请分析文件 {cc_path} 中的数据...")
        ```
    """
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        raise ValueError("当前频道未绑定任何 CC Workspace，无法上传文件。请先绑定工作区。")

    try:
        host_path = _ctx.fs.get_file(sandbox_file_path)
    except Exception as e:
        raise ValueError(
            f"无法解析文件路径 '{sandbox_file_path}': {e}\n"
            f"请确保路径是有效的沙盒路径（如 /app/uploads/xxx 或 /app/shared/xxx）。"
        ) from e

    if not host_path.exists():
        raise ValueError(f"文件不存在: {sandbox_file_path}")

    if not host_path.is_file():
        raise ValueError(f"路径不是文件: {sandbox_file_path}")

    ws_shared_dir = WorkspaceService.get_workspace_dir(workspace.id) / "default" / "shared"
    ws_shared_dir.mkdir(parents=True, exist_ok=True)

    target_name = dest_name.strip() if dest_name.strip() else host_path.name
    # 安全处理：强制取纯文件名，防止路径穿越（如 ../../etc/passwd）
    target_name = Path(target_name).name
    if not target_name:
        raise ValueError("目标文件名无效")
    target_path = ws_shared_dir / target_name

    try:
        shutil.copy2(str(host_path), str(target_path))
    except Exception as e:
        logger.error(f"[cc_workspace] upload_file_to_cc 失败: {e}")
        raise ValueError(f"文件复制失败: {e}") from e

    cc_path = f"/workspace/default/shared/{target_name}"
    logger.info(f"[cc_workspace] upload_file_to_cc: {host_path} → {target_path} (cc_path={cc_path})")
    return cc_path


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    "从 CC Workspace 下载文件",
    description=(
        "从 CC Workspace 工作区下载文件到主沙盒共享目录，返回沙盒内可访问的文件路径。"
        "支持绝对路径（如 /workspace/default/shared/report.pdf）、相对路径（如 shared/report.pdf）"
        "或纯文件名（如 report.pdf，将在 shared/ 目录中查找）。"
        "适用于 CC 生成了结果文件需要在主沙盒中进一步处理或发送给用户的场景。"
    ),
)
async def download_file_from_cc(_ctx: schemas.AgentCtx, cc_file_path: str, dest_name: str = "") -> str:
    """Download a file from anywhere in the CC Workspace into the current sandbox's shared directory.

    Supports three path formats:
    - Absolute path: `/workspace/default/shared/report.pdf`
    - Relative path: `shared/report.pdf` (relative to `/workspace/default/`)
    - Filename only: `report.pdf` (searched in `shared/` directory)

    Args:
        cc_file_path (str): Path to the file inside the CC Workspace.
        dest_name (str): Optional destination filename. If empty, the original filename is kept.

    Returns:
        str: Sandbox-accessible path of the downloaded file (e.g., `/app/shared/report.pdf`).

    Raises:
        ValueError: If the workspace is not bound, the file doesn't exist, or the path is invalid.

    Example:
        ```python
        file_path = download_file_from_cc("shared/summary.json")  # file_path = "/app/shared/summary.json"
        send_msg_file(file_path)  # Send the file to the chat
        ```
    """
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        raise ValueError("当前频道未绑定任何 CC Workspace，无法下载文件。请先绑定工作区。")

    ws_root = WorkspaceService.get_workspace_dir(workspace.id) / "default"
    cc_path = cc_file_path.strip()

    if cc_path.startswith("/workspace/default/"):
        rel = cc_path[len("/workspace/default/"):]
        src_path = (ws_root / rel).resolve()
    elif cc_path.startswith("/workspace/"):
        rel = cc_path[len("/workspace/"):]
        src_path = (WorkspaceService.get_workspace_dir(workspace.id) / rel).resolve()
    elif "/" in cc_path or cc_path.startswith("./"):
        src_path = (ws_root / cc_path).resolve()
    else:
        src_path = (ws_root / "shared" / cc_path).resolve()

    # 安全检查：路径 resolve 后必须在 workspace 目录内
    ws_base = WorkspaceService.get_workspace_dir(workspace.id).resolve()
    try:
        src_path.relative_to(ws_base)
    except ValueError as e:
        raise ValueError(f"非法路径（路径穿越）: {cc_file_path}") from e

    if not src_path.exists():
        raise ValueError(
            f"CC Workspace 中文件不存在: {cc_file_path}\n"
            f"请检查路径是否正确。支持的格式：绝对路径 /workspace/default/...、"
            f"相对路径 shared/...、或纯文件名（在 shared/ 中查找）。"
        )

    if not src_path.is_file():
        raise ValueError(f"路径不是文件: {cc_file_path}")

    shared_dir: Path = _ctx.fs.shared_path
    shared_dir.mkdir(parents=True, exist_ok=True)

    target_name = dest_name.strip() if dest_name.strip() else src_path.name
    target_host_path = shared_dir / target_name

    try:
        shutil.copy2(str(src_path), str(target_host_path))
    except Exception as e:
        logger.error(f"[cc_workspace] download_file_from_cc 失败: {e}")
        raise ValueError(f"文件复制失败: {e}") from e

    logger.info(f"[cc_workspace] download_file_from_cc: {src_path} → {target_host_path}")
    sandbox_path = _ctx.fs.forward_file(target_host_path)
    return str(sandbox_path)


# ---------------------------------------------------------------------------
# 动态方法可见性控制（三态）
# ---------------------------------------------------------------------------


@plugin.mount_collect_methods()
async def _collect_cc_methods(ctx: schemas.AgentCtx) -> List:
    """根据当前频道的工作区状态，动态决定哪些 CC 方法对 NA 可见。

    状态1 - 未绑定工作区：
      - ALLOW_AUTO_CREATE_WORKSPACE=True  → 展示 create_and_bind_workspace
      - ALLOW_AUTO_CREATE_WORKSPACE=False → 返回空列表（AI 无法创建）
    状态2 - 已绑定但沙盒未运行：
      - ALLOW_AUTO_CREATE_WORKSPACE=True  → 展示 start_cc_sandbox
      - ALLOW_AUTO_CREATE_WORKSPACE=False → 返回空列表（AI 无法启动）
    状态3 - 沙盒正常运行：展示所有工作方法，隐藏创建/启动方法
    """
    workspace = await ctx.get_bound_workspace()

    # 状态1：未绑定工作区
    if workspace is None:
        if cc_config.ALLOW_AUTO_CREATE_WORKSPACE:
            return [create_and_bind_workspace]
        return []

    # 状态2：有工作区但沙盒未运行
    if workspace.status != "active":
        if cc_config.ALLOW_AUTO_CREATE_WORKSPACE:
            return [start_cc_sandbox]
        return []

    # 状态3：沙盒正常运行
    return [
        delegate_to_cc,
        cancel_cc_task,
        get_cc_context,
        force_cancel_cc_workspace,
        reset_cc_session,
        restart_cc_sandbox,
        upload_file_to_cc,
        download_file_from_cc,
    ]
