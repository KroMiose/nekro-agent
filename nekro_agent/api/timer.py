"""定时器相关 API

此模块提供了与定时器相关的 API 接口。
"""

from nekro_agent.services.timer_service import timer_service

__all__ = [
    "clear_timers",
    "set_temp_timer",
    "set_timer",
]


async def set_timer(chat_key: str, trigger_time: int, event_desc: str) -> bool:
    """设置一个定时器

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"
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
            "group_123456",
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
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"
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
            "group_123456",
            int(time.time()) + 60,
            "检查用户是否已重启系统",
            ctx
        )
        ```
    """
    return await timer_service.set_timer(chat_key, trigger_time, event_desc, override=True)


async def clear_timers(chat_key: str) -> bool:
    """清空指定会话的所有定时器

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"

    Returns:
        bool: 是否清空成功

    Example:
        ```python
        from nekro_agent.api.timer import clear_timers

        # 清空群组的所有定时器
        clear_timers("group_123456")
        ```
    """
    return await timer_service.set_timer(chat_key, -1, "", override=False)
