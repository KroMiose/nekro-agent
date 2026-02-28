"""节日祝福插件 - 插件定义和配置"""

import json
from typing import Any, List

from pydantic import BaseModel, Field, field_validator

from nekro_agent.api import i18n
from nekro_agent.api.plugin import ConfigBase, ExtraField, NekroPlugin

# 创建插件实例
plugin = NekroPlugin(
    name="节日祝福",
    module_name="festival_greeting",
    description="自动在节日时向所有活跃聊天发送祝福",
    version="1.0.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="节日祝福",
        en_US="Festival Greeting",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="自动在节日时向所有活跃聊天发送祝福",
        en_US="Automatically send greetings to all active chats during festivals",
    ),
)


class CustomSolarFestival(BaseModel):
    """自定义公历节日"""

    name: str = Field(
        default="新节日",
        title="节日名称",
        description="节日名称",
    )
    description: str = Field(
        default="",
        title="节日说明",
        description="节日的描述信息",
    )
    month: int = Field(
        default=1,
        ge=1,
        le=12,
        title="月份",
        description="公历月份 (1-12)",
    )
    day: int = Field(
        default=1,
        ge=1,
        le=31,
        title="日期",
        description="公历日期 (1-31)",
    )
    hour: int = Field(
        default=8,
        ge=0,
        le=23,
        title="发送小时",
        description="发送时间-小时 (0-23)",
    )
    minute: int = Field(
        default=0,
        ge=0,
        le=59,
        title="发送分钟",
        description="发送时间-分钟 (0-59)",
    )
    enabled: bool = Field(
        default=True,
        title="启用",
        description="是否启用",
    )


class CustomLunarFestival(BaseModel):
    """自定义农历节日"""

    name: str = Field(
        default="新节日",
        title="节日名称",
        description="节日名称",
    )
    description: str = Field(
        default="",
        title="节日说明",
        description="节日的描述信息",
    )
    month: int = Field(
        default=1,
        ge=1,
        le=12,
        title="农历月份",
        description="农历月份 (1-12)",
    )
    day: int = Field(
        default=1,
        ge=1,
        le=30,
        title="农历日期",
        description="农历日期 (1-30)",
    )
    hour: int = Field(
        default=8,
        ge=0,
        le=23,
        title="发送小时",
        description="发送时间-小时 (0-23)",
    )
    minute: int = Field(
        default=0,
        ge=0,
        le=59,
        title="发送分钟",
        description="发送时间-分钟 (0-59)",
    )
    enabled: bool = Field(
        default=True,
        title="启用",
        description="是否启用",
    )


class CustomNthWeekdayFestival(BaseModel):
    """自定义第N个星期几节日（如母亲节：5月第2个星期日）"""

    name: str = Field(
        default="新节日",
        title="节日名称",
        description="节日名称",
    )
    description: str = Field(
        default="",
        title="节日说明",
        description="节日的描述信息",
    )
    month: int = Field(
        default=1,
        ge=1,
        le=12,
        title="月份",
        description="公历月份 (1-12)",
    )
    nth: int = Field(
        default=1,
        ge=1,
        le=5,
        title="第几个",
        description="第几个星期几 (1-5)",
    )
    weekday: int = Field(
        default=0,
        ge=0,
        le=6,
        title="星期几",
        description="0=周一, 1=周二, ..., 6=周日",
    )
    hour: int = Field(
        default=8,
        ge=0,
        le=23,
        title="发送小时",
        description="发送时间-小时 (0-23)",
    )
    minute: int = Field(
        default=0,
        ge=0,
        le=59,
        title="发送分钟",
        description="发送时间-分钟 (0-59)",
    )
    enabled: bool = Field(
        default=True,
        title="启用",
        description="是否启用",
    )


@plugin.mount_config()
class FestivalGreetingConfig(ConfigBase):
    """节日祝福配置"""

    # 分类开关
    ENABLE_CHINESE_TRADITIONAL: bool = Field(
        default=True,
        title="启用中国传统节日",
        description="中国传统农历节日（春节、元宵、端午、中秋等）",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="启用中国传统节日",
                en_US="Enable Chinese Traditional Festivals",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="中国传统农历节日（春节、元宵、端午、中秋等）",
                en_US="Chinese traditional lunar festivals (Spring Festival, Lantern Festival, Dragon Boat Festival, Mid-Autumn Festival, etc.)",
            ),
        ).model_dump(),
    )

    ENABLE_WESTERN_FESTIVALS: bool = Field(
        default=True,
        title="启用西方/公历节日",
        description="公历节日（元旦、情人节、劳动节、国庆节、圣诞节等）",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="启用西方/公历节日",
                en_US="Enable Western/Solar Festivals",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="公历节日（元旦、情人节、劳动节、国庆节、圣诞节等）",
                en_US="Solar calendar festivals (New Year, Valentine's Day, Labor Day, National Day, Christmas, etc.)",
            ),
        ).model_dump(),
    )

    ENABLE_SOLAR_TERMS: bool = Field(
        default=True,
        title="启用二十四节气",
        description="中国传统二十四节气（立春、春分、清明、夏至、冬至等）",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="启用二十四节气",
                en_US="Enable Solar Terms",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="中国传统二十四节气（立春、春分、清明、夏至、冬至等）",
                en_US="Chinese traditional 24 solar terms (Beginning of Spring, Spring Equinox, Qingming, Summer Solstice, Winter Solstice, etc.)",
            ),
        ).model_dump(),
    )

    ENABLE_SPECIAL_DAYS: bool = Field(
        default=True,
        title="启用特殊纪念日",
        description="特殊纪念日（母亲节、父亲节等）",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="启用特殊纪念日",
                en_US="Enable Special Days",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="特殊纪念日（母亲节、父亲节等）",
                en_US="Special memorial days (Mother's Day, Father's Day, etc.)",
            ),
        ).model_dump(),
    )

    # 默认发送时间
    DEFAULT_SEND_HOUR: int = Field(
        default=8,
        ge=0,
        le=23,
        title="默认发送时间（小时）",
        description="默认的节日祝福发送小时 (0-23)，可被单个节日的时间覆盖",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="默认发送时间（小时）",
                en_US="Default Send Hour",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="默认的节日祝福发送小时 (0-23)，可被单个节日的时间覆盖",
                en_US="Default hour for sending festival greetings (0-23), can be overridden by individual festival settings",
            ),
        ).model_dump(),
    )

    DEFAULT_SEND_MINUTE: int = Field(
        default=0,
        ge=0,
        le=59,
        title="默认发送时间（分钟）",
        description="默认的节日祝福发送分钟 (0-59)，可被单个节日的时间覆盖",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="默认发送时间（分钟）",
                en_US="Default Send Minute",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="默认的节日祝福发送分钟 (0-59)，可被单个节日的时间覆盖",
                en_US="Default minute for sending festival greetings (0-59), can be overridden by individual festival settings",
            ),
        ).model_dump(),
    )

    # 高级设置
    RANDOM_DELAY_MAX: int = Field(
        default=120,
        ge=1,
        le=600,
        title="多频道发送随机延迟最大秒数",
        description="向多个聊天频道发送祝福时的随机延迟上限（秒），防止并发过高",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="多频道发送随机延迟最大秒数",
                en_US="Max Random Delay Between Channels",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="向多个聊天频道发送祝福时的随机延迟上限（秒），防止并发过高",
                en_US="Maximum random delay (seconds) when sending greetings to multiple channels to prevent high concurrency",
            ),
        ).model_dump(),
    )

    # 跳过的聊天频道列表
    SKIP_CHAT_KEYS: List[str] = Field(
        default=[],
        title="跳过的聊天频道",
        description="不发送祝福的聊天频道列表，格式如 group_123456 或 private_789",
        json_schema_extra=ExtraField(
            sub_item_name="频道",
            i18n_title=i18n.i18n_text(
                zh_CN="跳过的聊天频道",
                en_US="Skip Chat Keys",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="不发送祝福的聊天频道列表，格式如 group_123456 或 private_789",
                en_US="List of chat channels to skip, format: group_123456 or private_789",
            ),
        ).model_dump(),
    )

    # 自定义公历节日
    CUSTOM_SOLAR_FESTIVALS: List[CustomSolarFestival] = Field(
        default=[],
        title="自定义公历节日",
        description="自定义的公历固定日期节日，如 5月20日",
        json_schema_extra=ExtraField(
            sub_item_name="公历节日",
            i18n_title=i18n.i18n_text(
                zh_CN="自定义公历节日",
                en_US="Custom Solar Festivals",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="自定义的公历固定日期节日，如 5月20日",
                en_US="Custom solar calendar festivals with fixed dates",
            ),
        ).model_dump(),
    )

    # 自定义农历节日
    CUSTOM_LUNAR_FESTIVALS: List[CustomLunarFestival] = Field(
        default=[],
        title="自定义农历节日",
        description="自定义的农历固定日期节日，如 农历八月十五",
        json_schema_extra=ExtraField(
            sub_item_name="农历节日",
            i18n_title=i18n.i18n_text(
                zh_CN="自定义农历节日",
                en_US="Custom Lunar Festivals",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="自定义的农历固定日期节日，如 农历八月十五",
                en_US="Custom lunar calendar festivals with fixed dates",
            ),
        ).model_dump(),
    )

    # 自定义第N个星期几节日
    CUSTOM_NTH_WEEKDAY_FESTIVALS: List[CustomNthWeekdayFestival] = Field(
        default=[],
        title="自定义第N个星期几节日",
        description="自定义的第N个星期几节日，如 5月第2个星期日（母亲节）",
        json_schema_extra=ExtraField(
            sub_item_name="星期几节日",
            i18n_title=i18n.i18n_text(
                zh_CN="自定义第N个星期几节日",
                en_US="Custom Nth Weekday Festivals",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="自定义的第N个星期几节日，如 5月第2个星期日（母亲节）",
                en_US="Custom nth weekday festivals, e.g., 2nd Sunday of May (Mother's Day)",
            ),
        ).model_dump(),
    )

    @field_validator("SKIP_CHAT_KEYS", mode="before")
    @classmethod
    def validate_skip_chat_keys(cls, v: Any) -> List[str]:
        """兼容旧版字符串格式配置"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            if not v.strip():
                return []
            return [key.strip() for key in v.strip().split("\n") if key.strip()]
        return []

    @field_validator("CUSTOM_SOLAR_FESTIVALS", mode="before")
    @classmethod
    def validate_solar_festivals(cls, v: Any) -> List[CustomSolarFestival]:
        """兼容旧版配置"""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, CustomSolarFestival):
                    result.append(item)
                elif isinstance(item, dict):
                    result.append(CustomSolarFestival(**item))
            return result
        return []

    @field_validator("CUSTOM_LUNAR_FESTIVALS", mode="before")
    @classmethod
    def validate_lunar_festivals(cls, v: Any) -> List[CustomLunarFestival]:
        """兼容旧版配置"""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, CustomLunarFestival):
                    result.append(item)
                elif isinstance(item, dict):
                    result.append(CustomLunarFestival(**item))
            return result
        return []

    @field_validator("CUSTOM_NTH_WEEKDAY_FESTIVALS", mode="before")
    @classmethod
    def validate_nth_weekday_festivals(cls, v: Any) -> List[CustomNthWeekdayFestival]:
        """兼容旧版配置"""
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, CustomNthWeekdayFestival):
                    result.append(item)
                elif isinstance(item, dict):
                    result.append(CustomNthWeekdayFestival(**item))
            return result
        return []


# 获取配置
config: FestivalGreetingConfig = plugin.get_config(FestivalGreetingConfig)
