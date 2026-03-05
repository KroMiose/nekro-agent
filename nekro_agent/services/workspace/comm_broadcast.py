"""per-workspace SSE 广播器

订阅者模式：每个前端连接注册一个 asyncio.Queue；
发布者（路由/插件 hook）调用 publish() 将事件推送到该工作区所有队列。

队列大小限制为 _MAX_QUEUE_SIZE，超限时自动移除该订阅者防止内存泄漏。
"""

import json
from asyncio import Queue, QueueFull
from typing import Dict, List

from nekro_agent.core.logger import logger

_subscribers: Dict[int, List[Queue]] = {}
_MAX_QUEUE_SIZE = 1000


async def publish(workspace_id: int, event: dict) -> None:
    """向指定工作区的所有订阅者广播事件。"""
    payload = json.dumps(event, ensure_ascii=False)
    stale: list[Queue] = []
    for q in list(_subscribers.get(workspace_id, [])):
        try:
            q.put_nowait(payload)
        except QueueFull:
            stale.append(q)
            logger.warning(
                f"[comm_broadcast] 订阅者队列已满（{_MAX_QUEUE_SIZE}），"
                f"自动移除断开的订阅者 workspace={workspace_id}"
            )
    # 移除超限的订阅者
    if stale:
        lst = _subscribers.get(workspace_id, [])
        for q in stale:
            if q in lst:
                lst.remove(q)


def subscribe(workspace_id: int) -> Queue:
    """注册新订阅者，返回其专属 Queue（有界）。"""
    q: Queue = Queue(maxsize=_MAX_QUEUE_SIZE)
    _subscribers.setdefault(workspace_id, []).append(q)
    return q


def unsubscribe(workspace_id: int, q: Queue) -> None:
    """注销订阅者。"""
    lst = _subscribers.get(workspace_id, [])
    if q in lst:
        lst.remove(q)
