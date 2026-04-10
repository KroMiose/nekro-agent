"""全局系统事件 SSE 广播器（Snapshot + Delta 模式）

架构概述
--------
后端维护一份全局 **状态快照（StateStore）**，按 ``domain → key → value`` 三级结构存储：

- domain: 状态领域（如 ``workspace_status``、``workspace_cc_active``）
- key:    领域内的标识（如 workspace_id 的字符串化）
- value:  JSON 可序列化的状态字典

每次调用 :func:`publish_system_event` 时，事件自动写入 StateStore（``_update_state``）；
新订阅者连接时先收到 ``type=snapshot`` 事件（包含所有 domain 的当前完整状态），
之后持续接收增量 delta 事件。

扩展新的状态类型
----------------
1. 定义新的 Pydantic 事件模型（``type`` 字段作为 discriminator）
2. 将其加入 :data:`SystemEvent` Union
3. 在 :func:`_update_state` 中注册该类型的状态提取逻辑
4. 前端 ``useSystemEvents`` 中增加对应的 state + handler

订阅者模式
----------
- 每个前端连接注册一个 ``asyncio.Queue``
- 队列大小限制 ``_MAX_QUEUE_SIZE``，超限自动移除断开连接的订阅者
- 最大并发订阅者 ``_MAX_SUBSCRIBERS``
"""

import asyncio
from asyncio import Queue, QueueFull
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from nekro_agent.core.logger import logger

_subscribers: List[Queue[str]] = []
_MAX_QUEUE_SIZE = 200
_MAX_SUBSCRIBERS = 50


WorkspaceStatusValue = Literal["active", "stopped", "failed", "deleting"]
WORKSPACE_STATUS_ACTIVE: WorkspaceStatusValue = "active"
WORKSPACE_STATUS_STOPPED: WorkspaceStatusValue = "stopped"
WORKSPACE_STATUS_FAILED: WorkspaceStatusValue = "failed"
WORKSPACE_STATUS_DELETING: WorkspaceStatusValue = "deleting"
WORKSPACE_STATUS_VALUES: tuple[WorkspaceStatusValue, ...] = (
    WORKSPACE_STATUS_ACTIVE,
    WORKSPACE_STATUS_STOPPED,
    WORKSPACE_STATUS_FAILED,
    WORKSPACE_STATUS_DELETING,
)

WorkspaceCcRuntimePhase = Literal["queued", "running", "responding", "completed", "failed", "cancelled"]
WORKSPACE_CC_PHASE_QUEUED: WorkspaceCcRuntimePhase = "queued"
WORKSPACE_CC_PHASE_RUNNING: WorkspaceCcRuntimePhase = "running"
WORKSPACE_CC_PHASE_RESPONDING: WorkspaceCcRuntimePhase = "responding"
WORKSPACE_CC_PHASE_COMPLETED: WorkspaceCcRuntimePhase = "completed"
WORKSPACE_CC_PHASE_FAILED: WorkspaceCcRuntimePhase = "failed"
WORKSPACE_CC_PHASE_CANCELLED: WorkspaceCcRuntimePhase = "cancelled"
WORKSPACE_CC_RUNTIME_PHASE_VALUES: tuple[WorkspaceCcRuntimePhase, ...] = (
    WORKSPACE_CC_PHASE_QUEUED,
    WORKSPACE_CC_PHASE_RUNNING,
    WORKSPACE_CC_PHASE_RESPONDING,
    WORKSPACE_CC_PHASE_COMPLETED,
    WORKSPACE_CC_PHASE_FAILED,
    WORKSPACE_CC_PHASE_CANCELLED,
)


# ── 事件模型 ─────────────────────────────────────────────────────────────────


class WorkspaceStatusEvent(BaseModel):
    """工作区容器状态变化事件（沙盒启动/停止/重启/重建时触发）。"""

    type: Literal["workspace_status"] = "workspace_status"
    workspace_id: int
    status: WorkspaceStatusValue
    name: str
    container_name: Optional[str] = None
    host_port: Optional[int] = None


class WorkspaceCcActiveEvent(BaseModel):
    """CC 沙盒任务活跃状态事件（任务开始/结束时触发）。"""

    type: Literal["workspace_cc_active"] = "workspace_cc_active"
    workspace_id: int
    active: bool
    name: Optional[str] = None
    started_at: int = Field(default=0, description="任务开始时间戳（ms），用于前端恢复真实耗时")
    max_duration_ms: int = Field(default=300_000, description="任务最大持续时间（ms），超时后前端自动降为 inactive")


class WorkspaceCcRuntimeStatusEvent(BaseModel):
    """工作区 CC 运行阶段状态事件。"""

    type: Literal["workspace_cc_runtime_status"] = "workspace_cc_runtime_status"
    workspace_id: int
    active: bool
    name: Optional[str] = None
    started_at: int = Field(default=0, description="任务开始时间戳（ms）")
    updated_at: int = Field(default=0, description="本次状态更新时间戳（ms）")
    phase: WorkspaceCcRuntimePhase = WORKSPACE_CC_PHASE_RUNNING
    current_tool: Optional[str] = None
    source_chat_key: Optional[str] = None
    queue_length: int = 0
    operation_block_count: int = 0
    last_block_kind: Optional[Literal["tool_call", "tool_result", "text_chunk"]] = None
    last_block_summary: Optional[str] = None
    error_summary: Optional[str] = None


class AgentActiveEvent(BaseModel):
    """NA Agent 响应生成活跃状态事件（频道 AI 处理开始/结束时触发）。

    前端使用此事件在全局悬浮卡片中展示正在处理的频道及其绑定的人设头像。
    注意：头像 base64 数据量较大，不内联于事件，由前端通过 preset_id 独立获取。
    """

    type: Literal["agent_active"] = "agent_active"
    chat_key: str
    active: bool
    channel_name: Optional[str] = None
    chat_type: Optional[str] = None
    preset_id: Optional[int] = None
    preset_name: Optional[str] = None
    started_at: int = Field(default=0, description="任务开始时间戳（ms），用于前端恢复真实耗时")
    max_duration_ms: int = Field(default=300_000, description="任务最大持续时间（ms），超时后前端自动降为 inactive")


class AgentRuntimeStatusEvent(BaseModel):
    """NA Agent 运行阶段状态事件。"""

    type: Literal["agent_runtime_status"] = "agent_runtime_status"
    chat_key: str
    active: bool
    channel_name: Optional[str] = None
    chat_type: Optional[str] = None
    preset_id: Optional[int] = None
    preset_name: Optional[str] = None
    started_at: int = Field(default=0, description="任务开始时间戳（ms）")
    updated_at: int = Field(default=0, description="本次状态更新时间戳（ms）")
    phase: Literal[
        "llm_generating",
        "llm_retrying",
        "sandbox_running",
        "sandbox_stopped",
        "iterating",
        "completed",
        "failed",
    ] = "llm_generating"
    iteration_index: int = 1
    iteration_total: int = 1
    llm_retry_index: int = 1
    llm_retry_total: int = 1
    sandbox_stop_type: Optional[int] = None
    model_name: Optional[str] = None
    error_summary: Optional[str] = None


class MemoryRecallMatchedNode(BaseModel):
    """记忆检索命中节点。"""

    memory_type: Literal["paragraph", "relation", "episode"]
    id: int
    score: float = 0.0


class MemoryRecallActivityEvent(BaseModel):
    """记忆检索活动状态事件。"""

    type: Literal["memory_recall_activity"] = "memory_recall_activity"
    workspace_id: int
    chat_key: str
    active: bool
    phase: Literal["query_built", "retrieving", "compiled", "applied"] = "query_built"
    request_id: str
    target_kind: Literal["na_history", "cc_handshake"] = "na_history"
    focus_text: str = ""
    query_text: str = ""
    channel_name: Optional[str] = None
    started_at: int = Field(default=0, description="客户端可恢复的开始时间戳（ms）")
    expires_in_ms: int = Field(default=8000, description="前端展示有效期（ms）")
    hit_count: int = 0
    applied_count: int = 0
    matched_nodes: List[MemoryRecallMatchedNode] = Field(default_factory=list)
    query_embedding_time_ms: float = 0.0
    search_time_ms: float = 0.0


class KbIndexProgressEvent(BaseModel):
    """知识库文档索引进度事件。"""

    type: Literal["kb_index_progress"] = "kb_index_progress"
    workspace_id: int
    document_id: int
    active: bool
    title: str = ""
    source_path: str = ""
    phase: Literal["queued", "extracting", "chunking", "embedding", "upserting", "ready", "failed"] = "queued"
    started_at: int = Field(default=0, description="索引开始时间戳（ms）")
    updated_at: int = Field(default=0, description="本次状态更新时间戳（ms）")
    progress_percent: int = Field(default=0, ge=0, le=100)
    total_chunks: int = 0
    processed_chunks: int = 0
    expires_in_ms: int = Field(default=5000, description="终态前端展示有效期（ms）")
    error_summary: str = ""


class KbLibraryIndexProgressEvent(BaseModel):
    """全局知识库文件索引进度事件。"""

    type: Literal["kb_library_index_progress"] = "kb_library_index_progress"
    asset_id: int
    active: bool
    title: str = ""
    source_path: str = ""
    phase: Literal["queued", "extracting", "chunking", "embedding", "upserting", "ready", "failed"] = "queued"
    started_at: int = Field(default=0, description="索引开始时间戳（ms）")
    updated_at: int = Field(default=0, description="本次状态更新时间戳（ms）")
    progress_percent: int = Field(default=0, ge=0, le=100)
    total_chunks: int = 0
    processed_chunks: int = 0
    expires_in_ms: int = Field(default=5000, description="终态前端展示有效期（ms）")
    error_summary: str = ""


SystemEvent = Annotated[
    Union[
        WorkspaceStatusEvent,
        WorkspaceCcActiveEvent,
        WorkspaceCcRuntimeStatusEvent,
        AgentActiveEvent,
        AgentRuntimeStatusEvent,
        MemoryRecallActivityEvent,
        KbIndexProgressEvent,
        KbLibraryIndexProgressEvent,
    ],
    Field(discriminator="type"),
]


class WorkspaceStatusState(BaseModel):
    workspace_id: int
    status: WorkspaceStatusValue
    name: str
    container_name: Optional[str] = None
    host_port: Optional[int] = None


class WorkspaceCcActiveState(BaseModel):
    workspace_id: int
    active: Literal[True] = True
    name: Optional[str] = None
    started_at: int
    max_duration_ms: int


class WorkspaceCcRuntimeStatusState(BaseModel):
    workspace_id: int
    active: Literal[True] = True
    name: Optional[str] = None
    started_at: int
    updated_at: int
    phase: WorkspaceCcRuntimePhase
    current_tool: Optional[str] = None
    source_chat_key: Optional[str] = None
    queue_length: int = 0
    operation_block_count: int = 0
    last_block_kind: Optional[Literal["tool_call", "tool_result", "text_chunk"]] = None
    last_block_summary: Optional[str] = None
    error_summary: Optional[str] = None


class AgentActiveState(BaseModel):
    chat_key: str
    active: Literal[True] = True
    channel_name: Optional[str] = None
    chat_type: Optional[str] = None
    preset_id: Optional[int] = None
    preset_name: Optional[str] = None
    started_at: int
    max_duration_ms: int


class AgentRuntimeStatusState(BaseModel):
    chat_key: str
    active: Literal[True] = True
    channel_name: Optional[str] = None
    chat_type: Optional[str] = None
    preset_id: Optional[int] = None
    preset_name: Optional[str] = None
    started_at: int
    updated_at: int
    phase: Literal[
        "llm_generating",
        "llm_retrying",
        "sandbox_running",
        "sandbox_stopped",
        "iterating",
        "completed",
        "failed",
    ]
    iteration_index: int
    iteration_total: int
    llm_retry_index: int
    llm_retry_total: int
    sandbox_stop_type: Optional[int] = None
    model_name: Optional[str] = None
    error_summary: Optional[str] = None


class MemoryRecallActivityState(BaseModel):
    workspace_id: int
    chat_key: str
    active: Literal[True] = True
    phase: Literal["query_built", "retrieving", "compiled", "applied"]
    request_id: str
    target_kind: Literal["na_history", "cc_handshake"]
    focus_text: str = ""
    query_text: str = ""
    channel_name: Optional[str] = None
    started_at: int
    expires_in_ms: int
    hit_count: int
    applied_count: int
    matched_nodes: List[MemoryRecallMatchedNode] = Field(default_factory=list)
    query_embedding_time_ms: float
    search_time_ms: float


class KbIndexProgressState(BaseModel):
    workspace_id: int
    document_id: int
    active: Literal[True] = True
    title: str = ""
    source_path: str = ""
    phase: Literal["queued", "extracting", "chunking", "embedding", "upserting", "ready", "failed"]
    started_at: int
    updated_at: int
    progress_percent: int
    total_chunks: int
    processed_chunks: int
    expires_in_ms: int
    error_summary: str = ""


class KbLibraryIndexProgressState(BaseModel):
    asset_id: int
    active: Literal[True] = True
    title: str = ""
    source_path: str = ""
    phase: Literal["queued", "extracting", "chunking", "embedding", "upserting", "ready", "failed"]
    started_at: int
    updated_at: int
    progress_percent: int
    total_chunks: int
    processed_chunks: int
    expires_in_ms: int
    error_summary: str = ""


# ── 状态快照存储 ──────────────────────────────────────────────────────────────

# domain → key → value（JSON 可序列化的状态字典）
_state_store: Dict[str, Dict[str, Dict[str, Any]]] = {}


def _update_state(
    event: Union[
        WorkspaceStatusEvent,
        WorkspaceCcActiveEvent,
        WorkspaceCcRuntimeStatusEvent,
        AgentActiveEvent,
        AgentRuntimeStatusEvent,
        MemoryRecallActivityEvent,
        KbIndexProgressEvent,
        KbLibraryIndexProgressEvent,
    ],
) -> None:
    """根据事件类型更新内存状态快照。

    新增事件类型时在此处注册其状态提取逻辑即可。
    """
    if isinstance(event, WorkspaceStatusEvent):
        domain = "workspace_status"
        key = str(event.workspace_id)
        _state_store.setdefault(domain, {})[key] = WorkspaceStatusState(
            workspace_id=event.workspace_id,
            status=event.status,
            name=event.name,
            container_name=event.container_name,
            host_port=event.host_port,
        ).model_dump()

    elif isinstance(event, WorkspaceCcActiveEvent):
        domain = "workspace_cc_active"
        key = str(event.workspace_id)
        if event.active:
            _state_store.setdefault(domain, {})[key] = WorkspaceCcActiveState(
                workspace_id=event.workspace_id,
                name=event.name,
                started_at=event.started_at,
                max_duration_ms=event.max_duration_ms,
            ).model_dump()
        else:
            _state_store.get(domain, {}).pop(key, None)

    elif isinstance(event, WorkspaceCcRuntimeStatusEvent):
        domain = "workspace_cc_runtime_status"
        key = str(event.workspace_id)
        if event.active:
            _state_store.setdefault(domain, {})[key] = WorkspaceCcRuntimeStatusState(
                workspace_id=event.workspace_id,
                name=event.name,
                started_at=event.started_at,
                updated_at=event.updated_at,
                phase=event.phase,
                current_tool=event.current_tool,
                source_chat_key=event.source_chat_key,
                queue_length=event.queue_length,
                operation_block_count=event.operation_block_count,
                last_block_kind=event.last_block_kind,
                last_block_summary=event.last_block_summary,
                error_summary=event.error_summary,
            ).model_dump()
        else:
            _state_store.get(domain, {}).pop(key, None)

    elif isinstance(event, AgentActiveEvent):
        domain = "agent_active"
        key = event.chat_key
        if event.active:
            _state_store.setdefault(domain, {})[key] = AgentActiveState(
                chat_key=event.chat_key,
                channel_name=event.channel_name,
                chat_type=event.chat_type,
                preset_id=event.preset_id,
                preset_name=event.preset_name,
                started_at=event.started_at,
                max_duration_ms=event.max_duration_ms,
            ).model_dump()
        else:
            # active=False 时从快照中移除该频道，避免晚到者看到已结束的任务
            _state_store.get(domain, {}).pop(key, None)

    elif isinstance(event, AgentRuntimeStatusEvent):
        domain = "agent_runtime_status"
        key = event.chat_key
        if event.active:
            _state_store.setdefault(domain, {})[key] = AgentRuntimeStatusState(
                chat_key=event.chat_key,
                channel_name=event.channel_name,
                chat_type=event.chat_type,
                preset_id=event.preset_id,
                preset_name=event.preset_name,
                started_at=event.started_at,
                updated_at=event.updated_at,
                phase=event.phase,
                iteration_index=event.iteration_index,
                iteration_total=event.iteration_total,
                llm_retry_index=event.llm_retry_index,
                llm_retry_total=event.llm_retry_total,
                sandbox_stop_type=event.sandbox_stop_type,
                model_name=event.model_name,
                error_summary=event.error_summary,
            ).model_dump()
        else:
            _state_store.get(domain, {}).pop(key, None)

    elif isinstance(event, MemoryRecallActivityEvent):
        domain = "memory_recall_activity"
        key = f"{event.workspace_id}:{event.chat_key}"
        if event.active:
            _state_store.setdefault(domain, {})[key] = MemoryRecallActivityState(
                workspace_id=event.workspace_id,
                chat_key=event.chat_key,
                phase=event.phase,
                request_id=event.request_id,
                target_kind=event.target_kind,
                focus_text=event.focus_text,
                query_text=event.query_text,
                channel_name=event.channel_name,
                started_at=event.started_at,
                expires_in_ms=event.expires_in_ms,
                hit_count=event.hit_count,
                applied_count=event.applied_count,
                matched_nodes=event.matched_nodes,
                query_embedding_time_ms=event.query_embedding_time_ms,
                search_time_ms=event.search_time_ms,
            ).model_dump()
        else:
            current = _state_store.get(domain, {}).get(key)
            if current is None or current.get("request_id") == event.request_id:
                _state_store.get(domain, {}).pop(key, None)

    elif isinstance(event, KbIndexProgressEvent):
        domain = "kb_index_progress"
        key = f"{event.workspace_id}:{event.document_id}"
        if event.active:
            _state_store.setdefault(domain, {})[key] = KbIndexProgressState(
                workspace_id=event.workspace_id,
                document_id=event.document_id,
                title=event.title,
                source_path=event.source_path,
                phase=event.phase,
                started_at=event.started_at,
                updated_at=event.updated_at,
                progress_percent=event.progress_percent,
                total_chunks=event.total_chunks,
                processed_chunks=event.processed_chunks,
                expires_in_ms=event.expires_in_ms,
                error_summary=event.error_summary,
            ).model_dump()
        else:
            _state_store.get(domain, {}).pop(key, None)

    elif isinstance(event, KbLibraryIndexProgressEvent):
        domain = "kb_library_index_progress"
        key = str(event.asset_id)
        if event.active:
            _state_store.setdefault(domain, {})[key] = KbLibraryIndexProgressState(
                asset_id=event.asset_id,
                title=event.title,
                source_path=event.source_path,
                phase=event.phase,
                started_at=event.started_at,
                updated_at=event.updated_at,
                progress_percent=event.progress_percent,
                total_chunks=event.total_chunks,
                processed_chunks=event.processed_chunks,
                expires_in_ms=event.expires_in_ms,
                error_summary=event.error_summary,
            ).model_dump()
        else:
            _state_store.get(domain, {}).pop(key, None)


def get_state_snapshot() -> Dict[str, Dict[str, dict]]:
    """返回当前全部状态快照的深拷贝。

    结构::

        {
            "workspace_status": {
                "1": {"workspace_id": 1, "status": "active", ...},
                "2": {"workspace_id": 2, "status": "stopped", ...},
            },
            "workspace_cc_active": {
                "1": {"workspace_id": 1, "active": true, ...},
            },
        }
    """
    return {domain: dict(entries) for domain, entries in _state_store.items()}


# ── 广播器 ───────────────────────────────────────────────────────────────────


def _build_snapshot_payload() -> str:
    """构建 snapshot 事件的 JSON payload。"""
    import json

    return json.dumps({"type": "snapshot", "data": get_state_snapshot()}, ensure_ascii=False)


async def publish_system_event(
    event: Union[
        WorkspaceStatusEvent,
        WorkspaceCcActiveEvent,
        WorkspaceCcRuntimeStatusEvent,
        AgentActiveEvent,
        AgentRuntimeStatusEvent,
        MemoryRecallActivityEvent,
        KbIndexProgressEvent,
        KbLibraryIndexProgressEvent,
    ],
) -> None:
    """向所有全局 SSE 订阅者广播事件，并同步更新状态快照。"""
    _update_state(event)

    payload = event.model_dump_json()
    stale: list[Queue[str]] = []
    for q in list(_subscribers):
        try:
            q.put_nowait(payload)
        except QueueFull:
            stale.append(q)
            logger.warning("[system_broadcast] 订阅者队列已满，自动移除断开的连接")
    if stale:
        for q in stale:
            if q in _subscribers:
                _subscribers.remove(q)


def subscribe_system_events() -> "Queue[str] | None":
    """注册新订阅者，返回专属 Queue；连接数超限时返回 None。

    订阅时会立即向 Queue 推入一条 snapshot 事件（包含所有 domain 的当前状态），
    确保晚到的订阅者能立即获取完整状态。
    """
    if len(_subscribers) >= _MAX_SUBSCRIBERS:
        logger.warning(f"[system_broadcast] 全局 SSE 连接数已达上限 {_MAX_SUBSCRIBERS}，拒绝新连接")
        return None
    q: Queue[str] = Queue(maxsize=_MAX_QUEUE_SIZE)

    # 新订阅者立即获得完整状态快照
    snapshot_payload = _build_snapshot_payload()
    q.put_nowait(snapshot_payload)

    _subscribers.append(q)
    logger.debug(f"[system_broadcast] 新增全局 SSE 订阅，当前连接数: {len(_subscribers)}")
    return q


def unsubscribe_system_events(q: "Queue[str]") -> None:
    """注销订阅者。"""
    if q in _subscribers:
        _subscribers.remove(q)
        logger.debug(f"[system_broadcast] 移除全局 SSE 订阅，当前连接数: {len(_subscribers)}")


async def publish_memory_recall_activity(event: MemoryRecallActivityEvent) -> None:
    """发布记忆检索活动状态，并在 TTL 到期后自动清理。"""
    await publish_system_event(event)
    if not event.active or event.phase != "applied" or event.expires_in_ms <= 0:
        return

    async def _clear_later() -> None:
        await asyncio.sleep(event.expires_in_ms / 1000)
        await publish_system_event(
            MemoryRecallActivityEvent(
                workspace_id=event.workspace_id,
                chat_key=event.chat_key,
                active=False,
                phase=event.phase,
                request_id=event.request_id,
                target_kind=event.target_kind,
            )
        )

    asyncio.create_task(_clear_later())


async def publish_kb_index_progress(event: KbIndexProgressEvent) -> None:
    """发布知识库索引进度，并在终态后自动清理。"""
    await publish_system_event(event)
    if not event.active or event.phase not in {"ready", "failed"} or event.expires_in_ms <= 0:
        return

    async def _clear_later() -> None:
        await asyncio.sleep(event.expires_in_ms / 1000)
        await publish_system_event(
            KbIndexProgressEvent(
                workspace_id=event.workspace_id,
                document_id=event.document_id,
                active=False,
            )
        )

    asyncio.create_task(_clear_later())


async def publish_kb_library_index_progress(event: KbLibraryIndexProgressEvent) -> None:
    """发布全局知识库文件索引进度，并在终态后自动清理。"""
    await publish_system_event(event)
    if not event.active or event.phase not in {"ready", "failed"} or event.expires_in_ms <= 0:
        return

    async def _clear_later() -> None:
        await asyncio.sleep(event.expires_in_ms / 1000)
        await publish_system_event(
            KbLibraryIndexProgressEvent(
                asset_id=event.asset_id,
                active=False,
            )
        )

    asyncio.create_task(_clear_later())
