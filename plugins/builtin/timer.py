import time
from datetime import datetime

from pydantic import Field

from nekro_agent.api import core, timer
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.services.festival_service import FestivalService
from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin, SandboxMethodType

plugin = NekroPlugin(
    name="定时器工具集",
    module_name="timer",
    description="提供主动触发、预定事件的能力，支持设置、清除定时器",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_config()
class TimerConfig(ConfigBase):
    """定时器配置"""

    MAX_DISPLAY_DESC_LENGTH: int = Field(default=100, title="定时器描述最大显示长度")


# 获取配置
config = plugin.get_config(TimerConfig)


@plugin.mount_prompt_inject_method("timer_prompt")
async def timer_prompt(_ctx: AgentCtx) -> str:
    """定时器提示词注入"""
    # 获取当前会话未触发的定时器
    chat_key = _ctx.from_chat_key
    timers = await timer.get_timers(chat_key)

    # 过滤掉节日祝福定时器
    timers = [t for t in timers if t.chat_key != FestivalService.FESTIVAL_CHAT_KEY]

    if not timers:
        return "No active timers"

    current_time = int(time.time())
    timer_lines = []

    for idx, t in enumerate(timers, 1):
        # 计算剩余时间
        remain_seconds = t.trigger_time - current_time
        if remain_seconds <= 0:
            continue

        # 格式化定时器描述
        desc = t.event_desc
        if len(desc) > config.MAX_DISPLAY_DESC_LENGTH:
            desc = desc[: config.MAX_DISPLAY_DESC_LENGTH // 2] + "..." + desc[-config.MAX_DISPLAY_DESC_LENGTH // 2 :]

        # 格式化触发时间
        trigger_time_str = datetime.fromtimestamp(t.trigger_time).strftime("%Y-%m-%d %H:%M:%S")

        # 格式化剩余时间 - 更简洁的表示
        hours, remainder = divmod(remain_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        remain_time_str = (
            f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            if hours > 0
            else f"{int(minutes)}m {int(seconds)}s" if minutes > 0 else f"{int(seconds)}s"
        )

        # 定时器类型
        timer_type = "Temporary" if t.temporary else "Regular"

        timer_lines.append(
            f"Timer #{idx}: {desc}\n"
            f"- Type: {timer_type}\n"
            f"- Trigger: {trigger_time_str}\n"
            f"- Remaining: {remain_time_str}",
        )

    if not timer_lines:
        return "No active timers"

    return "Active Timers:\n\n" + "\n\n".join(timer_lines)


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "设置定时器")
async def set_timer(
    _ctx: AgentCtx,
    chat_key: str,
    trigger_time: int,
    event_desc: str,
    temporary: bool,
) -> bool:
    """设置一个定时器，在指定时间触发自身响应；临时定时器主要用于回复后设置短期自我唤醒来观察新消息和反馈
    !!!始终记住：定时器的本质功能是允许你自行唤醒你自己作为 LLM 的回复流程, 非必要不得反复自我唤醒!!!

    Args:
        chat_key (str): 会话标识
        trigger_time (int): 触发时间戳。若 trigger_time == 0 则立即触发会话；若 trigger_time < 0 则清空当前会话指定类型的定时器
        event_desc (str): 事件描述（详细描述事件的 context 信息，触发时提供参考）
        temporary (bool): 是否临时定时器。用于设置短期自我唤醒检查新消息，同一会话只会保留最后一个临时定时器。
                         当 trigger_time < 0 时，此参数用于指定要清除的定时器类型。

    Returns:
        bool: 是否设置成功

    Example:
        ```python
        # 临时定时器（自我唤醒）
        set_timer(
            chat_key="group_123",
            trigger_time=int(time.time()) + 60,
            event_desc="我刚才建议用户重启，需要观察反馈。",
            temporary=True
        )

        # 清空临时定时器
        set_timer(chat_key="group_123", trigger_time=-1, event_desc="", temporary=True)

        # 清空非临时定时器
        set_timer(chat_key="group_123", trigger_time=-1, event_desc="", temporary=False)

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
        return await timer.clear_timers(chat_key, temporary=temporary)
    if temporary:
        return await timer.set_temp_timer(chat_key, trigger_time, event_desc)
    return await timer.set_timer(chat_key, trigger_time, event_desc)


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
