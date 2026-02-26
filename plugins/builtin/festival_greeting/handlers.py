"""节日祝福插件 - 核心处理逻辑"""

import asyncio
import random
from typing import List, Union

from nekro_agent.core import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.services.message_service import message_service
from nekro_agent.services.timer.timer_service import timer_service

from .festivals import (
    CHINESE_TRADITIONAL_FESTIVALS,
    SOLAR_TERM_FESTIVALS,
    SPECIAL_DAY_FESTIVALS,
    WESTERN_FESTIVALS,
    FestivalCategory,
    FestivalConfig,
    FestivalDateCalculator,
    FestivalType,
)
from .plugin import (
    CustomLunarFestival,
    CustomNthWeekdayFestival,
    CustomSolarFestival,
    FestivalGreetingConfig,
    plugin,
)

# 节日祝福专用的 chat_key
FESTIVAL_CHAT_KEY = "system_festival"

# 存储已设置的节日定时器信息
_festival_timers: List[str] = []


def _convert_custom_festivals(
    solar_festivals: List[CustomSolarFestival],
    lunar_festivals: List[CustomLunarFestival],
    nth_weekday_festivals: List[CustomNthWeekdayFestival],
) -> List[FestivalConfig]:
    """将自定义节日配置转换为内部节日配置格式

    Args:
        solar_festivals: 公历节日列表
        lunar_festivals: 农历节日列表
        nth_weekday_festivals: 第N个星期几节日列表

    Returns:
        List[FestivalConfig]: 内部节日配置列表
    """
    result: List[FestivalConfig] = []

    # 转换公历节日
    for f in solar_festivals:
        if not f.enabled:
            continue
        result.append(
            FestivalConfig(
                name=f.name,
                description=f.description,
                festival_type=FestivalType.SOLAR,
                category=FestivalCategory.CUSTOM,
                month=f.month,
                day=f.day,
                hour=f.hour,
                minute=f.minute,
            ),
        )

    # 转换农历节日
    for f in lunar_festivals:
        if not f.enabled:
            continue
        result.append(
            FestivalConfig(
                name=f.name,
                description=f.description,
                festival_type=FestivalType.LUNAR,
                category=FestivalCategory.CUSTOM,
                month=f.month,
                day=f.day,
                hour=f.hour,
                minute=f.minute,
            ),
        )

    # 转换第N个星期几节日
    for f in nth_weekday_festivals:
        if not f.enabled:
            continue
        result.append(
            FestivalConfig(
                name=f.name,
                description=f.description,
                festival_type=FestivalType.SPECIAL,
                category=FestivalCategory.CUSTOM,
                month=f.month,
                hour=f.hour,
                minute=f.minute,
                special_type="nth_weekday",
                special_params={
                    "weekday": f.weekday,
                    "nth": f.nth,
                },
            ),
        )

    return result


async def _festival_callback(festival_name: str, event_desc: str):
    """节日触发回调

    Args:
        festival_name: 节日名称
        event_desc: 事件描述
    """
    # 每次触发时重新获取配置
    current_config: FestivalGreetingConfig = plugin.get_config(FestivalGreetingConfig)

    channels = await DBChatChannel.filter(is_active=True).all()
    skip_keys = set(current_config.SKIP_CHAT_KEYS)

    sent_count = 0
    for channel in channels:
        # 跳过 group_0 和配置中指定跳过的频道
        if channel.chat_key == "group_0" or channel.chat_key in skip_keys:
            continue
        try:
            await message_service.push_system_message(
                chat_key=channel.chat_key,
                agent_messages=event_desc,
                trigger_agent=True,
            )
            sent_count += 1
            # 每个聊天频道间隔随机时间，防止并发过高
            await asyncio.sleep(random.randint(1, current_config.RANDOM_DELAY_MAX))
        except Exception as e:
            logger.error(f"向频道 {channel.chat_key} 发送 {festival_name} 祝福失败: {e}")

    logger.info(f"节日祝福 {festival_name} 发送完成，共推送至 {sent_count} 个聊天频道")


async def _set_festival_timer(
    trigger_time: int,
    year: str,
    calendar_type: str,
    month: int,
    day: int,
    festival_name: str,
    desc: str,
):
    """设置节日定时器

    Args:
        trigger_time: 触发时间戳
        year: 年份
        calendar_type: 历法类型
        month: 月份
        day: 日期
        festival_name: 节日名称
        desc: 节日说明
    """
    event_desc = (
        f"{year}年{calendar_type}{month}月{day}日{festival_name}。\n"
        f"节日说明：{desc}\n\n"
        "context：这是一个预设的系统节日提醒，请根据节日特点和说明自由发挥，"
        "表达你的祝福，记得加入应景的表情。"
    )

    async def callback():
        await _festival_callback(festival_name, event_desc)
        # 触发后重新设置下一年的定时器
        await _schedule_next_year_timer(festival_name)

    await timer_service.set_timer(
        chat_key=FESTIVAL_CHAT_KEY,
        trigger_time=trigger_time,
        event_desc=event_desc,
        silent=True,
        callback=callback,
    )

    _festival_timers.append(festival_name)


async def _schedule_next_year_timer(festival_name: str):
    """在当前节日触发后，重新调度下一年的同一节日

    Args:
        festival_name: 节日名称
    """
    current_config: FestivalGreetingConfig = plugin.get_config(FestivalGreetingConfig)

    # 查找对应的节日配置
    all_festivals: List[FestivalConfig] = []

    if current_config.ENABLE_CHINESE_TRADITIONAL:
        all_festivals.extend(CHINESE_TRADITIONAL_FESTIVALS)
    if current_config.ENABLE_WESTERN_FESTIVALS:
        all_festivals.extend(WESTERN_FESTIVALS)
    if current_config.ENABLE_SOLAR_TERMS:
        all_festivals.extend(SOLAR_TERM_FESTIVALS)
    if current_config.ENABLE_SPECIAL_DAYS:
        all_festivals.extend(SPECIAL_DAY_FESTIVALS)

    # 加载自定义节日
    custom_festivals = _convert_custom_festivals(
        current_config.CUSTOM_SOLAR_FESTIVALS,
        current_config.CUSTOM_LUNAR_FESTIVALS,
        current_config.CUSTOM_NTH_WEEKDAY_FESTIVALS,
    )
    all_festivals.extend(custom_festivals)

    for festival in all_festivals:
        if festival.name == festival_name:
            trigger_time, year, calendar_type, month, day = FestivalDateCalculator.get_next_festival_date(
                festival,
                current_config.DEFAULT_SEND_HOUR,
                current_config.DEFAULT_SEND_MINUTE,
            )
            if trigger_time > 0:
                await _set_festival_timer(
                    trigger_time=trigger_time,
                    year=year,
                    calendar_type=calendar_type,
                    month=month,
                    day=day,
                    festival_name=festival.name,
                    desc=festival.description,
                )
                logger.info(f"已重新调度节日 {festival_name} 的下一次定时器")
            break


async def _setup_all_festival_timers():
    """设置所有节日的定时器"""
    global _festival_timers
    _festival_timers = []

    current_config: FestivalGreetingConfig = plugin.get_config(FestivalGreetingConfig)

    festivals: List[FestivalConfig] = []

    # 根据配置加载预设节日
    if current_config.ENABLE_CHINESE_TRADITIONAL:
        festivals.extend(CHINESE_TRADITIONAL_FESTIVALS)
        logger.debug(f"加载中国传统节日 {len(CHINESE_TRADITIONAL_FESTIVALS)} 个")

    if current_config.ENABLE_WESTERN_FESTIVALS:
        festivals.extend(WESTERN_FESTIVALS)
        logger.debug(f"加载西方/公历节日 {len(WESTERN_FESTIVALS)} 个")

    if current_config.ENABLE_SOLAR_TERMS:
        festivals.extend(SOLAR_TERM_FESTIVALS)
        logger.debug(f"加载二十四节气 {len(SOLAR_TERM_FESTIVALS)} 个")

    if current_config.ENABLE_SPECIAL_DAYS:
        festivals.extend(SPECIAL_DAY_FESTIVALS)
        logger.debug(f"加载特殊纪念日 {len(SPECIAL_DAY_FESTIVALS)} 个")

    # 加载自定义节日
    custom_festivals = _convert_custom_festivals(
        current_config.CUSTOM_SOLAR_FESTIVALS,
        current_config.CUSTOM_LUNAR_FESTIVALS,
        current_config.CUSTOM_NTH_WEEKDAY_FESTIVALS,
    )
    if custom_festivals:
        festivals.extend(custom_festivals)
        logger.debug(f"加载自定义节日 {len(custom_festivals)} 个")

    # 为每个节日设置定时器
    success_count = 0
    for festival in festivals:
        trigger_time, year, calendar_type, month, day = FestivalDateCalculator.get_next_festival_date(
            festival,
            current_config.DEFAULT_SEND_HOUR,
            current_config.DEFAULT_SEND_MINUTE,
        )

        if trigger_time > 0:
            await _set_festival_timer(
                trigger_time=trigger_time,
                year=year,
                calendar_type=calendar_type,
                month=month,
                day=day,
                festival_name=festival.name,
                desc=festival.description,
            )
            success_count += 1

    logger.info(f"节日祝福插件初始化完成，共设置 {success_count} 个节日定时器")


async def _clear_all_festival_timers():
    """清除所有节日定时器"""
    global _festival_timers

    # 清除节日专用 chat_key 的所有定时器
    await timer_service.set_timer(
        chat_key=FESTIVAL_CHAT_KEY,
        trigger_time=-1,
        event_desc="",
        silent=True,
    )

    _festival_timers = []
    logger.info("已清除所有节日定时器")


@plugin.mount_init_method()
async def init():
    """插件初始化 - 定时器设置由 on_enabled 回调负责，避免重复设置"""
    pass


@plugin.mount_cleanup_method()
async def cleanup():
    """插件清理"""
    await _clear_all_festival_timers()


@plugin.on_enabled()
async def on_enabled():
    """插件启用时重新初始化定时器"""
    await _setup_all_festival_timers()


@plugin.on_disabled()
async def on_disabled():
    """插件禁用时清除所有节日定时器"""
    await _clear_all_festival_timers()
