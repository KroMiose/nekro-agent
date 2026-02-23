"""CC 工作区协作插件 — 主逻辑

提供以下能力：
- **prompt 注入**：在主 Agent 系统提示词中注入当前频道绑定的 CC Workspace 状态
- **delegate_to_cc**（TOOL 类型）：异步委托任务给 CC Workspace 执行，完成后自动将结果推送回主 Agent
- **cancel_cc_task**（TOOL 类型）：取消正在后台运行的 CC 委托任务
- **get_cc_task_status**（TOOL 类型）：查询当前频道 CC 委托任务的执行进度
- **get_cc_status**（TOOL 类型）：查询 CC Sandbox 工作区实时状态
- **upload_file_to_cc**（TOOL 类型）：将主沙盒文件上传/共享至 CC Workspace 数据目录
- **download_file_from_cc**（TOOL 类型）：将 CC Workspace 数据目录中的文件引入主沙盒
"""

import asyncio
import shutil
from pathlib import Path
from typing import AsyncGenerator

from nekro_agent.api import schemas
from nekro_agent.api.plugin import SandboxMethodType
from nekro_agent.core.logger import logger
from nekro_agent.services.message_service import message_service
from nekro_agent.services.plugin.task import AsyncTaskHandle, TaskCtl
from nekro_agent.services.plugin.task import task as task_api
from nekro_agent.services.workspace.client import CCSandboxClient, CCSandboxError
from nekro_agent.services.workspace.manager import WorkspaceService

from .plugin import plugin

_TASK_TYPE = "cc_delegate"


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
    from nekro_agent.models.db_workspace import DBWorkspace

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

    # 在任务 prompt 前注入来源频道标记，供 CC 侧记忆系统区分多频道背景
    enriched_prompt = f"[任务来源频道: {handle.task_id}]\n\n{task_prompt}"

    # 持久化 NA_TO_CC 日志并广播（失败不阻断主流程）
    try:
        from nekro_agent.models.db_workspace_comm_log import DBWorkspaceCommLog
        from nekro_agent.services.workspace import comm_broadcast

        _na_log = await DBWorkspaceCommLog.create(
            workspace_id=workspace_id,
            direction="NA_TO_CC",
            source_chat_key=handle.task_id,
            content=enriched_prompt,
            task_id=f"cc_delegate:{handle.task_id}",
        )
        await comm_broadcast.publish(workspace_id, {
            "id": _na_log.id,
            "workspace_id": _na_log.workspace_id,
            "direction": _na_log.direction,
            "source_chat_key": _na_log.source_chat_key,
            "content": _na_log.content,
            "is_streaming": _na_log.is_streaming,
            "task_id": _na_log.task_id,
            "create_time": _na_log.create_time.isoformat(),
        })
    except Exception:
        pass

    try:
        yield TaskCtl.report_progress("CC Sandbox 任务已开始执行...", percent=0)

        async def _on_queued(event: dict) -> None:
            current = event.get("current_task") or {}
            src = current.get("source_chat_key", "未知频道")
            elapsed = current.get("elapsed_seconds", 0)
            pos = event.get("position", "?")
            _queued_messages.append(
                f"CC 工作区被占用（来源: {src}，已运行 {elapsed:.0f}s），排队第 {pos} 位..."
            )

        _env_vars = {
            item["key"]: item["value"]
            for item in (workspace.metadata or {}).get("env_vars", [])
            if item.get("key") and item.get("value")
        }
        async for item in client.stream_message(enriched_prompt, source_chat_key=handle.task_id, on_queued=_on_queued, env_vars=_env_vars or None):
            if handle.is_cancelled:
                yield TaskCtl.cancel("任务被用户取消")
                return
            # 检查并 flush 排队消息
            while _queued_messages:
                msg = _queued_messages.pop(0)
                yield TaskCtl.report_progress(msg, percent=0)

            if isinstance(item, dict):
                # tool_call / tool_result 事件 — 写入通讯日志并广播（失败不阻断）
                item_type = item.get("type")
                if item_type in ("tool_call", "tool_result"):
                    try:
                        import json as _json
                        from nekro_agent.models.db_workspace_comm_log import DBWorkspaceCommLog
                        from nekro_agent.services.workspace import comm_broadcast

                        direction = "TOOL_CALL" if item_type == "tool_call" else "TOOL_RESULT"
                        _tool_log = await DBWorkspaceCommLog.create(
                            workspace_id=workspace_id,
                            direction=direction,
                            source_chat_key=handle.task_id,
                            content=_json.dumps(item, ensure_ascii=False),
                            task_id=f"cc_delegate:{handle.task_id}",
                        )
                        await comm_broadcast.publish(workspace_id, {
                            "id": _tool_log.id,
                            "workspace_id": _tool_log.workspace_id,
                            "direction": _tool_log.direction,
                            "source_chat_key": _tool_log.source_chat_key,
                            "content": _tool_log.content,
                            "is_streaming": _tool_log.is_streaming,
                            "task_id": _tool_log.task_id,
                            "create_time": _tool_log.create_time.isoformat(),
                        })
                    except Exception:
                        pass
            else:
                chunks.append(item)
                chunk_count += 1
                # 每 20 个 chunk 汇报一次进度，避免过于频繁
                if chunk_count % 20 == 0:
                    yield TaskCtl.report_progress(f"执行中（已收到 {chunk_count} 个数据块）", percent=50)

        full_result = "".join(chunks)

        # 持久化 CC_TO_NA 日志并广播（失败不阻断主流程）
        try:
            from nekro_agent.models.db_workspace_comm_log import DBWorkspaceCommLog
            from nekro_agent.services.workspace import comm_broadcast

            _cc_log = await DBWorkspaceCommLog.create(
                workspace_id=workspace_id,
                direction="CC_TO_NA",
                source_chat_key=handle.task_id,
                content=full_result,
                is_streaming=True,
                task_id=f"cc_delegate:{handle.task_id}",
            )
            await comm_broadcast.publish(workspace_id, {
                "id": _cc_log.id,
                "workspace_id": _cc_log.workspace_id,
                "direction": _cc_log.direction,
                "source_chat_key": _cc_log.source_chat_key,
                "content": _cc_log.content,
                "is_streaming": _cc_log.is_streaming,
                "task_id": _cc_log.task_id,
                "create_time": _cc_log.create_time.isoformat(),
            })
        except Exception:
            pass

        # 检测未登录状态
        if "not logged in" in full_result.lower() or "/login" in full_result.lower():
            logger.warning(f"[cc_workspace] CC Sandbox 未认证，workspace={workspace_id}")
            yield TaskCtl.fail(
                "CC Sandbox 未认证。请在工作区「配置」页面关联有效的 CC 模型预设（需包含 auth_token），然后重建容器使配置生效。"
            )
            return

        if not full_result.strip():
            yield TaskCtl.fail("CC Sandbox 返回了空响应")
            return

        logger.info(f"[cc_workspace] cc_delegate 完成，workspace={workspace_id}，响应长度={len(full_result)}")
        yield TaskCtl.success(f"[CC Workspace 执行结果]\n{full_result}", data=full_result)

    except CCSandboxError as e:
        logger.error(f"[cc_workspace] cc_delegate 流式执行失败: {e}")
        yield TaskCtl.fail(f"CC Sandbox 执行失败: {e}")
    except Exception as e:
        logger.exception(f"[cc_workspace] cc_delegate 异常: {e}")
        yield TaskCtl.fail(f"CC Workspace 发生意外错误: {e}")


# ---------------------------------------------------------------------------
# Prompt 注入
# ---------------------------------------------------------------------------


@plugin.mount_prompt_inject_method("cc_workspace_status")
async def cc_workspace_status(_ctx: schemas.AgentCtx) -> str:
    """向主 Agent 系统提示词注入当前频道绑定的 CC Workspace 信息"""
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        return ""

    # 工作区未运行时只注入基础信息，不尝试连接 CC
    if workspace.status != "active":
        return (
            f"[CC Workspace]\n"
            f"当前频道已绑定 CC Workspace: {workspace.name}（ID: {workspace.id}）\n"
            f"状态: {workspace.status}（未运行，CC 能力暂不可用）\n"
        )

    client = CCSandboxClient(workspace)

    # CC 应用状态：仅在异常时提示
    status_info = await client.get_sandbox_status()
    ws_status = status_info.get("status", "")
    _NORMAL_CC_STATES = {"idle", "busy", "running", "ready", ""}
    status_hint = "" if ws_status in _NORMAL_CC_STATES else f"CC 应用状态异常: {ws_status}\n"

    # 能力摘要（skills + MCP）
    capability_hint = WorkspaceService.get_capability_summary(workspace)

    # 记忆摘要（_na_context.md），附带更新时间
    memory_hint = ""
    try:
        na_context, updated = WorkspaceService.read_na_context(workspace.id)
        if na_context.strip():
            time_str = f"（更新于: {updated}）" if updated else ""
            memory_hint = f"\n[CC 工作区记忆摘要]{time_str}\n{na_context}\n"
    except Exception:
        pass

    # 合并任务/队列状态：NA 侧 AsyncTask + CC 侧队列，给出统一逻辑视图
    task_hint = ""
    is_running = bool(_ctx.from_chat_key and task_api.is_running(_TASK_TYPE, _ctx.from_chat_key))
    try:
        queue_status = await client.get_workspace_queue(workspace_id="default")
        current_task = queue_status.get("current_task")
        queue_len = queue_status.get("queue_length", 0)
        queue_suffix = f"，当前等待队列: {queue_len} 个任务" if queue_len > 0 else ""

        if current_task:
            src = current_task.get("source_chat_key", "")
            elapsed = current_task.get("elapsed_seconds", 0)
            preview = current_task.get("prompt_preview", "")
            preview_str = preview[:60] + ("..." if len(preview) > 60 else "")
            src_display = (src.split("_")[0] + " 频道") if "_" in src else (src or "未知频道")

            if is_running and src == _ctx.from_chat_key:
                # 本频道任务正在 CC 执行
                task_hint = (
                    f"\n[CC 委托任务执行中] 已运行 {elapsed:.0f}s\n"
                    f"任务: {preview_str}\n"
                    f"完成后结果将自动推回本会话。可通过 `cancel_cc_task` 取消，"
                    f"或通过 `get_cc_task_status` 查询进度。\n"
                )
            elif is_running:
                # 本频道任务在排队，工作区被其他频道占用
                task_hint = (
                    f"\n[CC 委托任务排队中] 工作区当前由 {src_display} 占用（已运行 {elapsed:.0f}s）{queue_suffix}\n"
                    f"本频道任务正在等待执行。可通过 `cancel_cc_task` 取消等待，"
                    f"或通过 `force_cancel_cc_workspace` 强制抢占。\n"
                )
            else:
                # 本频道无任务，工作区被其他频道占用
                task_hint = (
                    f"\n[CC 工作区占用中] 当前由 {src_display} 占用（已运行 {elapsed:.0f}s）{queue_suffix}\n"
                    f"任务: {preview_str}\n"
                    f"委托新任务将自动排队。如需强制取消，可调用 `force_cancel_cc_workspace`。\n"
                )
        elif is_running:
            # NA 任务在跑但 CC 队列为空（任务刚提交/CC 侧尚未入队）
            task_hint = (
                "\n[CC 委托任务已提交，等待 CC 侧接收...]\n"
                "完成后结果将自动推回本会话。可通过 `get_cc_task_status` 查询进度，或通过 `cancel_cc_task` 取消。\n"
            )
    except Exception:
        # 无法查询 CC 队列时，仅依赖 NA 侧状态
        if is_running:
            task_hint = (
                "\n[当前有 CC 委托任务正在后台执行中，完成后结果将自动回传。"
                "可通过 `get_cc_task_status` 查询进度，或通过 `cancel_cc_task` 取消。]\n"
            )

    return (
        f"[CC Workspace]\n"
        f"当前频道已绑定 CC Workspace: {workspace.name}（ID: {workspace.id}）\n"
        f"运行策略: {workspace.runtime_policy}\n"
        f"{status_hint}"
        f"{capability_hint}"
        f"{memory_hint}"
        f"{task_hint}"
        f"可通过 `delegate_to_cc` 将复杂的编程/工具任务**异步**委托给 CC Sandbox 后台执行（完成后自动回传），"
        f"通过 `upload_file_to_cc` / `download_file_from_cc` 与 CC Workspace 传递文件，"
        f"通过 `get_cc_status` 查询工作区详细状态。\n"
    )


# ---------------------------------------------------------------------------
# Sandbox 方法
# ---------------------------------------------------------------------------


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "异步委托任务给 CC Workspace（claude-code 沙盒）后台执行")
async def delegate_to_cc(_ctx: schemas.AgentCtx, task_prompt: str) -> str:
    """Delegate a task to the bound CC Workspace (claude-code sandbox) asynchronously.

    The task runs in the background via streaming. When complete, the result will be
    automatically pushed back to this conversation as a system message, and you will be
    triggered to respond with the CC result.

    **When to use**: Long coding tasks, shell commands, multi-step file processing, anything
    requiring a persistent tool environment.

    **Note**: Only one CC task can run per channel at a time. Use `cancel_cc_task` to
    cancel the current task before starting a new one.

    Args:
        task_prompt (str): Detailed description of the task for CC Sandbox to perform. Be as
            specific as possible — include expected inputs, outputs, file paths, and constraints.

    Returns:
        str: Confirmation that the task has been started asynchronously (NOT the final result —
             the result will come back automatically when execution is complete).

    Example:
        ```python
        delegate_to_cc(
            "请读取 ./data/report.csv，计算每列的均值，并将结果保存到 ./data/summary.json"
        )
        ```
    """
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        return "[CC Workspace] 当前频道未绑定任何 CC Workspace，无法委托任务。请先在工作区管理页面绑定频道。"

    if workspace.status != "active":
        return (
            f"[CC Workspace] 工作区 '{workspace.name}' 当前状态为 {workspace.status}，"
            f"无法接受任务。请先启动工作区后重试。"
        )

    chat_key = _ctx.from_chat_key
    task_id = chat_key  # 每个频道同时只允许一个 CC 任务

    if task_api.is_running(_TASK_TYPE, task_id):
        return (
            f"[CC Workspace] 当前频道已有 CC 任务在后台执行中。\n"
            f"请等待当前任务完成（完成后结果将自动推回本会话），"
            f"或使用 `cancel_cc_task` 取消后再委托新任务。"
        )

    # on_terminal 为同步回调，在任务终态时将结果异步推送给主 Agent
    def on_terminal(ctl: TaskCtl) -> None:
        if ctl.signal.value == "success":
            notify_msg = ctl.message  # "[CC Workspace 执行结果]\n..."
        elif ctl.signal.value == "fail":
            notify_msg = f"[CC Workspace] CC 任务执行失败: {ctl.message}"
        elif ctl.signal.value == "cancel":
            notify_msg = f"[CC Workspace] CC 任务已被取消: {ctl.message}"
        else:
            return

        asyncio.create_task(
            message_service.push_system_message(
                chat_key=chat_key,
                agent_messages=notify_msg,
                trigger_agent=True,
            )
        )

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
        return f"[CC Workspace] 启动任务失败: {e}"


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "取消当前频道正在后台执行的 CC Workspace 委托任务")
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
        return "[CC Workspace] 当前没有正在运行的 CC 委托任务。"

    cancelled = await task_api.cancel(_TASK_TYPE, task_id)
    if cancelled:
        logger.info(f"[cc_workspace] 已取消 CC 任务，chat_key={task_id}")
        return "[CC Workspace] CC 委托任务已成功取消。"
    return "[CC Workspace] 取消任务失败，任务可能已结束。"


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "查询当前频道 CC Workspace 委托任务的执行状态")
async def get_cc_task_status(_ctx: schemas.AgentCtx) -> str:
    """Get the execution status of the CC Workspace delegation task for this channel.

    Returns:
        str: Task status report including signal, progress, and latest message.

    Example:
        ```python
        status = get_cc_task_status()
        ```
    """
    task_id = _ctx.from_chat_key
    is_running = task_api.is_running(_TASK_TYPE, task_id)
    state = task_api.get_state(_TASK_TYPE, task_id)

    if not is_running and state is None:
        return "[CC Workspace] 当前频道没有 CC 委托任务记录。"

    status_label = "运行中" if is_running else "已结束"
    if state:
        signal_map = {"progress": "执行中", "success": "已完成", "fail": "失败", "cancel": "已取消"}
        signal_label = signal_map.get(state.signal.value, state.signal.value)
        preview = state.message[:300] + "..." if len(state.message) > 300 else state.message
        return (
            f"[CC Workspace 任务状态]\n"
            f"状态: {status_label}（{signal_label}）\n"
            f"最新进度: {preview}"
        )
    return f"[CC Workspace 任务状态]\n状态: {status_label}"


@plugin.mount_sandbox_method(SandboxMethodType.AGENT, "查询 CC Workspace 实时状态")
async def get_cc_status(_ctx: schemas.AgentCtx) -> str:
    """Get the real-time status of the bound CC Workspace.

    Returns workspace name, container status, available tools, and last heartbeat time.

    Returns:
        str: A formatted status report of the CC Workspace.

    Example:
        ```python
        status = get_cc_status()
        print(status)
        ```
    """
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        return "[CC Workspace] 当前频道未绑定任何 CC Workspace。"

    client = CCSandboxClient(workspace)
    healthy = await client.health_check()
    status_info = await client.get_sandbox_status()
    tools_list: list[str] = []
    try:
        tools_list = await client.get_tools()
    except Exception:
        pass

    tools_str = ", ".join(tools_list) if tools_list else "（暂无）"
    ws_status = status_info.get("status", workspace.status)
    heartbeat = str(workspace.last_heartbeat) if workspace.last_heartbeat else "N/A"

    return (
        f"[CC Workspace 状态]\n"
        f"工作区: {workspace.name}（ID: {workspace.id}）\n"
        f"容器状态: {workspace.status} | CC 应用状态: {ws_status}\n"
        f"健康检查: {'✓ 正常' if healthy else '✗ 不可达'}\n"
        f"运行策略: {workspace.runtime_policy}\n"
        f"可用工具: {tools_str}\n"
        f"最近心跳: {heartbeat}\n"
        f"最近错误: {workspace.last_error or '无'}"
    )


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "强制取消 CC Workspace 中当前正在运行的任务（来自任意频道）")
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
        return "[CC Workspace] 当前频道未绑定任何 CC Workspace，无法取消任务。"

    client = CCSandboxClient(workspace)
    queue_status = await client.get_workspace_queue(workspace_id="default")
    current_task = queue_status.get("current_task")

    if not current_task:
        return "[CC Workspace] 当前工作区没有正在运行的任务。"

    src = current_task.get("source_chat_key", "未知频道")
    elapsed = current_task.get("elapsed_seconds", 0)

    cancelled = await client.force_cancel_current_task(workspace_id="default")
    if cancelled:
        logger.info(f"[cc_workspace] force_cancel_cc_workspace: 已取消来自 {src} 的任务（workspace={workspace.id}）")
        return (
            f"[CC Workspace] 已强制取消来自频道 `{src}` 的任务（已运行 {elapsed:.0f}s）。\n"
            f"该任务的执行结果将会丢失，频道 `{src}` 的委托任务将收到取消通知。"
        )
    return "[CC Workspace] 取消失败，任务可能已经执行完毕。"


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "将主沙盒文件上传/共享至 CC Workspace 数据目录")
async def upload_file_to_cc(_ctx: schemas.AgentCtx, sandbox_file_path: str, dest_name: str = "") -> str:
    """Copy a file from the current sandbox into the bound CC Workspace data directory.

    The file will be placed in the CC Workspace's `data/` directory so that CC Sandbox
    can access it directly via its own file system.

    Args:
        sandbox_file_path (str): Path to the file inside the current sandbox
            (e.g., `./output/result.csv` or `/home/user/shared/report.pdf`).
        dest_name (str): Optional destination filename. If empty, the original filename is kept.

    Returns:
        str: Success message with the path CC Sandbox can use to access the file,
             or an error message.

    Example:
        ```python
        upload_file_to_cc("./data/result.csv", "result.csv")
        ```
    """
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        return "[CC Workspace] 当前频道未绑定任何 CC Workspace，无法上传文件。"

    try:
        host_path = _ctx.fs.get_file(sandbox_file_path)
    except Exception as e:
        return f"[CC Workspace] 无法解析文件路径 '{sandbox_file_path}': {e}"

    if not host_path.exists():
        return f"[CC Workspace] 文件不存在: {sandbox_file_path}"

    if not host_path.is_file():
        return f"[CC Workspace] 路径不是文件: {sandbox_file_path}"

    ws_data_dir = WorkspaceService.get_workspace_dir(workspace.id) / "default" / "data"
    ws_data_dir.mkdir(parents=True, exist_ok=True)

    target_name = dest_name.strip() if dest_name.strip() else host_path.name
    target_path = ws_data_dir / target_name

    try:
        shutil.copy2(str(host_path), str(target_path))
        logger.info(f"[cc_workspace] upload_file_to_cc: {host_path} → {target_path}")
        return (
            f"[CC Workspace] 文件已上传至工作区数据目录。\n"
            f"CC Sandbox 可通过绝对路径访问: /workspace/default/data/{target_name}"
        )
    except Exception as e:
        logger.error(f"[cc_workspace] upload_file_to_cc 失败: {e}")
        return f"[CC Workspace] 文件上传失败: {e}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "从 CC Workspace 数据目录下载文件到主沙盒共享目录")
async def download_file_from_cc(_ctx: schemas.AgentCtx, cc_data_filename: str, dest_name: str = "") -> str:
    """Copy a file from the CC Workspace data directory into the current sandbox's shared directory.

    After calling this, you can access the file in the sandbox at the returned path.

    Args:
        cc_data_filename (str): Filename (or relative path) inside the CC Workspace `data/` directory.
            For example: `"result.json"` or `"output/report.pdf"`.
        dest_name (str): Optional destination filename in the sandbox shared directory.
            If empty, the original filename is kept.

    Returns:
        str: Sandbox-accessible path of the downloaded file, or an error message.

    Example:
        ```python
        path = download_file_from_cc("summary.json")
        # Now use path to read the file in the sandbox
        ```
    """
    workspace = await _ctx.get_bound_workspace()
    if workspace is None:
        return "[CC Workspace] 当前频道未绑定任何 CC Workspace，无法下载文件。"

    ws_data_dir = WorkspaceService.get_workspace_dir(workspace.id) / "default" / "data"
    src_path = (ws_data_dir / cc_data_filename).resolve()

    # 安全检查：不允许路径穿越
    try:
        src_path.relative_to(ws_data_dir.resolve())
    except ValueError:
        return f"[CC Workspace] 非法路径: {cc_data_filename}"

    if not src_path.exists():
        return f"[CC Workspace] CC Workspace 数据目录中不存在文件: {cc_data_filename}"

    if not src_path.is_file():
        return f"[CC Workspace] 路径不是文件: {cc_data_filename}"

    shared_dir: Path = _ctx.fs.shared_path
    shared_dir.mkdir(parents=True, exist_ok=True)

    target_name = dest_name.strip() if dest_name.strip() else src_path.name
    target_host_path = shared_dir / target_name

    try:
        shutil.copy2(str(src_path), str(target_host_path))
        logger.info(f"[cc_workspace] download_file_from_cc: {src_path} → {target_host_path}")
        sandbox_path = _ctx.fs.forward_file(target_host_path)
        return str(sandbox_path)
    except Exception as e:
        logger.error(f"[cc_workspace] download_file_from_cc 失败: {e}")
        return f"[CC Workspace] 文件下载失败: {e}"
