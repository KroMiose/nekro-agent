"""定时器相关 API

此模块提供了与定时器相关的 API 接口。
"""

from typing import Dict, List, Optional

from nekro_agent.services.timer_service import TimerTask, timer_service

__all__ = [
    "clear_timers",
    "get_timers",
    "set_temp_timer",
    "set_timer",
]


async def set_timer(chat_key: str, trigger_time: int, event_desc: str) -> bool:
    """设置一个定时器

    Args:
        chat_key (str): 会话标识，格式为 "{adapter_key}-{type}_{id}"，例如 "platform-group_123456"
        trigger_time (int): 触发时间戳
        event_desc (str): 事件描述（详细描述事件的 context 信息，触发时提供参考）
        ctx (AgentCtx): 上下文对象

    Returns:
        bool: 是否设置成功

    Example:
        ```python
        from nekro_agent.api.timer import set_timer
        import time

        # 设置5分钟后的定时器
        set_timer(
            chat_key,
            int(time.time()) + 300,
            "提醒用户吃早餐",
            ctx
        )
        ```
    """
    return await timer_service.set_timer(chat_key, trigger_time, event_desc, override=False)


async def set_temp_timer(chat_key: str, trigger_time: int, event_desc: str) -> bool:
    """设置一个临时定时器（用于短期自我唤醒检查新消息，同一会话只会保留最后一个临时定时器）

    Args:
        chat_key (str): 会话标识，格式为 "{adapter_key}-{type}_{id}"，例如 "platform-group_123456"
        trigger_time (int): 触发时间戳
        event_desc (str): 事件描述（详细描述事件的 context 信息，触发时提供参考）
        ctx (AgentCtx): 上下文对象

    Returns:
        bool: 是否设置成功

    Example:
        ```python
        from nekro_agent.api.timer import set_temp_timer
        import time

        # 设置1分钟后的临时定时器
        set_temp_timer(
            chat_key,
            int(time.time()) + 60,
            "检查用户是否已重启系统",
            ctx
        )
        ```
    """
    return await timer_service.set_timer(chat_key, trigger_time, event_desc, override=True)


async def clear_timers(chat_key: str, temporary: Optional[bool] = None) -> bool:
    """清空指定会话的定时器

    Args:
        chat_key (str): 会话标识，格式为 "{adapter_key}-{type}_{id}"，例如 "platform-group_123456"
        temporary (Optional[bool], optional): 定时器类型筛选。None表示清除所有定时器，True只清除临时定时器，False只清除非临时定时器。

    Returns:
        bool: 是否清空成功

    Example:
        ```python
        from nekro_agent.api import timer

        # 清空群组的所有定时器
        timer.clear_timers(chat_key)

        # 只清空临时定时器
        timer.clear_timers(chat_key, temporary=True)

        # 只清空非临时定时器
        timer.clear_timers(chat_key, temporary=False)
        ```
    """
    return await timer_service.set_timer(chat_key, -1, "", override=False, temporary=temporary)


async def get_timers(chat_key: str) -> List[TimerTask]:
    """获取指定会话的所有未触发定时器

    Args:
        chat_key (str): 会话标识，格式为 "{adapter_key}-{type}_{id}"，例如 "platform-group_123456"

    Returns:
        List[TimerTask]: 定时器任务列表

    Example:
        ```python
        from nekro_agent.api import timer

        # 获取群组的所有定时器
        timers = await timer.get_timers(chat_key)
        for t in timers:
            print(f"触发时间: {t.trigger_time}, 描述: {t.event_desc}")
        ```
    """
    return timer_service.get_timers(chat_key)
