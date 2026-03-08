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

from asyncio import Queue, QueueFull
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from nekro_agent.core.logger import logger

_subscribers: List[Queue[str]] = []
_MAX_QUEUE_SIZE = 200
_MAX_SUBSCRIBERS = 50


# ── 事件模型 ─────────────────────────────────────────────────────────────────


class WorkspaceStatusEvent(BaseModel):
    """工作区容器状态变化事件（沙盒启动/停止/重启/重建时触发）。"""

    type: Literal["workspace_status"] = "workspace_status"
    workspace_id: int
    status: Literal["active", "stopped", "failed", "deleting"]
    name: str
    container_name: Optional[str] = None
    host_port: Optional[int] = None


class WorkspaceCcActiveEvent(BaseModel):
    """CC 沙盒任务活跃状态事件（任务开始/结束时触发）。"""

    type: Literal["workspace_cc_active"] = "workspace_cc_active"
    workspace_id: int
    active: bool
    name: Optional[str] = None
    max_duration_ms: int = Field(default=300_000, description="任务最大持续时间（ms），超时后前端自动降为 inactive")


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
    max_duration_ms: int = Field(default=300_000, description="任务最大持续时间（ms），超时后前端自动降为 inactive")


SystemEvent = Annotated[
    Union[WorkspaceStatusEvent, WorkspaceCcActiveEvent, AgentActiveEvent],
    Field(discriminator="type"),
]


# ── 状态快照存储 ──────────────────────────────────────────────────────────────

# domain → key → value（JSON 可序列化的状态字典）
_state_store: Dict[str, Dict[str, dict]] = {}


def _update_state(event: Union[WorkspaceStatusEvent, WorkspaceCcActiveEvent, AgentActiveEvent]) -> None:
    """根据事件类型更新内存状态快照。

    新增事件类型时在此处注册其状态提取逻辑即可。
    """
    if isinstance(event, WorkspaceStatusEvent):
        domain = "workspace_status"
        key = str(event.workspace_id)
        _state_store.setdefault(domain, {})[key] = {
            "workspace_id": event.workspace_id,
            "status": event.status,
            "name": event.name,
            "container_name": event.container_name,
            "host_port": event.host_port,
        }

    elif isinstance(event, WorkspaceCcActiveEvent):
        domain = "workspace_cc_active"
        key = str(event.workspace_id)
        _state_store.setdefault(domain, {})[key] = {
            "workspace_id": event.workspace_id,
            "active": event.active,
            "name": event.name,
            "max_duration_ms": event.max_duration_ms,
        }

    elif isinstance(event, AgentActiveEvent):
        domain = "agent_active"
        key = event.chat_key
        if event.active:
            _state_store.setdefault(domain, {})[key] = {
                "chat_key": event.chat_key,
                "active": True,
                "channel_name": event.channel_name,
                "chat_type": event.chat_type,
                "preset_id": event.preset_id,
                "preset_name": event.preset_name,
                "max_duration_ms": event.max_duration_ms,
            }
        else:
            # active=False 时从快照中移除该频道，避免晚到者看到已结束的任务
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


async def publish_system_event(event: Union[WorkspaceStatusEvent, WorkspaceCcActiveEvent, AgentActiveEvent]) -> None:
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
    return q


def unsubscribe_system_events(q: "Queue[str]") -> None:
    """注销订阅者。"""
    if q in _subscribers:
        _subscribers.remove(q)
