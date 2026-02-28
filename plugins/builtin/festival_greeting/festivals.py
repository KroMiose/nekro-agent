"""节日祝福插件 - 节日定义和日期计算"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import time as dt_time
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

from lunar_python import Lunar

from nekro_agent.core import logger


class FestivalType(Enum):
    """节日类型枚举"""

    SOLAR = auto()  # 公历固定日期
    LUNAR = auto()  # 农历固定日期
    SPECIAL = auto()  # 特殊计算日期（节气、第N个周几等）


class FestivalCategory(Enum):
    """节日分类枚举"""

    CHINESE_TRADITIONAL = "chinese_traditional"  # 中国传统节日
    WESTERN = "western"  # 西方/公历节日
    SOLAR_TERM = "solar_term"  # 二十四节气
    SPECIAL_DAY = "special_day"  # 特殊纪念日
    CUSTOM = "custom"  # 自定义节日


@dataclass
class FestivalConfig:
    """节日配置"""

    name: str  # 节日名称
    description: str  # 节日说明
    festival_type: FestivalType  # 节日类型
    category: FestivalCategory  # 节日分类
    month: int  # 月份
    day: int = 0  # 日期 (对于特殊节日可能不使用)
    hour: Optional[int] = None  # 小时 (None 表示使用默认时间)
    minute: Optional[int] = None  # 分钟 (None 表示使用默认时间)
    special_type: str = ""  # 特殊节日类型标识
    special_params: Dict[str, Any] = field(default_factory=dict)  # 特殊节日参数


# 中国传统农历节日
CHINESE_TRADITIONAL_FESTIVALS: List[FestivalConfig] = [
    FestivalConfig(
        name="春节",
        description="农历新年第一天，象征着新的开始，是中国最重要的传统节日",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=1,
        day=1,
        hour=0,
        minute=0,
    ),
    FestivalConfig(
        name="元宵节",
        description="农历正月十五，上元节，传统上是赏月、猜灯谜、吃元宵的日子",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=1,
        day=15,
        hour=19,
        minute=0,
    ),
    FestivalConfig(
        name="龙抬头",
        description="农历二月初二，传说中龙抬头的日子，有剃龙头、吃春饼等习俗",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=2,
        day=2,
        hour=10,
        minute=0,
    ),
    FestivalConfig(
        name="上巳节",
        description="农历三月三，传统的踏青节，祭祀祈福、郊游赏春",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=3,
        day=3,
        hour=10,
        minute=0,
    ),
    FestivalConfig(
        name="端午节",
        description="农历五月初五，有食粽子、赛龙舟、佩香囊等传统习俗",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=5,
        day=5,
        hour=12,
        minute=0,
    ),
    FestivalConfig(
        name="天贶节",
        description="农历六月初六，也称姑姑节，祈求平安健康的日子",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=6,
        day=6,
        hour=10,
        minute=0,
    ),
    FestivalConfig(
        name="七夕节",
        description="农历七月初七，牛郎织女相会之日，中国传统的爱情节",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=7,
        day=7,
        hour=19,
        minute=30,
    ),
    FestivalConfig(
        name="中元节",
        description="农历七月十五，也叫鬼节，祭祀祖先、放河灯的日子",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=7,
        day=15,
        hour=19,
        minute=30,
    ),
    FestivalConfig(
        name="中秋节",
        description="农历八月十五，传统的团圆节日，赏月赐福，品尝月饼",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=8,
        day=15,
        hour=19,
        minute=30,
    ),
    FestivalConfig(
        name="重阳节",
        description="农历九月九，登高望远、插茱萸、饮菊花酒的重阳佳节",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=9,
        day=9,
        hour=9,
        minute=0,
    ),
    FestivalConfig(
        name="寒衣节",
        description="农历十月初一，为祖先送寒衣的日子",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=10,
        day=1,
        hour=10,
        minute=0,
    ),
    FestivalConfig(
        name="下元节",
        description="农历十月十五，道教三元之下元，祭祀、祈福的日子",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=10,
        day=15,
        hour=19,
        minute=0,
    ),
    FestivalConfig(
        name="腊八节",
        description="农历腊月初八，传统喝腊八粥的日子",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=12,
        day=8,
        hour=8,
        minute=0,
    ),
    FestivalConfig(
        name="小年",
        description="农历腊月廿三，祭灶神、大扫除、准备年货的日子",
        festival_type=FestivalType.LUNAR,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=12,
        day=23,
        hour=23,
        minute=30,
    ),
    FestivalConfig(
        name="除夕",
        description="农历年最后一天，辞旧迎新、全家团圆吃年夜饭的日子",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.CHINESE_TRADITIONAL,
        month=12,
        hour=18,
        minute=0,
        special_type="lunar_new_year_eve",
    ),
]

# 西方/公历节日
WESTERN_FESTIVALS: List[FestivalConfig] = [
    FestivalConfig(
        name="元旦",
        description="新年第一天，象征着新的开始和希望",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=1,
        day=1,
        hour=0,
        minute=0,
    ),
    FestivalConfig(
        name="情人节",
        description="西方传统的爱情节日，寄托着美好的爱情愿望",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=2,
        day=14,
        hour=0,
        minute=0,
    ),
    FestivalConfig(
        name="妇女节",
        description="国际劳动妇女节，致敬天下女性",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=3,
        day=8,
        hour=8,
        minute=0,
    ),
    FestivalConfig(
        name="植树节",
        description="植树造林、绿化祖国的纪念日",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=3,
        day=12,
        hour=12,
        minute=0,
    ),
    FestivalConfig(
        name="愚人节",
        description="西方传统节日，充满欢乐和趣味的日子",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=4,
        day=1,
        hour=0,
        minute=0,
    ),
    FestivalConfig(
        name="世界地球日",
        description="提高环保意识，保护地球家园的主题日",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=4,
        day=22,
        hour=10,
        minute=0,
    ),
    FestivalConfig(
        name="劳动节",
        description="国际劳动节，致敬所有劳动者的贡献",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=5,
        day=1,
        hour=8,
        minute=0,
    ),
    FestivalConfig(
        name="青年节",
        description="中国青年奋发图强的纪念日",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=5,
        day=4,
        hour=10,
        minute=0,
    ),
    FestivalConfig(
        name="护士节",
        description="国际护士节，致敬白衣天使的贡献",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=5,
        day=12,
        hour=8,
        minute=0,
    ),
    FestivalConfig(
        name="儿童节",
        description="国际儿童节，关注儿童成长，保护儿童权益",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=6,
        day=1,
        hour=8,
        minute=30,
    ),
    FestivalConfig(
        name="音乐节",
        description="国际音乐日，享受音乐的魅力",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=6,
        day=21,
        hour=12,
        minute=0,
    ),
    FestivalConfig(
        name="建军节",
        description="中国人民解放军建军纪念日",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=8,
        day=1,
        hour=8,
        minute=0,
    ),
    FestivalConfig(
        name="教师节",
        description="尊师重教、感恩师恩的节日",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=9,
        day=10,
        hour=8,
        minute=0,
    ),
    FestivalConfig(
        name="国庆节",
        description="中华人民共和国成立纪念日，举国同庆的日子",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=10,
        day=1,
        hour=8,
        minute=0,
    ),
    FestivalConfig(
        name="联合国日",
        description="纪念联合国成立，促进世界和平与发展",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=10,
        day=24,
        hour=10,
        minute=0,
    ),
    FestivalConfig(
        name="万圣节前夜",
        description="西方传统节日，充满神秘色彩的狂欢之夜",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=10,
        day=31,
        hour=18,
        minute=0,
    ),
    FestivalConfig(
        name="光棍节",
        description="起源于中国高校，后成为网络购物节",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=11,
        day=11,
        hour=11,
        minute=11,
    ),
    FestivalConfig(
        name="平安夜",
        description="西方圣诞节前夜，寄托平安祝福的时刻",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=12,
        day=24,
        hour=23,
        minute=30,
    ),
    FestivalConfig(
        name="圣诞节",
        description="西方传统节日，传递爱与祝福的节日",
        festival_type=FestivalType.SOLAR,
        category=FestivalCategory.WESTERN,
        month=12,
        day=25,
        hour=0,
        minute=0,
    ),
]

# 二十四节气
SOLAR_TERM_FESTIVALS: List[FestivalConfig] = [
    FestivalConfig(
        name="立春",
        description="二十四节气之首，春季的开始，万物复苏",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="雨水",
        description="雨量渐增，雨水滋润大地",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="惊蛰",
        description="冬眠的昆虫被春雷惊醒，春耕开始",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="春分",
        description="昼夜平分，阴阳相半",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="清明",
        description="祭祖扫墓，春光明媚",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="谷雨",
        description="雨生百谷，播种的好时节",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="立夏",
        description="夏季的开始，万物繁茂",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="小满",
        description="麦类等夏熟作物籽粒开始饱满",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="芒种",
        description="麦类等夏熟农作物成熟，适合播种",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="夏至",
        description="一年中白昼最长的一天",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="小暑",
        description="暑气开始，天气炎热",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="大暑",
        description="一年中最热的时期",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="立秋",
        description="秋季的开始，暑气渐消",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="处暑",
        description="暑气结束，天气开始转凉",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="白露",
        description="天气转凉，露水开始凝结",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="秋分",
        description="昼夜平分，阴阳相半",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="寒露",
        description="露水寒冷，将要结冰",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="霜降",
        description="天气渐冷，开始有霜",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="立冬",
        description="冬季的开始，万物收藏",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="小雪",
        description="开始下雪，但雪量较小",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="大雪",
        description="降雪量大，地面可能积雪",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="冬至",
        description="一年中白昼最短的一天，阳气开始回升",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="小寒",
        description="天气寒冷，但尚未到极点",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
    FestivalConfig(
        name="大寒",
        description="一年中最冷的时期",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SOLAR_TERM,
        month=0,
        special_type="jieqi",
    ),
]

# 特殊纪念日
SPECIAL_DAY_FESTIVALS: List[FestivalConfig] = [
    FestivalConfig(
        name="母亲节",
        description="每年5月第二个星期日，感恩母亲、传递亲情的节日",
        festival_type=FestivalType.SPECIAL,
        category=FestivalCategory.SPECIAL_DAY,
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
        category=FestivalCategory.SPECIAL_DAY,
        month=6,
        hour=10,
        minute=0,
        special_type="nth_weekday",
        special_params={"weekday": 6, "nth": 3},
    ),
]


class FestivalDateCalculator:
    """节日日期计算器"""

    @staticmethod
    def get_nth_weekday_of_month(year: int, month: int, weekday: int, nth: int) -> datetime:
        """获取某月第n个星期几的日期

        Args:
            year (int): 年份
            month (int): 月份
            weekday (int): 星期几 (0=星期一, 6=星期日)
            nth (int): 第几个 (1-5)

        Returns:
            datetime: 对应的日期
        """
        first_day = datetime(year, month, 1)
        target_day = first_day + timedelta(days=(weekday - first_day.weekday()) % 7)
        if target_day.day < first_day.day:
            target_day += timedelta(days=7)
        target_day += timedelta(days=7 * (nth - 1))
        return target_day

    @staticmethod
    def get_lunar_new_year_eve(year: int) -> Tuple[int, int, int]:
        """获取指定年份的农历除夕日期

        Args:
            year (int): 年份

        Returns:
            Tuple[int, int, int]: (年, 月, 日)，返回的是公历日期
        """
        lunar_new_year = Lunar.fromYmd(year, 1, 1)
        solar_new_year = lunar_new_year.getSolar()
        new_year_timestamp = datetime(
            solar_new_year.getYear(),
            solar_new_year.getMonth(),
            solar_new_year.getDay(),
        ).timestamp()
        eve_date = datetime.fromtimestamp(new_year_timestamp - 86400)
        return eve_date.year, eve_date.month, eve_date.day

    @staticmethod
    def get_next_festival_date(
        festival: FestivalConfig,
        default_hour: int = 8,
        default_minute: int = 0,
    ) -> Tuple[int, str, str, int, int]:
        """获取下一个节日的时间戳和相关信息

        Args:
            festival (FestivalConfig): 节日配置
            default_hour (int): 默认发送小时
            default_minute (int): 默认发送分钟

        Returns:
            Tuple[int, str, str, int, int]: (时间戳, 年份, 历法类型, 月份, 日期)
        """
        now = datetime.now()
        current_year = now.year

        # 使用节日配置的时间，如果未指定则使用默认时间
        hour = festival.hour if festival.hour is not None else default_hour
        minute = festival.minute if festival.minute is not None else default_minute

        # 节气计算
        if festival.special_type == "jieqi":
            return FestivalDateCalculator._calculate_jieqi_date(festival, current_year)

        if festival.festival_type == FestivalType.LUNAR:
            return FestivalDateCalculator._calculate_lunar_date(festival, current_year, hour, minute)

        if festival.festival_type == FestivalType.SOLAR:
            return FestivalDateCalculator._calculate_solar_date(festival, current_year, hour, minute)

        if festival.festival_type == FestivalType.SPECIAL:
            return FestivalDateCalculator._calculate_special_date(festival, current_year, hour, minute)

        return 0, "", "", 0, 0

    @staticmethod
    def _calculate_jieqi_date(festival: FestivalConfig, current_year: int) -> Tuple[int, str, str, int, int]:
        """计算节气日期"""
        jq_name = "清明" if festival.name == "清明节" else festival.name

        def _compute_jieqi_time(target_year: int) -> Tuple[int, int, int, int]:
            try:
                table = Lunar.fromYmd(target_year, 1, 1).getJieQiTable()
                solar = table.get(jq_name)
                if solar is None:
                    return 0, 0, 0, 0
                ts = datetime(
                    solar.getYear(),
                    solar.getMonth(),
                    solar.getDay(),
                    solar.getHour(),
                    solar.getMinute(),
                    solar.getSecond(),
                ).timestamp()
                return int(ts), solar.getYear(), solar.getMonth(), solar.getDay()
            except Exception as e:
                logger.error(f"计算节气 {jq_name} 时间失败: {e}")
                return 0, 0, 0, 0

        ts, y, m, d = _compute_jieqi_time(current_year)
        if ts == 0:
            return 0, "", "", 0, 0
        if ts < time.time():
            ts, y, m, d = _compute_jieqi_time(current_year + 1)
            if ts == 0:
                return 0, "", "", 0, 0
            return ts, str(current_year + 1), "节气", m, d
        return ts, str(current_year), "节气", m, d

    @staticmethod
    def _calculate_lunar_date(
        festival: FestivalConfig,
        current_year: int,
        hour: int,
        minute: int,
    ) -> Tuple[int, str, str, int, int]:
        """计算农历节日日期"""
        try:
            lunar_date = Lunar.fromYmd(current_year, festival.month, festival.day)
            solar_date = lunar_date.getSolar()
            festival_time = datetime.combine(
                datetime(solar_date.getYear(), solar_date.getMonth(), solar_date.getDay()),
                dt_time(hour, minute),
            ).timestamp()

            if festival_time < time.time():
                lunar_date = Lunar.fromYmd(current_year + 1, festival.month, festival.day)
                solar_date = lunar_date.getSolar()
                festival_time = datetime.combine(
                    datetime(solar_date.getYear(), solar_date.getMonth(), solar_date.getDay()),
                    dt_time(hour, minute),
                ).timestamp()
                return int(festival_time), str(current_year + 1), "农历", solar_date.getMonth(), solar_date.getDay()
            return int(festival_time), str(current_year), "农历", solar_date.getMonth(), solar_date.getDay()
        except Exception as e:
            logger.error(f"计算农历节日 {festival.name} 日期失败: {e}")
            return 0, "", "", 0, 0

    @staticmethod
    def _calculate_solar_date(
        festival: FestivalConfig,
        current_year: int,
        hour: int,
        minute: int,
    ) -> Tuple[int, str, str, int, int]:
        """计算公历节日日期"""
        try:
            festival_time = datetime.combine(
                datetime(current_year, festival.month, festival.day),
                dt_time(hour, minute),
            ).timestamp()

            if festival_time < time.time():
                festival_time = datetime.combine(
                    datetime(current_year + 1, festival.month, festival.day),
                    dt_time(hour, minute),
                ).timestamp()
                return int(festival_time), str(current_year + 1), "公历", festival.month, festival.day
            return int(festival_time), str(current_year), "公历", festival.month, festival.day
        except Exception as e:
            logger.error(f"计算公历节日 {festival.name} 日期失败: {e}")
            return 0, "", "", 0, 0

    @staticmethod
    def _calculate_special_date(
        festival: FestivalConfig,
        current_year: int,
        hour: int,
        minute: int,
    ) -> Tuple[int, str, str, int, int]:
        """计算特殊节日日期"""
        try:
            if festival.special_type == "nth_weekday":
                params = festival.special_params or {}
                weekday = params.get("weekday", 6)
                nth = params.get("nth", 1)

                target_date = FestivalDateCalculator.get_nth_weekday_of_month(
                    current_year,
                    festival.month,
                    weekday,
                    nth,
                )
                festival_time = datetime.combine(target_date, dt_time(hour, minute)).timestamp()

                if festival_time < time.time():
                    target_date = FestivalDateCalculator.get_nth_weekday_of_month(
                        current_year + 1,
                        festival.month,
                        weekday,
                        nth,
                    )
                    festival_time = datetime.combine(target_date, dt_time(hour, minute)).timestamp()
                    return int(festival_time), str(current_year + 1), "公历", festival.month, target_date.day
                return int(festival_time), str(current_year), "公历", festival.month, target_date.day

            if festival.special_type == "lunar_new_year_eve":
                eve_year, eve_month, eve_day = FestivalDateCalculator.get_lunar_new_year_eve(current_year)
                eve_time = datetime.combine(
                    datetime(eve_year, eve_month, eve_day),
                    dt_time(hour, minute),
                ).timestamp()

                if eve_time < time.time():
                    eve_year, eve_month, eve_day = FestivalDateCalculator.get_lunar_new_year_eve(current_year + 1)
                    eve_time = datetime.combine(
                        datetime(eve_year, eve_month, eve_day),
                        dt_time(hour, minute),
                    ).timestamp()
                    return int(eve_time), str(current_year + 1), "农历", eve_month, eve_day
                return int(eve_time), str(current_year), "农历", eve_month, eve_day
        except Exception as e:
            logger.error(f"计算特殊节日 {festival.name} 日期失败: {e}")

        return 0, "", "", 0, 0
