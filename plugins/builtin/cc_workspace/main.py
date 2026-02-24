"""CC 工作区协作插件 — 主逻辑

提供以下能力：
- **prompt 注入**：在主 Agent 系统提示词中注入当前频道绑定的 CC Workspace 状态
- **create_and_bind_workspace**（AGENT 类型）：为当前频道创建 CC Workspace 并自动绑定
- **start_cc_sandbox**（AGENT 类型）：启动绑定工作区的 CC 沙盒容器
- **delegate_to_cc**（BEHAVIOR 类型）：异步委托任务给 CC Workspace 执行，完成后自动将结果推送回主 Agent
- **cancel_cc_task**（BEHAVIOR 类型）：取消正在后台运行的 CC 委托任务
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
import re
import secrets
import shutil
from pathlib import Path
from typing import AsyncGenerator, List

import aiodocker

from nekro_agent.api import schemas
from nekro_agent.api.plugin import SandboxMethodType
from nekro_agent.core.config import config as app_config
from nekro_agent.core.logger import logger
from nekro_agent.models.db_workspace import DBWorkspace
from nekro_agent.models.db_workspace_comm_log import DBWorkspaceCommLog
from nekro_agent.services.message_service import message_service
from nekro_agent.services.plugin.task import AsyncTaskHandle, TaskCtl
from nekro_agent.services.plugin.task import task as task_api
from nekro_agent.services.workspace import comm_broadcast
from nekro_agent.services.workspace.client import CCSandboxClient, CCSandboxError
from nekro_agent.services.workspace.container import SandboxContainerManager
from nekro_agent.services.workspace.manager import WorkspaceService

from .plugin import plugin

_TASK_TYPE = "cc_delegate"


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


# ---------------------------------------------------------------------------
# 文件内容风险扫描
# ---------------------------------------------------------------------------

# 敏感凭据正则集合
_SENSITIVE_PATTERNS: List[tuple] = [
    ("私钥/证书", re.compile(r"-----BEGIN\s(?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub Token", re.compile(r"\b(?:ghp|ghs|gho|ghu|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("通用 API Key 赋值", re.compile(
        r"""(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\s*[=:]\s*['"]?[A-Za-z0-9+/._\-]{20,}['"]?"""
    )),
    ("高熵 Bearer Token", re.compile(r"\bBearer\s+[A-Za-z0-9+/._\-]{30,}\b")),
]

_SCAN_SIZE_LIMIT = 512 * 1024  # 只扫描前 512 KB，避免大文件卡顿


def _scan_sensitive_content(content: str) -> List[str]:
    """扫描文本内容，返回命中的风险类型列表（去重）。"""
    hits: List[str] = []
    for label, pattern in _SENSITIVE_PATTERNS:
        if pattern.search(content):
            hits.append(label)
    return hits


# ---------------------------------------------------------------------------
# NA 重启后恢复 CC 待投递结果
# ---------------------------------------------------------------------------


async def recover_pending_cc_results() -> None:
    """NA 启动时扫描所有 active 工作区，取回 CC 在断线期间完成的任务结果。

    调用方：nekro_agent/__init__.py on_startup（在 init_plugins 之后）。

    恢复逻辑：
    1. 遍历所有状态为 active 的工作区
    2. 调用 CC sandbox GET /pending-results（消费语义，取回后自动删除）
    3. 对每条结果：写入 CC_TO_NA 通讯日志、广播到 SSE、推送系统消息并触发 NA Agent
    """
    try:
        active_workspaces = await DBWorkspace.filter(status="active")
    except Exception as e:
        logger.warning(f"[cc_workspace] 恢复检查：获取工作区列表失败: {e}")
        return

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
            source_chat_key: str = item.get("source_chat_key", "")
            result: str = item.get("result", "")
            result_id: str = item.get("id", "")

            if not source_chat_key or not result.strip():
                logger.debug(f"[cc_workspace] 跳过无效的待投递结果: id={result_id!r}")
                continue

            # 写入 CC_TO_NA 通讯日志
            try:
                cc_log = await DBWorkspaceCommLog.create(
                    workspace_id=workspace.id,
                    direction="CC_TO_NA",
                    source_chat_key=source_chat_key,
                    content=result,
                    is_streaming=False,
                    task_id=f"cc_delegate:{source_chat_key}",
                )
                await comm_broadcast.publish(workspace.id, {
                    "id": cc_log.id,
                    "workspace_id": cc_log.workspace_id,
                    "direction": cc_log.direction,
                    "source_chat_key": cc_log.source_chat_key,
                    "content": cc_log.content,
                    "is_streaming": cc_log.is_streaming,
                    "task_id": cc_log.task_id,
                    "create_time": cc_log.create_time.isoformat(),
                })
            except Exception as e:
                logger.warning(f"[cc_workspace] 恢复：写入通讯日志失败 (id={result_id!r}): {e}")

            # 推送系统消息并触发 NA Agent
            try:
                notify_msg = (
                    f"[CC Workspace 恢复结果] NA 服务重启前，CC 已完成一个委托任务，"
                    f"结果如下（来自工作区: {workspace.name}）：\n\n"
                    f"[CC Workspace 执行结果]\n{result}"
                )
                await message_service.push_system_message(
                    chat_key=source_chat_key,
                    agent_messages=notify_msg,
                    trigger_agent=True,
                )
                logger.info(
                    f"[cc_workspace] 恢复成功：已推送到 chat_key={source_chat_key!r}，"
                    f"workspace={workspace.id}，chars={len(result)}"
                )
            except Exception as e:
                logger.error(
                    f"[cc_workspace] 恢复：推送消息失败 (chat_key={source_chat_key!r}): {e}"
                )


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

    # 在任务 prompt 前注入来源频道标记，供 CC 侧记忆系统区分多频道背景
    enriched_prompt = f"[任务来源频道: {handle.task_id}]\n\n{task_prompt}"

    # 持久化 NA_TO_CC 日志并广播（失败不阻断主流程）
    try:
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
                        direction = "TOOL_CALL" if item_type == "tool_call" else "TOOL_RESULT"
                        _tool_log = await DBWorkspaceCommLog.create(
                            workspace_id=workspace_id,
                            direction=direction,
                            source_chat_key=handle.task_id,
                            content=json.dumps(item, ensure_ascii=False),
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

    # ── 状态1：未绑定工作区 ──────────────────────────────────────────────────
    if workspace is None:
        return (
            "[CC Workspace]\n"
            "当前频道未绑定任何 CC Workspace。\n"
            "CC Workspace 是一个独立的 Claude Code 沙盒，支持持久化执行代码、处理文件、运行命令和使用各种工具。\n"
            "可通过 `create_and_bind_workspace` 自动创建并绑定工作区到当前频道（绑定后需再调用 `start_cc_sandbox` 启动容器）。\n"
            "如果用户有特殊需求（如指定镜像、运行策略），建议引导用户到工作区管理页面手动创建后再绑定。\n"
        )

    # ── 状态2：已绑定工作区，但沙盒未运行 ──────────────────────────────────
    if workspace.status != "active":
        status_label = {
            "stopped": "已停止",
            "failed": "启动失败",
            "deleting": "删除中",
        }.get(workspace.status, workspace.status)
        last_error_hint = f"\n上次错误: {workspace.last_error}" if workspace.last_error else ""
        user_action_hint = (
            "上次错误可能需要用户介入处理（如镜像缺失、配置错误等），请告知用户查看工作区管理页面。"
            if workspace.last_error
            else "可通过 `start_cc_sandbox` 启动沙盒容器。"
        )
        return (
            f"[CC Workspace]\n"
            f"当前频道已绑定 CC Workspace: {workspace.name}（ID: {workspace.id}）\n"
            f"运行策略: {workspace.runtime_policy}\n"
            f"状态: {status_label}（沙盒未运行）{last_error_hint}\n"
            f"{user_action_hint}\n"
        )

    # ── 状态3：工作区正常运行 ────────────────────────────────────────────────

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
                    f"或通过 `get_cc_context` 查询完整上下文（含原始任务和通讯历史）。\n"
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
                "完成后结果将自动推回本会话。可通过 `get_cc_context` 查询完整协作上下文，或通过 `cancel_cc_task` 取消。\n"
            )
    except Exception:
        # 无法查询 CC 队列时，仅依赖 NA 侧状态
        if is_running:
            task_hint = (
                "\n[当前有 CC 委托任务正在后台执行中，完成后结果将自动回传。"
                "可通过 `get_cc_context` 查询完整协作上下文，或通过 `cancel_cc_task` 取消。]\n"
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
        f"通过 `get_cc_context` 查询工作区协作上下文（任务状态 + 原始任务 + 通讯历史）。\n"
        f"\n"
        f"[CC 协作注意事项]\n"
        f"- CC 是工作区的**第一手知识持有者**，你（NA）无法主动读取 CC 工作区的文件和代码，不了解工作区实际状态\n"
        f"- 委托任务时请描述**目标和背景**，而不是具体实现步骤——不要在任务中假设工作区存在特定文件路径、函数名或代码行\n"
        f"- 如果用户提到具体的文件/函数/路径，应以「用户提及，请自行核实」的方式传达，而非断言其存在\n"
        f"- CC 响应中若包含「[需要澄清]」问题，应将问题**转达给用户**后，再决定是否继续委托新任务\n"
        f"- 绝对不要根据对工作区的主观臆测，向 CC 下达精细化的代码修改指令（如'将第X行改为...'）\n"
    )


# ---------------------------------------------------------------------------
# Sandbox 方法
# ---------------------------------------------------------------------------


@plugin.mount_sandbox_method(
    SandboxMethodType.BEHAVIOR,
    "开启/关闭当前频道的 CC Workspace 自动创建权限",
    description=(
        "控制当前频道是否允许 NA 通过 create_and_bind_workspace 自动创建 CC Workspace。"
        "默认关闭，须由管理员手动开启。"
        "enable=True 开启自动创建，enable=False 关闭。"
    ),
)
async def toggle_cc_auto_workspace(_ctx: schemas.AgentCtx, enable: bool) -> str:
    """Enable or disable automatic CC Workspace creation for the current channel.

    This is an admin-level control. By default, NA cannot auto-create a workspace
    for a channel. An operator must explicitly enable this permission first.

    Args:
        enable (bool): True to allow auto-creation, False to disallow.

    Returns:
        str: Confirmation of the new permission state.

    Example:
        ```python
        toggle_cc_auto_workspace(True)   # 开启本频道自动创建权限
        toggle_cc_auto_workspace(False)  # 关闭
        ```
    """
    chat_key = _ctx.from_chat_key
    await plugin.store.set(chat_key=chat_key, store_key="enable_auto_workspace", value="true" if enable else "false")
    if enable:
        return (
            "[CC Workspace] 已开启当前频道的工作区自动创建权限。\n"
            "NA 现在可以通过 `create_and_bind_workspace` 为本频道自动创建并绑定工作区。"
        )
    return (
        "[CC Workspace] 已关闭当前频道的工作区自动创建权限。\n"
        "NA 将无法在本频道自动创建新工作区，现有绑定关系不受影响。"
    )


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

    # 频道级权限检查：需管理员提前通过 toggle_cc_auto_workspace 开启
    auto_ws_enabled = await plugin.store.get(chat_key=chat_key, store_key="enable_auto_workspace")
    if auto_ws_enabled != "true":
        return (
            "[CC Workspace] 当前频道尚未开启工作区自动创建权限。\n"
            "如需使用 CC Workspace，请管理员在本频道执行 `toggle_cc_auto_workspace(enable=True)` 开启后重试，"
            "或直接在工作区管理页面手动创建并绑定工作区。"
        )

    # 当前频道已绑定工作区时，不允许重复创建
    existing = await _ctx.get_bound_workspace()
    if existing is not None:
        return (
            f"[CC Workspace] 当前频道已绑定工作区 '{existing.name}'（ID: {existing.id}，状态: {existing.status}）。\n"
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
    except Exception as e:
        logger.error(f"[cc_workspace] 创建工作区失败: {e}")
        return f"[CC Workspace] 创建工作区失败：{e}"

    # 绑定到当前频道
    try:
        await WorkspaceService.bind_channel(ws, chat_key)
    except Exception as e:
        logger.error(f"[cc_workspace] 绑定工作区到频道失败: {e}")
        try:
            await ws.delete()
        except Exception:
            pass
        return f"[CC Workspace] 工作区创建成功但绑定到当前频道失败：{e}"

    logger.info(f"[cc_workspace] 已创建并绑定工作区: {final_name}（ID: {ws.id}），chat_key={chat_key}")
    return (
        f"[CC Workspace] 工作区已创建并绑定到当前频道。\n"
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
        return "[CC Workspace] 当前频道未绑定工作区，请先调用 `create_and_bind_workspace` 创建工作区。"

    if workspace.status == "active":
        return (
            f"[CC Workspace] 工作区 '{workspace.name}' 的沙盒已在运行中，无需重复启动。\n"
            f"可通过 `delegate_to_cc` 直接委托任务。"
        )

    # 确定镜像名称并检查本地是否存在
    image_name = workspace.sandbox_image or app_config.CC_SANDBOX_IMAGE
    image_tag = workspace.sandbox_version or app_config.CC_SANDBOX_IMAGE_TAG
    image = f"{image_name}:{image_tag}"

    image_exists = await _check_sandbox_image_exists(image)
    if not image_exists:
        return (
            f"[CC Workspace] 本地未找到沙盒镜像 `{image}`，无法启动容器。\n"
            f"请通知用户在宿主机（或 NA 容器内）执行以下命令拉取镜像：\n"
            f"```\ndocker pull {image}\n```\n"
            f"拉取完成后，重新调用 `start_cc_sandbox` 即可启动。"
        )

    # 启动容器（等待健康检查通过）
    try:
        await SandboxContainerManager.create_and_start(workspace)
        logger.info(f"[cc_workspace] 沙盒已启动: workspace={workspace.name}（ID: {workspace.id}）")
        return (
            f"[CC Workspace] 沙盒已成功启动！\n"
            f"工作区: {workspace.name}（ID: {workspace.id}）\n"
            f"现在可以通过 `delegate_to_cc` 向 CC Workspace 委托编程任务了。"
        )
    except RuntimeError as e:
        logger.error(f"[cc_workspace] 启动沙盒失败: {e}")
        return (
            f"[CC Workspace] 沙盒启动失败：{e}\n"
            f"可能原因：容器健康检查超时，或镜像/配置异常。\n"
            f"建议告知用户检查 Docker 日志，或在工作区管理页面查看详细错误信息。"
        )
    except Exception as e:
        logger.error(f"[cc_workspace] 启动沙盒异常: {e}")
        return f"[CC Workspace] 启动沙盒时发生意外错误：{e}"


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

    **IMPORTANT — How to write task_prompt correctly**:
    CC has DIRECT access to the workspace and knows its actual file structure and code state.
    YOU (NA) do NOT have this knowledge. Therefore:
    - Describe the GOAL and CONTEXT, NOT step-by-step implementation instructions
    - Do NOT assume specific file paths, function names, or line numbers in the workspace
    - If the user mentioned a specific path/function, pass it as "user mentioned X, please verify it exists"
    - Let CC explore the workspace and decide how to implement — do NOT micromanage
    - If CC's response contains "[需要澄清]" questions, relay them to the user before delegating again

    Args:
        task_prompt (str): Goal-oriented description of what needs to be accomplished.
            Include the user's intent, relevant background, and any constraints.
            Do NOT include assumed implementation details about the workspace internals.

    Returns:
        str: Confirmation that the task has been started asynchronously (NOT the final result —
             the result will come back automatically when execution is complete).

    Example (CORRECT — goal-oriented):
        ```python
        delegate_to_cc(
            "用户希望分析项目中的数据文件并生成统计报告。"
            "用户提到文件可能在 data/ 目录下（请自行确认）。"
            "请探索工作区，找到相关数据文件，计算统计摘要，并将结果保存到工作区。"
        )
        ```

    Example (WRONG — do NOT do this, NA doesn't actually know this):
        ```python
        # 错误示范：假设了不确定存在的路径和代码细节
        delegate_to_cc("请修改 ./src/utils.py 第42行的 calculate() 函数，将参数 n 改为 count")
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

    # 持久化 task_prompt，供结果回传时提醒 NA 本次任务的原始目标
    await plugin.store.set(chat_key=chat_key, store_key="last_cc_task_prompt", value=task_prompt)

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
            notify_msg = f"[CC Workspace] CC 任务执行失败: {ctl.message}{task_ctx_section}"
        elif ctl.signal.value == "cancel":
            notify_msg = f"[CC Workspace] CC 任务已被取消: {ctl.message}{task_ctx_section}"
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
        return f"[CC Workspace] 启动任务失败: {e}"


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
        return "[CC Workspace] 当前没有正在运行的 CC 委托任务。"

    # 先取消 NA 侧异步任务
    cancelled = await task_api.cancel(_TASK_TYPE, task_id)

    # 同时强制终止 CC 侧正在运行的进程（仅当 current_task 属于本频道时）
    cc_cancelled = False
    workspace = await _ctx.get_bound_workspace()
    if workspace is not None and workspace.status == "active":
        try:
            client = CCSandboxClient(workspace)
            queue_status = await client.get_workspace_queue(workspace_id="default")
            current_task = queue_status.get("current_task")
            if current_task and current_task.get("source_chat_key") == task_id:
                cc_cancelled = await client.force_cancel_current_task(workspace_id="default")
                if cc_cancelled:
                    logger.info(f"[cc_workspace] 已强制终止 CC 侧进程，chat_key={task_id}")
                else:
                    logger.warning(f"[cc_workspace] CC 侧进程终止失败，chat_key={task_id}")
        except Exception as e:
            logger.warning(f"[cc_workspace] 取消 CC 侧进程失败（不影响 NA 侧取消）: {e}")

    if cancelled:
        cc_hint = (
            "（CC 沙盒进程已同步终止）" if cc_cancelled
            else "（NA 侧已取消，CC 沙盒进程可能仍在后台运行，可用 `force_cancel_cc_workspace` 手动终止）"
        )
        logger.info(f"[cc_workspace] 已取消 CC 任务，chat_key={task_id}")
        return f"[CC Workspace] CC 委托任务已成功取消 {cc_hint}。"
    return "[CC Workspace] 取消任务失败，任务可能已结束。"


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
    situation, and review recent NA↔CC communication history.

    This is especially valuable in long sessions where the original delegation may
    have scrolled out of context — it brings together:
    - Current task execution state (NA-side AsyncTask status)
    - The original task prompt that was delegated to CC
    - Recent NA↔CC message exchange (last 6 entries)
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
        return "[CC Workspace] 当前频道未绑定任何 CC Workspace。"

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
                # 去除 NA_TO_CC 时自动注入的 [任务来源频道: ...] 前缀
                if log.direction == "NA_TO_CC" and content.startswith("[任务来源频道:"):
                    nl = content.find("\n\n")
                    if nl != -1:
                        content = content[nl + 2:]
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


@plugin.mount_sandbox_method(
    SandboxMethodType.BEHAVIOR,
    "上传文件到 CC Workspace",
    description=(
        "将主沙盒中的文件复制到 CC Workspace 的 data/ 目录，供 CC 沙盒直接通过文件系统访问。"
        "CC 可通过绝对路径 /workspace/default/data/<文件名> 读取该文件。"
        "适用于需要将用户提供的数据文件交给 CC 处理的场景。"
    ),
)
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


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    "从 CC Workspace 下载文件",
    description=(
        "将 CC Workspace data/ 目录中的文件复制到主沙盒共享目录，返回沙盒内可访问的文件路径。"
        "适用于 CC 生成了结果文件（如报告、图表、数据集）需要在主沙盒中进一步处理或发送给用户的场景。"
    ),
)
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

        # 内容风险扫描：对可读文本文件进行敏感凭据检测
        try:
            raw = target_host_path.read_bytes()
            text = raw[:_SCAN_SIZE_LIMIT].decode("utf-8", errors="ignore")
            hits = _scan_sensitive_content(text)
            if hits:
                risk_list = "、".join(hits)
                logger.warning(
                    f"[cc_workspace] download_file_from_cc 风险扫描命中: {target_name} → {risk_list}"
                )
                return (
                    f"[CC Workspace] ⚠️ 文件下载已拦截 — 内容风险扫描发现潜在敏感信息。\n"
                    f"命中类型：{risk_list}\n"
                    f"文件名：{target_name}\n"
                    f"如确认文件内容安全，请先在 CC Workspace 中对文件进行脱敏处理后再下载。"
                )
        except Exception as scan_err:
            logger.warning(f"[cc_workspace] download_file_from_cc 风险扫描异常（跳过）: {scan_err}")

        sandbox_path = _ctx.fs.forward_file(target_host_path)
        return str(sandbox_path)
    except Exception as e:
        logger.error(f"[cc_workspace] download_file_from_cc 失败: {e}")
        return f"[CC Workspace] 文件下载失败: {e}"


# ---------------------------------------------------------------------------
# 动态方法可见性控制（三态）
# ---------------------------------------------------------------------------


@plugin.mount_collect_methods()
async def _collect_cc_methods(ctx: schemas.AgentCtx) -> List:
    """根据当前频道的工作区状态，动态决定哪些 CC 方法对 NA 可见。

    状态1 - 未绑定工作区：仅展示 create_and_bind_workspace
    状态2 - 已绑定但沙盒未运行：仅展示 start_cc_sandbox
    状态3 - 沙盒正常运行：展示所有工作方法，隐藏创建/启动方法
    """
    workspace = await ctx.get_bound_workspace()

    # 状态1：未绑定工作区
    if workspace is None:
        return [toggle_cc_auto_workspace, create_and_bind_workspace]

    # 状态2：有工作区但沙盒未运行
    if workspace.status != "active":
        return [toggle_cc_auto_workspace, start_cc_sandbox]

    # 状态3：沙盒正常运行
    return [
        toggle_cc_auto_workspace,
        delegate_to_cc,
        cancel_cc_task,
        get_cc_context,
        force_cancel_cc_workspace,
        upload_file_to_cc,
        download_file_from_cc,
    ]
