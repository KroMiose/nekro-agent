import asyncio
import calendar
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import time as dt_time
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from lunar_python import Lunar

from nekro_agent.core import logger
from nekro_agent.core.config import config
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.services.message_service import message_service
from nekro_agent.services.timer_service import timer_service


class FestivalType(Enum):
    """节日类型枚举"""

    SOLAR = auto()  # 公历固定日期
    LUNAR = auto()  # 农历固定日期
    SPECIAL = auto()  # 特殊计算日期


@dataclass
class FestivalConfig:
    """节日配置"""

    name: str  # 节日名称
    description: str  # 节日说明
    festival_type: FestivalType  # 节日类型
    month: int  # 月份
    day: int = 0  # 日期 (对于特殊节日可能不使用)
    hour: int = 0  # 小时
    minute: int = 0  # 分钟
    special_type: str = ""  # 特殊节日类型标识
    special_params: Dict[str, Any] = field(default_factory=dict)  # 特殊节日参数

    def __post_init__(self):
        """初始化后处理"""
        # 保留做必要的初始化后处理


class FestivalService:
    """节日提醒服务"""

    FESTIVAL_CHAT_KEY = "system_festival"  # 节日提醒专用的公共 chat_key

    def __init__(self):
        self.initialized = False
        self._festival_configs = []
        self._init_festival_configs()

    def _init_festival_configs(self):
        """初始化节日配置列表"""
        # 农历传统节日
        lunar_festivals = [
            FestivalConfig(
                name="春节",
                description="农历新年第一天，象征着新的开始，是中国最重要的传统节日",
                festival_type=FestivalType.LUNAR,
                month=1,
                day=1,
                hour=0,
                minute=0,
            ),
            FestivalConfig(
                name="元宵节",
                description="农历正月十五，上元节，传统上是赏月、猜灯谜、吃元宵的日子",
                festival_type=FestivalType.LUNAR,
                month=1,
                day=15,
                hour=19,
                minute=0,
            ),
            FestivalConfig(
                name="龙抬头",
                description="农历二月初二，传说中龙抬头的日子，有剃龙头、吃春饼等习俗",
                festival_type=FestivalType.LUNAR,
                month=2,
                day=2,
                hour=10,
                minute=0,
            ),
            FestivalConfig(
                name="上巳节",
                description="农历三月三，传统的踏青节，祭祀祈福、郊游赏春",
                festival_type=FestivalType.LUNAR,
                month=3,
                day=3,
                hour=10,
                minute=0,
            ),
            FestivalConfig(
                name="端午节",
                description="农历五月初五，有食粽子、赛龙舟、佩香囊等传统习俗",
                festival_type=FestivalType.LUNAR,
                month=5,
                day=5,
                hour=12,
                minute=0,
            ),
            FestivalConfig(
                name="天贶节",
                description="农历六月初六，也称姑姑节，祈求平安健康的日子",
                festival_type=FestivalType.LUNAR,
                month=6,
                day=6,
                hour=10,
                minute=0,
            ),
            FestivalConfig(
                name="七夕节",
                description="农历七月初七，牛郎织女相会之日，中国传统的爱情节",
                festival_type=FestivalType.LUNAR,
                month=7,
                day=7,
                hour=19,
                minute=30,
            ),
            FestivalConfig(
                name="中元节",
                description="农历七月十五，也叫鬼节，祭祀祖先、放河灯的日子",
                festival_type=FestivalType.LUNAR,
                month=7,
                day=15,
                hour=19,
                minute=30,
            ),
            FestivalConfig(
                name="中秋节",
                description="农历八月十五，传统的团圆节日，赏月赐福，品尝月饼",
                festival_type=FestivalType.LUNAR,
                month=8,
                day=15,
                hour=19,
                minute=30,
            ),
            FestivalConfig(
                name="重阳节",
                description="农历九月九，登高望远、插茱萸、饮菊花酒的重阳佳节",
                festival_type=FestivalType.LUNAR,
                month=9,
                day=9,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="寒衣节",
                description="农历十月初一，为祖先送寒衣的日子",
                festival_type=FestivalType.LUNAR,
                month=10,
                day=1,
                hour=10,
                minute=0,
            ),
            FestivalConfig(
                name="下元节",
                description="农历十月十五，道教三元之下元，祭祀、祈福的日子",
                festival_type=FestivalType.LUNAR,
                month=10,
                day=15,
                hour=19,
                minute=0,
            ),
            FestivalConfig(
                name="腊八节",
                description="农历腊月初八，传统喝腊八粥的日子",
                festival_type=FestivalType.LUNAR,
                month=12,
                day=8,
                hour=8,
                minute=0,
            ),
            FestivalConfig(
                name="小年",
                description="农历腊月廿三，祭灶神、大扫除、准备年货的日子",
                festival_type=FestivalType.LUNAR,
                month=12,
                day=23,
                hour=23,
                minute=30,
            ),
            FestivalConfig(
                name="除夕",
                description="农历年最后一天，辞旧迎新、全家团圆吃年夜饭的日子",
                festival_type=FestivalType.SPECIAL,
                month=12,
                hour=18,
                minute=0,
                special_type="lunar_new_year_eve",
            ),
        ]

        # 公历传统节日
        solar_festivals = [
            FestivalConfig(
                name="元旦",
                description="新年第一天，象征着新的开始和希望",
                festival_type=FestivalType.SOLAR,
                month=1,
                day=1,
                hour=0,
                minute=0,
            ),
            FestivalConfig(
                name="情人节",
                description="西方传统的爱情节日，寄托着美好的爱情愿望",
                festival_type=FestivalType.SOLAR,
                month=2,
                day=14,
                hour=0,
                minute=0,
            ),
            FestivalConfig(
                name="妇女节",
                description="国际劳动妇女节，致敬天下女性",
                festival_type=FestivalType.SOLAR,
                month=3,
                day=8,
                hour=8,
                minute=0,
            ),
            FestivalConfig(
                name="植树节",
                description="植树造林、绿化祖国的纪念日",
                festival_type=FestivalType.SOLAR,
                month=3,
                day=12,
                hour=12,
                minute=0,
            ),
            FestivalConfig(
                name="愚人节",
                description="西方传统节日，充满欢乐和趣味的日子",
                festival_type=FestivalType.SOLAR,
                month=4,
                day=1,
                hour=0,
                minute=0,
            ),
            FestivalConfig(
                name="清明节",
                description="传统扫墓祭祖、踏青郊游的节日",
                festival_type=FestivalType.SOLAR,
                month=4,
                day=5,
                hour=10,
                minute=0,
            ),
            FestivalConfig(
                name="世界地球日",
                description="提高环保意识，保护地球家园的主题日",
                festival_type=FestivalType.SOLAR,
                month=4,
                day=22,
                hour=10,
                minute=0,
            ),
            FestivalConfig(
                name="劳动节",
                description="国际劳动节，致敬所有劳动者的贡献",
                festival_type=FestivalType.SOLAR,
                month=5,
                day=1,
                hour=8,
                minute=0,
            ),
            FestivalConfig(
                name="青年节",
                description="中国青年奋发图强的纪念日",
                festival_type=FestivalType.SOLAR,
                month=5,
                day=4,
                hour=10,
                minute=0,
            ),
            FestivalConfig(
                name="护士节",
                description="国际护士节，致敬白衣天使的贡献",
                festival_type=FestivalType.SOLAR,
                month=5,
                day=12,
                hour=8,
                minute=0,
            ),
            FestivalConfig(
                name="儿童节",
                description="国际儿童节，关注儿童成长，保护儿童权益",
                festival_type=FestivalType.SOLAR,
                month=6,
                day=1,
                hour=8,
                minute=30,
            ),
            FestivalConfig(
                name="音乐节",
                description="国际音乐日，享受音乐的魅力",
                festival_type=FestivalType.SOLAR,
                month=6,
                day=21,
                hour=12,
                minute=0,
            ),
            FestivalConfig(
                name="建军节",
                description="中国人民解放军建军纪念日",
                festival_type=FestivalType.SOLAR,
                month=8,
                day=1,
                hour=8,
                minute=0,
            ),
            FestivalConfig(
                name="教师节",
                description="尊师重教、感恩师恩的节日",
                festival_type=FestivalType.SOLAR,
                month=9,
                day=10,
                hour=8,
                minute=0,
            ),
            FestivalConfig(
                name="国庆节",
                description="中华人民共和国成立纪念日，举国同庆的日子",
                festival_type=FestivalType.SOLAR,
                month=10,
                day=1,
                hour=8,
                minute=0,
            ),
            FestivalConfig(
                name="联合国日",
                description="纪念联合国成立，促进世界和平与发展",
                festival_type=FestivalType.SOLAR,
                month=10,
                day=24,
                hour=10,
                minute=0,
            ),
            FestivalConfig(
                name="万圣节前夜",
                description="西方传统节日，充满神秘色彩的狂欢之夜",
                festival_type=FestivalType.SOLAR,
                month=10,
                day=31,
                hour=18,
                minute=0,
            ),
            FestivalConfig(
                name="光棍节",
                description="起源于中国高校，后成为网络购物节",
                festival_type=FestivalType.SOLAR,
                month=11,
                day=11,
                hour=11,
                minute=11,
            ),
            FestivalConfig(
                name="平安夜",
                description="西方圣诞节前夜，寄托平安祝福的时刻",
                festival_type=FestivalType.SOLAR,
                month=12,
                day=24,
                hour=23,
                minute=30,
            ),
            FestivalConfig(
                name="圣诞节",
                description="西方传统节日，传递爱与祝福的节日",
                festival_type=FestivalType.SOLAR,
                month=12,
                day=25,
                hour=0,
                minute=0,
            ),
        ]

        # 特殊计算节日
        special_festivals = [
            FestivalConfig(
                name="母亲节",
                description="每年5月第二个星期日，感恩母亲、传递亲情的节日",
                festival_type=FestivalType.SPECIAL,
                month=5,
                hour=10,
                minute=0,
                special_type="nth_weekday",
                special_params={"weekday": 6, "nth": 2},
            ),
            FestivalConfig(
                name="父亲节",
                description="每年6月第三个星期日，感恩父亲、传递亲情的节日",
                festival_type=FestivalType.SPECIAL,
                month=6,
                hour=10,
                minute=0,
                special_type="nth_weekday",
                special_params={"weekday": 6, "nth": 3},
            ),
        ]

        # 二十四节气
        solar_terms = [
            FestivalConfig(
                name="立春",
                description="二十四节气之首，春季的开始，万物复苏",
                festival_type=FestivalType.SOLAR,
                month=2,
                day=4,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="雨水",
                description="雨量渐增，雨水滋润大地",
                festival_type=FestivalType.SOLAR,
                month=2,
                day=19,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="惊蛰",
                description="冬眠的昆虫被春雷惊醒，春耕开始",
                festival_type=FestivalType.SOLAR,
                month=3,
                day=6,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="春分",
                description="昼夜平分，阴阳相半",
                festival_type=FestivalType.SOLAR,
                month=3,
                day=21,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="清明",
                description="祭祖扫墓，春光明媚",
                festival_type=FestivalType.SOLAR,
                month=4,
                day=5,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="谷雨",
                description="雨生百谷，播种的好时节",
                festival_type=FestivalType.SOLAR,
                month=4,
                day=20,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="立夏",
                description="夏季的开始，万物繁茂",
                festival_type=FestivalType.SOLAR,
                month=5,
                day=6,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="小满",
                description="麦类等夏熟作物籽粒开始饱满",
                festival_type=FestivalType.SOLAR,
                month=5,
                day=21,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="芒种",
                description="麦类等夏熟农作物成熟，适合播种",
                festival_type=FestivalType.SOLAR,
                month=6,
                day=6,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="夏至",
                description="一年中白昼最长的一天",
                festival_type=FestivalType.SOLAR,
                month=6,
                day=21,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="小暑",
                description="暑气开始，天气炎热",
                festival_type=FestivalType.SOLAR,
                month=7,
                day=7,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="大暑",
                description="一年中最热的时期",
                festival_type=FestivalType.SOLAR,
                month=7,
                day=23,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="立秋",
                description="秋季的开始，暑气渐消",
                festival_type=FestivalType.SOLAR,
                month=8,
                day=8,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="处暑",
                description="暑气结束，天气开始转凉",
                festival_type=FestivalType.SOLAR,
                month=8,
                day=23,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="白露",
                description="天气转凉，露水开始凝结",
                festival_type=FestivalType.SOLAR,
                month=9,
                day=8,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="秋分",
                description="昼夜平分，阴阳相半",
                festival_type=FestivalType.SOLAR,
                month=9,
                day=23,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="寒露",
                description="露水寒冷，将要结冰",
                festival_type=FestivalType.SOLAR,
                month=10,
                day=8,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="霜降",
                description="天气渐冷，开始有霜",
                festival_type=FestivalType.SOLAR,
                month=10,
                day=24,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="立冬",
                description="冬季的开始，万物收藏",
                festival_type=FestivalType.SOLAR,
                month=11,
                day=8,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="小雪",
                description="开始下雪，但雪量较小",
                festival_type=FestivalType.SOLAR,
                month=11,
                day=22,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="大雪",
                description="降雪量大，地面可能积雪",
                festival_type=FestivalType.SOLAR,
                month=12,
                day=7,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="冬至",
                description="一年中白昼最短的一天，阳气开始回升",
                festival_type=FestivalType.SOLAR,
                month=12,
                day=22,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="小寒",
                description="天气寒冷，但尚未到极点",
                festival_type=FestivalType.SOLAR,
                month=1,
                day=6,
                hour=9,
                minute=0,
            ),
            FestivalConfig(
                name="大寒",
                description="一年中最冷的时期",
                festival_type=FestivalType.SOLAR,
                month=1,
                day=20,
                hour=9,
                minute=0,
            ),
        ]

        # 合并所有节日配置
        self._festival_configs = lunar_festivals + solar_festivals + special_festivals + solar_terms

    def _get_nth_weekday_of_month(self, year: int, month: int, weekday: int, nth: int) -> datetime:
        """获取某月第n个星期几的日期

        Args:
            year (int): 年份
            month (int): 月份
            weekday (int): 星期几 (0=星期一, 6=星期日)
            nth (int): 第几个 (1-5)

        Returns:
            datetime: 对应的日期
        """
        # 获取该月第一天
        first_day = datetime(year, month, 1)
        # 计算第一个对应星期几的日期
        target_day = first_day + timedelta(days=(weekday - first_day.weekday()) % 7)
        # 如果第一个目标星期几在该月第一天之前，则加7天
        if target_day.day < first_day.day:
            target_day += timedelta(days=7)
        # 获取第n个目标星期几的日期
        target_day += timedelta(days=7 * (nth - 1))
        return target_day

    def _get_next_festival_date(self, festival: FestivalConfig) -> Tuple[int, str, int, int]:
        """获取下一个节日的时间戳和相关信息

        Args:
            festival (FestivalConfig): 节日配置

        Returns:
            Tuple[int, str, int, int]: (时间戳, 年份描述, 月份, 日期)
        """
        now = datetime.now()
        current_year = now.year

        if festival.festival_type == FestivalType.LUNAR:
            # 农历固定日期节日
            lunar_date = Lunar.fromYmd(current_year, festival.month, festival.day)
            solar_date = lunar_date.getSolar()
            festival_time = datetime.combine(
                datetime(solar_date.getYear(), solar_date.getMonth(), solar_date.getDay()),
                dt_time(festival.hour, festival.minute),
            ).timestamp()

            if festival_time < time.time():
                # 如果今年的节日已过，获取明年的
                lunar_date = Lunar.fromYmd(current_year + 1, festival.month, festival.day)
                solar_date = lunar_date.getSolar()
                festival_time = datetime.combine(
                    datetime(solar_date.getYear(), solar_date.getMonth(), solar_date.getDay()),
                    dt_time(festival.hour, festival.minute),
                ).timestamp()
                return int(festival_time), str(current_year + 1), solar_date.getMonth(), solar_date.getDay()
            return int(festival_time), str(current_year), solar_date.getMonth(), solar_date.getDay()

        if festival.festival_type == FestivalType.SOLAR:
            # 公历固定日期节日
            festival_time = datetime.combine(
                datetime(current_year, festival.month, festival.day),
                dt_time(festival.hour, festival.minute),
            ).timestamp()

            if festival_time < time.time():
                festival_time = datetime.combine(
                    datetime(current_year + 1, festival.month, festival.day),
                    dt_time(festival.hour, festival.minute),
                ).timestamp()
                return int(festival_time), str(current_year + 1), festival.month, festival.day
            return int(festival_time), str(current_year), festival.month, festival.day

        if festival.festival_type == FestivalType.SPECIAL:
            # 特殊计算日期节日
            if festival.special_type == "nth_weekday":
                # 第n个星期几类型的节日
                params = festival.special_params or {}
                weekday = params.get("weekday", 6)  # 默认星期日
                nth = params.get("nth", 1)  # 默认第一个

                target_date = self._get_nth_weekday_of_month(current_year, festival.month, weekday, nth)
                festival_time = datetime.combine(target_date, dt_time(festival.hour, festival.minute)).timestamp()

                if festival_time < time.time():
                    target_date = self._get_nth_weekday_of_month(current_year + 1, festival.month, weekday, nth)
                    festival_time = datetime.combine(target_date, dt_time(festival.hour, festival.minute)).timestamp()
                    return int(festival_time), str(current_year + 1), festival.month, target_date.day
                return int(festival_time), str(current_year), festival.month, target_date.day

            if festival.special_type == "lunar_new_year_eve":
                # 农历除夕
                eve_year, eve_month, eve_day = self._get_lunar_new_year_eve(current_year)
                eve_time = datetime.combine(
                    datetime(eve_year, eve_month, eve_day),
                    dt_time(festival.hour, festival.minute),
                ).timestamp()

                if eve_time < time.time():
                    eve_year, eve_month, eve_day = self._get_lunar_new_year_eve(current_year + 1)
                    eve_time = datetime.combine(
                        datetime(eve_year, eve_month, eve_day),
                        dt_time(festival.hour, festival.minute),
                    ).timestamp()
                    return int(eve_time), str(current_year + 1), eve_month, eve_day
                return int(eve_time), str(current_year), eve_month, eve_day

        # 默认返回
        return 0, "", 0, 0

    def _get_lunar_new_year_eve(self, year: int) -> Tuple[int, int, int]:
        """获取指定年份的农历除夕日期

        Args:
            year (int): 年份

        Returns:
            Tuple[int, int, int]: (年, 月, 日)，返回的是公历日期
        """
        # 获取农历正月初一
        lunar_new_year = Lunar.fromYmd(year, 1, 1)
        solar_new_year = lunar_new_year.getSolar()

        # 农历除夕是农历正月初一的前一天
        new_year_timestamp = datetime(solar_new_year.getYear(), solar_new_year.getMonth(), solar_new_year.getDay()).timestamp()

        # 除夕时间戳 = 春节时间戳 - 1天
        eve_date = datetime.fromtimestamp(new_year_timestamp - 86400)
        return eve_date.year, eve_date.month, eve_date.day

    async def _set_festival_timer(
        self,
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
            trigger_time (int): 触发时间戳
            year (str): 年份
            calendar_type (str): 历法类型
            month (int): 月份
            day (int): 日期
            festival_name (str): 节日名称
            desc (str): 节日说明
        """
        event_desc = (
            f"{year}年{calendar_type}{month}月{day}日{festival_name}。\n"
            f"节日说明：{desc}\n\n"
            "context：这是一个预设的系统节日提醒，请根据节日特点和说明自由发挥，"
            "表达你的祝福，记得加入应景的表情。"
        )

        # 获取所有活跃会话并推送节日祝福
        async def festival_callback():
            # 检查节日祝福是否开启
            if not config.ENABLE_FESTIVAL_REMINDER:
                logger.info(f"节日提醒功能已关闭，跳过 {festival_name} 祝福发送")
                return

            channels = await DBChatChannel.filter(is_active=True).all()
            for channel in channels:
                if channel.chat_key != "group_0":
                    await message_service.push_system_message(
                        chat_key=channel.chat_key,
                        agent_messages=event_desc,
                        trigger_agent=True,
                    )
                    await asyncio.sleep(random.randint(1, 120))  # 每个会话间隔随机时间，防止并发过高

            logger.info(f"节日祝福 {festival_name} 发送完成，共推送至 {len(channels)} 个会话")

        # 设置定时器
        await timer_service.set_timer(
            chat_key=self.FESTIVAL_CHAT_KEY,
            trigger_time=trigger_time,
            event_desc=event_desc,
            silent=True,
            callback=festival_callback,
        )

    async def init_festivals(self):
        """初始化节日提醒"""
        if self.initialized:
            return

        # 为每个节日设置定时器
        for festival in self._festival_configs:
            trigger_time, year, month, day = self._get_next_festival_date(festival)

            if trigger_time > 0:
                calendar_type = "农历" if festival.festival_type == FestivalType.LUNAR else "公历"
                await self._set_festival_timer(
                    trigger_time=trigger_time,
                    year=year,
                    calendar_type=calendar_type,
                    month=month,
                    day=day,
                    festival_name=festival.name,
                    desc=festival.description,
                )

        self.initialized = True
        logger.info("Festival service initialized")


# 全局节日提醒服务实例
festival_service = FestivalService()
