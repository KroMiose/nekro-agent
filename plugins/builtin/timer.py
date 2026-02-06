"""
# 定时器 (Timer)

提供定时与周期任务能力，让 AI 能够在未来某个时间点继续处理事项，或按计划周期性触发提醒。

## 主要功能

- **一次性定时器**: 在指定时间戳触发 AI（适合「X 分钟后提醒」等）。
- **临时自唤醒**: 每个频道仅保留最后一个临时定时器（适合「发完消息后过一会儿回来看看」）。
- **持久化周期任务（Cron）**: 支持创建/更新/暂停/恢复/删除，服务重启后可恢复。
- **一次性/临时定时器持久化**: 普通一次性/临时定时器会写入数据目录，重启后可恢复（带 callback 的系统定时器不会持久化）。
- **工作日/周末/节假日提醒**: 周期任务可选择 `workday_mode`：\n  - `none`：完全按 cron\n  - `mon_fri`：周一到周五\n  - `weekend`：仅周六日\n  - `cn_workday`：中国法定工作日（含调休/补班）\n  - `cn_restday`：中国休息日（周末/法定节假日/调休放假）\n- **提示词注入**: 自动注入「短期定时器列表 + 周期任务摘要（未来将触发 + 最近执行）」；需要全量列表时再调用工具查询，避免刷屏。

## 使用方法

此插件主要由 AI 在后台自动调用。例如：\n+- 当用户说「半小时后提醒我开会」时，AI 使用 `set_timer` 设置一次性定时器。\n+- 当用户说「每天 9 点提醒我打卡」时，AI 使用 `create_recurring_timer` 创建持久化 cron 周期任务。\n+- 当用户说「工作日 9 点提醒」时，AI 创建 cron 并设置 `workday_mode=mon_fri`；若需要按中国法定工作日（含调休/补班）计算，可用 `cn_workday`。\n+- 当用户说「周末 10 点提醒我去运动」时，AI 创建 cron 并设置 `workday_mode=weekend`。\n+- 当用户说「节假日早上提醒我抢票」时，AI 创建 cron 并设置 `workday_mode=cn_restday`。\n+- 当需要管理周期任务时，AI 使用 `list_recurring_timers` / `update_recurring_timer` / `pause_recurring_timer` 等工具方法。
"""

import time
from datetime import datetime

from pydantic import Field
from tzlocal import get_localzone

from nekro_agent.api import core, i18n, recurring_timer, timer
from nekro_agent.api.plugin import (
    ConfigBase,
    ExtraField,
    NekroPlugin,
    SandboxMethodType,
)
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.models.db_recurring_timer_job import DBRecurringTimerJob
from nekro_agent.services.festival_service import FestivalService

plugin = NekroPlugin(
    name="定时器工具集",
    module_name="timer",
    description="提供一次性定时器与持久化周期任务（Cron），支持工作日提醒与 AI 管理",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="定时器工具集",
        en_US="Timer Utilities",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="提供一次性定时器与持久化周期任务（Cron），支持工作日提醒与 AI 管理",
        en_US="Provides one-shot timers and persistent recurring cron jobs with workday options and AI management",
    ),
)


@plugin.mount_config()
class TimerConfig(ConfigBase):
    """定时器配置"""

    MAX_DISPLAY_DESC_LENGTH: int = Field(
        default=100,
        title="定时器描述最大显示长度",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="定时器描述最大显示长度",
                en_US="Max Timer Description Display Length",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="定时器描述超过该长度时将被截断显示",
                en_US="Timer descriptions exceeding this length will be truncated",
            ),
        ).model_dump(),
    )

    RECURRING_INJECT_UPCOMING_LIMIT: int = Field(
        default=3,
        title="周期任务注入-未来任务条数",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="周期任务注入-未来任务条数",
                en_US="Recurring Inject - Upcoming Count",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="在提示词中注入最近将触发的周期任务条数（避免刷屏）",
                en_US="How many upcoming recurring jobs to inject into prompt",
            ),
        ).model_dump(),
    )

    RECURRING_INJECT_RECENT_LIMIT: int = Field(
        default=2,
        title="周期任务注入-最近执行条数",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="周期任务注入-最近执行条数",
                en_US="Recurring Inject - Recent Runs Count",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="在提示词中注入最近执行过的周期任务条数（帮助感知日常）",
                en_US="How many recent recurring jobs to inject into prompt",
            ),
        ).model_dump(),
    )

    MAX_RECURRING_PER_CHAT: int = Field(
        default=50,
        title="每个频道最大周期任务数量",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="每个频道最大周期任务数量",
                en_US="Max Recurring Jobs Per Chat",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="用于防止 AI 或用户误操作创建过多周期任务",
                en_US="Prevent too many recurring jobs per chat",
            ),
        ).model_dump(),
    )

    DEFAULT_TIMEZONE: str = Field(
        default=str(get_localzone()),
        title="默认时区",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="默认时区",
                en_US="Default Timezone",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="创建周期任务时默认使用的时区（IANA TZ），例如 Asia/Shanghai",
                en_US="Default timezone used for recurring jobs (IANA TZ)",
            ),
        ).model_dump(),
    )


# 获取配置
config = plugin.get_config(TimerConfig)


@plugin.mount_prompt_inject_method("timer_prompt")
async def timer_prompt(_ctx: AgentCtx) -> str:
    """定时器提示词注入"""
    # 获取当前频道未触发的定时器
    chat_key = _ctx.chat_key
    timers = await timer.get_timers(chat_key)

    # 过滤掉节日祝福定时器
    timers = [t for t in timers if t.chat_key != FestivalService.FESTIVAL_CHAT_KEY]

    current_time = int(time.time())
    timer_lines: list[str] = []

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
        timer_lines = []

    # 周期任务摘要注入（限长，避免刷屏）
    active_count, paused_count, upcoming, recent = await recurring_timer.get_job_summary(
        chat_key=chat_key,
        upcoming_limit=config.RECURRING_INJECT_UPCOMING_LIMIT,
        recent_limit=config.RECURRING_INJECT_RECENT_LIMIT,
    )

    recurring_lines: list[str] = []
    for idx, job in enumerate(upcoming, 1):
        title = job.title or ""
        desc = title if title else job.event_desc
        if len(desc) > config.MAX_DISPLAY_DESC_LENGTH:
            desc = desc[: config.MAX_DISPLAY_DESC_LENGTH // 2] + "..." + desc[-config.MAX_DISPLAY_DESC_LENGTH // 2 :]
        next_run = job.next_run_at.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_at else "N/A"
        recurring_lines.append(
            f"Recurring #{idx}: {desc}\n"
            f"- ID: {job.job_id}\n"
            f"- Cron: {job.cron_expr}\n"
            f"- Next: {next_run}\n"
            f"- TZ: {job.timezone}\n"
            f"- WorkdayMode: {job.workday_mode}",
        )

    recent_lines: list[str] = []
    for idx, job in enumerate(recent, 1):
        title = job.title or ""
        desc = title if title else job.event_desc
        if len(desc) > config.MAX_DISPLAY_DESC_LENGTH:
            desc = desc[: config.MAX_DISPLAY_DESC_LENGTH // 2] + "..." + desc[-config.MAX_DISPLAY_DESC_LENGTH // 2 :]
        last_run = job.last_run_at.strftime("%Y-%m-%d %H:%M:%S") if job.last_run_at else "N/A"
        recent_lines.append(f"Recent #{idx}: {desc}\n- ID: {job.job_id}\n- LastRun: {last_run}")

    parts: list[str] = []
    if timer_lines:
        parts.append("Active Timers:\n\n" + "\n\n".join(timer_lines))
    if active_count or paused_count:
        parts.append(f"Recurring Jobs: active={active_count}, paused={paused_count}")
    if recurring_lines:
        parts.append("Upcoming Recurring:\n\n" + "\n\n".join(recurring_lines))
    if recent_lines:
        parts.append("Recent Recurring:\n\n" + "\n\n".join(recent_lines))

    if not parts:
        return "No active timers"

    parts.append("Tip: 管理周期任务时，请使用上面展示的任务ID（ID 字段）；需要全量列表可调用 `list_recurring_timers`。")
    return "\n\n".join(parts)


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
        chat_key (str): 频道标识
        trigger_time (int): 触发时间戳。若 trigger_time == 0 则立即触发频道；若 trigger_time < 0 则清空当前频道指定类型的定时器
        event_desc (str): 事件描述（详细描述事件的 context 信息，触发时提供参考）
        temporary (bool): 是否临时定时器。用于设置短期自我唤醒检查新消息，同一频道只会保留最后一个临时定时器。
                         当 trigger_time < 0 时，此参数用于指定要清除的定时器类型。

    Returns:
        bool: 是否设置成功

    Example:
        ```python
        # 临时定时器（自我唤醒）
        set_timer(
            chat_key=_ck,
            trigger_time=int(time.time()) + 60,
            event_desc="我刚才建议用户重启，需要观察反馈。",
            temporary=True
        )

        # 清空临时定时器
        set_timer(chat_key=_ck, trigger_time=-1, event_desc="", temporary=True)

        # 清空非临时定时器
        set_timer(chat_key=_ck, trigger_time=-1, event_desc="", temporary=False)

        # 普通定时器（常规提醒）
        set_timer(
            chat_key=_ck,
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


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "创建周期定时任务")
async def create_recurring_timer(
    _ctx: AgentCtx,
    chat_key: str,
    cron_expr: str,
    event_desc: str,
    workday_mode: str = "none",
    timezone: str = "",
    title: str = "",
) -> str:
    """创建一个持久化周期定时任务（cron）。

    说明：
    - cron 默认使用 5 段表达式：`min hour day month dow`
    - workday_mode：
      - none：不做额外过滤（完全按 cron）
      - mon_fri：仅周一到周五触发（不考虑法定节假日/调休）
      - weekend：仅周六日触发
      - cn_workday：按中国法定工作日触发（含调休补班）
      - cn_restday：按中国休息日触发（周末/法定节假日/调休放假）

    Args:
        chat_key: 频道标识
        cron_expr: cron 表达式（5 段）
        event_desc: 事件描述（触发时提供给 Agent 的上下文）
        workday_mode: 触发日模式（none/mon_fri/weekend/cn_workday/cn_restday）
        timezone: 时区（IANA TZ），为空则使用插件默认时区
        title: 标题（可选），用于提示词摘要展示

    Returns:
        str: 新任务的任务ID（默认4位，必要时自动扩展；全局唯一）
    """
    tz = timezone.strip() or config.DEFAULT_TIMEZONE
    mode = workday_mode.strip() or "none"
    if mode not in ("none", "mon_fri", "weekend", "cn_workday", "cn_restday"):
        raise ValueError(f"workday_mode 非法: {mode}")  # noqa: TRY003

    count = await DBRecurringTimerJob.filter(chat_key=chat_key).count()
    if count >= config.MAX_RECURRING_PER_CHAT:
        raise ValueError("周期任务数量过多，请先清理无用任务再创建")  # noqa: TRY003

    job = await recurring_timer.create_cron_job(
        chat_key=chat_key,
        cron_expr=cron_expr,
        event_desc=event_desc,
        timezone=tz,
        workday_mode=mode,
        title=title.strip() or None,
    )
    return job.job_id


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "列出周期定时任务")
async def list_recurring_timers(
    _ctx: AgentCtx,
    chat_key: str,
    status: str = "",
    limit: int = 50,
) -> dict:
    """列出当前频道的周期定时任务（用于 AI 主动管理）。

    Args:
        chat_key: 频道标识
        status: 可选筛选（active/paused），为空表示全部
        limit: 最大返回数量

    Returns:
        dict: 任务列表（JSON 可序列化）
    """
    status_filter = status.strip() or None
    jobs = await recurring_timer.list_jobs(chat_key=chat_key, status=status_filter, limit=limit)

    def _fmt(dt: datetime | None) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""

    return {
        "count": len(jobs),
        "jobs": [
            {
                "id": j.job_id,
                "title": j.title or "",
                "status": j.status,
                "cron_expr": j.cron_expr,
                "timezone": j.timezone,
                "workday_mode": j.workday_mode,
                "next_run_at": _fmt(j.next_run_at),
                "last_run_at": _fmt(j.last_run_at),
                "consecutive_failures": j.consecutive_failures,
                "last_error": j.last_error or "",
            }
            for j in jobs
        ],
    }


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "更新周期定时任务")
async def update_recurring_timer(
    _ctx: AgentCtx,
    job_id: str,
    cron_expr: str = "",
    event_desc: str = "",
    workday_mode: str = "",
    timezone: str = "",
    title: str = "",
) -> bool:
    """更新周期定时任务。

    Args:
        job_id: 任务ID（UUID）
        cron_expr: 为空表示不更新
        event_desc: 为空表示不更新
        workday_mode: 为空表示不更新（none/mon_fri/cn_workday）
        timezone: 为空表示不更新
        title: 为空表示不更新（若要清空标题，请传入单个空格 \" \"）

    Returns:
        bool: 是否更新成功
    """
    patch_workday: str | None = None
    if workday_mode.strip():
        mode = workday_mode.strip()
        if mode not in ("none", "mon_fri", "weekend", "cn_workday", "cn_restday"):
            raise ValueError(f"workday_mode 非法: {mode}")  # noqa: TRY003
        patch_workday = mode

    patch_title: str | None = None
    if title != "":
        patch_title = title.strip() or ""

    await recurring_timer.update_job(
        job_id,
        cron_expr=cron_expr.strip() or None,
        event_desc=event_desc if event_desc != "" else None,
        timezone=timezone.strip() or None,
        workday_mode=patch_workday,
        title=patch_title,
    )
    return True


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "暂停周期定时任务")
async def pause_recurring_timer(_ctx: AgentCtx, job_id: str) -> str:
    """暂停周期定时任务（暂停后不会触发）。
    
    Args:
        job_id: 任务ID（UUID）
    """
    await recurring_timer.pause_job(job_id)
    return f"周期定时任务 {job_id} 已暂停"


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "恢复周期定时任务")
async def resume_recurring_timer(_ctx: AgentCtx, job_id: str) -> str:
    """恢复周期定时任务（恢复后会重新计算下次触发时间）。
    
    Args:
        job_id: 任务ID（UUID）
    """
    await recurring_timer.resume_job(job_id)
    return f"周期定时任务 {job_id} 已恢复"


@plugin.mount_sandbox_method(SandboxMethodType.BEHAVIOR, "删除周期定时任务")
async def delete_recurring_timer(_ctx: AgentCtx, job_id: str) -> str:
    """删除周期定时任务。
    
    Args:
        job_id: 任务ID（UUID）
    """
    await recurring_timer.delete_job(job_id)
    return f"周期定时任务 {job_id} 已删除"


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件"""
