from nekro_agent.api import core, timer
from nekro_agent.api.schemas import AgentCtx

__meta__ = core.ExtMetaData(
    name="timer",
    description="[NA] 定时器工具集",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@core.agent_collector.mount_method(core.MethodType.TOOL)
async def set_timer(
    chat_key: str,
    trigger_time: int,
    event_desc: str,
    temporary: bool,
    _ctx: AgentCtx,
) -> bool:
    """设置一个定时器，在指定时间触发自身响应；临时定时器主要用于回复后设置短期自我唤醒来观察新消息和反馈
    !!!始终记住：定时器的本质功能是允许你自行唤醒你自己作为 LLM 的回复流程, 非必要不得反复自我唤醒!!!

    Args:
        chat_key (str): 会话标识
        trigger_time (int): 触发时间戳。若 trigger_time == 0 则立即触发会话；若 trigger_time < 0 则清空当前会话所有定时器
        event_desc (str): 事件描述（详细描述事件的 context 信息，触发时提供参考）
        temporary (bool): 是否临时定时器。用于设置短期自我唤醒检查新消息，同一会话只会保留最后一个临时定时器。

    Returns:
        bool: 是否设置成功

    Example:
        ```python
        # 清空定时器
        set_timer(chat_key="group_123", trigger_time=-1, event_desc="", temporary=False)

        # 临时定时器（自我唤醒）
        set_timer(
            chat_key="group_123",
            trigger_time=int(time.time()) + 60,
            event_desc="我刚才建议用户重启，需要观察反馈。",
            temporary=True
        )

        # 普通定时器（常规提醒）
        set_timer(
            chat_key="group_123",
            trigger_time=int(time.time()) + 300,
            event_desc="提醒吃早餐。context: 用户5分钟前说要吃早餐，让我提醒。",
            temporary=False
        )
        ```
    """
    if trigger_time < 0:
        return await timer.clear_timers(chat_key)
    if temporary:
        return await timer.set_temp_timer(chat_key, trigger_time, event_desc)
    return await timer.set_timer(chat_key, trigger_time, event_desc)


async def clean_up():
    """清理扩展"""
