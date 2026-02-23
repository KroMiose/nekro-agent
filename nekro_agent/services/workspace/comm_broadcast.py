"""per-workspace SSE 广播器

订阅者模式：每个前端连接注册一个 asyncio.Queue；
发布者（路由/插件 hook）调用 publish() 将事件推送到该工作区所有队列。
"""

import json
from asyncio import Queue
from typing import Dict, List

_subscribers: Dict[int, List[Queue]] = {}


async def publish(workspace_id: int, event: dict) -> None:
    """向指定工作区的所有订阅者广播事件。"""
    payload = json.dumps(event, ensure_ascii=False)
    for q in list(_subscribers.get(workspace_id, [])):
        await q.put(payload)


def subscribe(workspace_id: int) -> Queue:
    """注册新订阅者，返回其专属 Queue。"""
    q: Queue = Queue()
    _subscribers.setdefault(workspace_id, []).append(q)
    return q


def unsubscribe(workspace_id: int, q: Queue) -> None:
    """注销订阅者。"""
    lst = _subscribers.get(workspace_id, [])
    if q in lst:
        lst.remove(q)
