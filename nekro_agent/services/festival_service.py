import asyncio
import random
import time
from datetime import datetime
from datetime import time as dt_time
from typing import List, Tuple

from lunar_python import Lunar

from nekro_agent.core import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.services.message.message_service import message_service
from nekro_agent.services.timer_service import timer_service


class FestivalService:
    """节日提醒服务"""

    FESTIVAL_CHAT_KEY = "system_festival"  # 节日提醒专用的公共 chat_key

    def __init__(self):
        self.initialized = False

    def _get_next_festival_time(self, month: int, day: int, hour: int, minute: int, is_lunar: bool = False) -> Tuple[int, str]:
        """获取下一个节日的时间戳

        Args:
            month (int): 月份
            day (int): 日期
            hour (int): 小时 (24小时制)
            minute (int): 分钟
            is_lunar (bool, optional): 是否为农历. Defaults to False.

        Returns:
            Tuple[int, str]: (时间戳, 年份描述)
        """
        now = datetime.now()
        current_year = now.year

        if is_lunar:
            # 获取今年的节日
            lunar_date = Lunar.fromYmd(current_year, month, day)
            solar_date = lunar_date.getSolar()
            festival_time = datetime.combine(
                datetime(solar_date.getYear(), solar_date.getMonth(), solar_date.getDay()),
                dt_time(hour, minute),
            ).timestamp()

            if festival_time < time.time():
                # 如果今年的节日已过，获取明年的
                lunar_date = Lunar.fromYmd(current_year + 1, month, day)
                solar_date = lunar_date.getSolar()
                festival_time = datetime.combine(
                    datetime(solar_date.getYear(), solar_date.getMonth(), solar_date.getDay()),
                    dt_time(hour, minute),
                ).timestamp()
                return int(festival_time), str(current_year + 1)
            return int(festival_time), str(current_year)

        # 公历节日
        festival_time = datetime.combine(
            datetime(current_year, month, day),
            dt_time(hour, minute),
        ).timestamp()
        if festival_time < time.time():
            festival_time = datetime.combine(
                datetime(current_year + 1, month, day),
                dt_time(hour, minute),
            ).timestamp()
            return int(festival_time), str(current_year + 1)
        return int(festival_time), str(current_year)

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
            channels = await DBChatChannel.filter(is_active=True).all()
            for channel in channels:
                if channel.chat_key != "group_0":
                    await message_service.push_system_message(
                        chat_key=channel.chat_key,
                        agent_messages=event_desc,
                        trigger_agent=True,
                    )
                    await asyncio.sleep(random.randint(1, 120))  # 每个会话间隔随机时间，防止并发过高

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

        # 定义节日列表：(月, 日, 时, 分, 是否农历, 节日名称, 节日说明)
        festivals = [
            # 农历传统节日
            (1, 1, 0, 0, True, "春节", "农历新年第一天，象征着新的开始，是中国最重要的传统节日"),
            (1, 15, 19, 0, True, "元宵节", "农历正月十五，上元节，传统上是赏月、猜灯谜、吃元宵的日子"),
            (3, 3, 10, 0, True, "上巳节", "农历三月三，传统的踏青节，祭祀祈福、郊游赏春"),
            (5, 5, 12, 0, True, "端午节", "农历五月初五，有食粽子、赛龙舟、佩香囊等传统习俗"),
            (7, 7, 19, 30, True, "七夕节", "农历七月初七，牛郎织女相会之日，中国传统的爱情节"),
            (7, 15, 19, 30, True, "中元节", "农历七月十五，也叫鬼节，祭祀祖先、放河灯的日子"),
            (8, 15, 19, 30, True, "中秋节", "农历八月十五，传统的团圆节日，赏月赐福，品尝月饼"),
            (9, 9, 9, 0, True, "重阳节", "农历九月九，登高望远、插茱萸、饮菊花酒的重阳佳节"),
            (12, 8, 8, 0, True, "腊八节", "农历腊月初八，传统喝腊八粥的日子"),
            (12, 23, 23, 30, True, "小年", "农历腊月廿三，祭灶神、大扫除、准备年货的日子"),
            # 公历传统节日
            (1, 1, 0, 0, False, "元旦", "新年第一天，象征着新的开始和希望"),
            (2, 14, 14, 14, False, "情人节", "西方传统的爱情节日，寄托着美好的爱情愿望"),
            (3, 8, 8, 0, False, "妇女节", "国际劳动妇女节，致敬天下女性"),
            (3, 12, 12, 0, False, "植树节", "植树造林、绿化祖国的纪念日"),
            (4, 1, 0, 0, False, "愚人节", "西方传统节日，充满欢乐和趣味的日子"),
            (4, 5, 10, 0, False, "清明节", "传统扫墓祭祖、踏青郊游的节日"),
            (5, 1, 8, 0, False, "劳动节", "国际劳动节，致敬所有劳动者的贡献"),
            (5, 4, 10, 0, False, "青年节", "中国青年奋发图强的纪念日"),
            (6, 1, 8, 30, False, "儿童节", "国际儿童节，关注儿童成长，保护儿童权益"),
            (9, 10, 8, 0, False, "教师节", "尊师重教、感恩师恩的节日"),
            (10, 1, 8, 0, False, "国庆节", "中华人民共和国成立纪念日，举国同庆的日子"),
            (12, 24, 23, 30, False, "平安夜", "西方圣诞节前夜，寄托平安祝福的时刻"),
            (12, 25, 0, 0, False, "圣诞节", "西方传统节日，传递爱与祝福的节日"),
        ]

        # 为每个节日设置定时器
        for month, day, hour, minute, is_lunar, festival_name, desc in festivals:
            trigger_time, year = self._get_next_festival_time(month, day, hour, minute, is_lunar)
            calendar_type = "农历" if is_lunar else "公历"
            await self._set_festival_timer(
                trigger_time=trigger_time,
                year=year,
                calendar_type=calendar_type,
                month=month,
                day=day,
                festival_name=festival_name,
                desc=desc,
            )

        self.initialized = True
        logger.info("Festival service initialized")


# 全局节日提醒服务实例
festival_service = FestivalService()
