from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.extension import ExtMetaData
from nekro_agent.services.timer_service import timer_service
from nekro_agent.tools.collector import MethodType, agent_collector

__meta__ = ExtMetaData(
    name="timer",
    description="[NA] 定时器工具集",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@agent_collector.mount_method(MethodType.TOOL)
async def set_timer(chat_key: str, trigger_time: int, event_desc: str, _ctx: AgentCtx) -> bool:
    """设置一个定时器，在指定时间触发回复，注意不要重复和频繁设置定时器！

    Args:
        chat_key (str): 会话标识
        trigger_time (int): 触发时间戳，如果为0则立即触发会话
        event_desc (str): 事件描述（详细描述事件的 context 信息，触发时提供参考）

    Returns:
        bool: 是否设置成功

    Example:
        ```python
        # 设置一个5分钟后的提醒
        set_timer(
            chat_key="group_123456789",
            trigger_time=int(time.time()) + 300,
            event_desc="提醒 xxx 吃早餐。context: xxx 在5分钟前说要去吃早餐，我答应5分钟后提醒他。"
        )

        # 直接再次触发会话（用于观察 print 输出）
        set_timer(
            chat_key="group_123456789",
            trigger_time=0,
            event_desc=""
        )
        ```
    """
    return await timer_service.set_timer(chat_key, trigger_time, event_desc)
