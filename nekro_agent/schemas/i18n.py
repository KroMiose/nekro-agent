"""国际化基础类型定义

本模块提供国际化(i18n)支持的基础类型和工具函数。

核心设计原则:
1. 使用显式关键字参数，每个语言都有清晰的键名
2. 函数名 `i18n_text` 具有标志性，便于全局搜索
3. 添加新语言时：修改函数签名 → 所有调用点报类型错误 → 逐个补充翻译

使用示例:
    >>> from nekro_agent.schemas.i18n import SupportedLang, i18n_text, get_text
    >>>
    >>> # 创建国际化字典（使用显式关键字参数）
    >>> msg = i18n_text(zh_CN="你好", en_US="Hello")
    >>> # 返回 {"zh-CN": "你好", "en-US": "Hello"}
    >>>
    >>> # 获取指定语言的文本
    >>> get_text(msg, "默认", SupportedLang.EN_US)  # 返回 "Hello"

添加新语言步骤:
    1. 在 SupportedLang 枚举中添加新语言
    2. 在 i18n_text() 函数中添加新的关键字参数
    3. 全局搜索 "i18n_text(" 找到所有调用点
    4. 为每个调用点添加新语言的翻译
"""

from enum import Enum
from typing import Optional, TypeAlias


class SupportedLang(str, Enum):
    """支持的语言枚举

    与前端 i18next 配置保持一致。
    语言代码遵循 BCP 47 标准。

    添加新语言时:
    1. 在此枚举添加新值
    2. 更新 i18n_text() 函数签名
    3. 更新 from_accept_language() 解析逻辑
    """

    ZH_CN = "zh-CN"
    EN_US = "en-US"

    @classmethod
    def from_accept_language(cls, accept_lang: str) -> "SupportedLang":
        """从 Accept-Language 头解析语言

        Args:
            accept_lang: HTTP Accept-Language 头的值

        Returns:
            解析出的语言，默认返回中文
        """
        if not accept_lang:
            return cls.ZH_CN

        # 简单解析，取第一个语言标签
        lang = accept_lang.split(",")[0].strip().lower()

        if lang.startswith("en"):
            return cls.EN_US
        # 默认返回中文
        return cls.ZH_CN


# i18n 字典类型：使用字符串键确保 JSON 序列化兼容性
# 键为语言代码字符串（如 "zh-CN"、"en-US"），与前端 i18next 一致
I18nDict: TypeAlias = dict[str, str]


def get_text(
    i18n_dict: Optional[I18nDict],
    default: str,
    lang: SupportedLang = SupportedLang.ZH_CN,
) -> str:
    """获取国际化文本

    Args:
        i18n_dict: 国际化字典，可为 None
        default: 默认文本（向后兼容，当 i18n_dict 为空或无对应语言时使用）
        lang: 目标语言

    Returns:
        本地化文本，如果无对应翻译则返回默认值

    Example:
        >>> msg = {"zh-CN": "你好", "en-US": "Hello"}
        >>> get_text(msg, "Hi", SupportedLang.EN_US)
        'Hello'
        >>> get_text(None, "Hi", SupportedLang.EN_US)
        'Hi'
    """
    if not i18n_dict:
        return default
    # 使用枚举的字符串值作为键来查找
    return i18n_dict.get(lang.value, default)


def i18n_text(
    *,
    zh_CN: str,
    en_US: str,
) -> I18nDict:
    """创建国际化文本字典

    使用显式关键字参数，确保每个语言都清晰可见。
    函数名具有标志性，便于全局搜索 "i18n_text(" 找到所有使用点。

    键使用语言代码字符串（如 "zh-CN"），确保 JSON 序列化后与前端 i18next 兼容。

    添加新语言时:
    1. 在此函数添加新的关键字参数（如 ja_JP: str）
    2. 在返回字典中添加对应映射
    3. 所有调用点会因缺少必需参数而报类型错误
    4. 逐个为调用点补充新语言翻译

    Args:
        zh_CN: 简体中文文本
        en_US: 美式英文文本

    Returns:
        I18nDict 字典，键为语言代码字符串

    Example:
        >>> i18n_text(zh_CN="你好", en_US="Hello")
        {"zh-CN": "你好", "en-US": "Hello"}
    """
    return {
        SupportedLang.ZH_CN.value: zh_CN,
        SupportedLang.EN_US.value: en_US,
    }
