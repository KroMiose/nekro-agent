"""全局系统事件 SSE 广播器

订阅者模式：每个已登录的前端连接注册一个 asyncio.Queue；
发布者（workspace 路由、cc_workspace 插件等）调用 publish_system_event() 推送事件。

支持的事件类型：
- WorkspaceStatusEvent: 工作区容器状态变化
- WorkspaceCcActiveEvent: CC 沙盒任务开始/结束

队列大小限制 _MAX_QUEUE_SIZE，超限自动移除断开连接的订阅者。
"""

from asyncio import Queue, QueueFull
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from nekro_agent.core.logger import logger

_subscribers: List[Queue] = []
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
    max_duration_ms: int = Field(default=300_000, description="任务最大持续时间（ms），超时后前端自动降为 inactive")


SystemEvent = Annotated[
    Union[WorkspaceStatusEvent, WorkspaceCcActiveEvent],
    Field(discriminator="type"),
]


# ── 广播器 ───────────────────────────────────────────────────────────────────


async def publish_system_event(event: Union[WorkspaceStatusEvent, WorkspaceCcActiveEvent]) -> None:
    """向所有全局 SSE 订阅者广播事件。"""
    payload = event.model_dump_json()
    stale: list[Queue] = []
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


def subscribe_system_events() -> "Queue | None":
    """注册新订阅者，返回专属 Queue；连接数超限时返回 None。"""
    if len(_subscribers) >= _MAX_SUBSCRIBERS:
        logger.warning(f"[system_broadcast] 全局 SSE 连接数已达上限 {_MAX_SUBSCRIBERS}，拒绝新连接")
        return None
    q: Queue = Queue(maxsize=_MAX_QUEUE_SIZE)
    _subscribers.append(q)
    return q


def unsubscribe_system_events(q: "Queue") -> None:
    """注销订阅者。"""
    if q in _subscribers:
        _subscribers.remove(q)
