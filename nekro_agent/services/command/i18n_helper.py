"""命令系统国际化辅助函数

提供命令层翻译快捷函数，供命令 execute() 内部使用。
复用 schemas.i18n 中已有的 i18n_text / get_text 基础设施。
"""

from nekro_agent.schemas.i18n import SupportedLang, get_text, i18n_text


def t(lang: SupportedLang, *, zh_CN: str, en_US: str) -> str:
    """命令层翻译快捷函数

    Args:
        lang: 目标语言
        zh_CN: 简体中文文本
        en_US: 美式英文文本

    Returns:
        对应语言的文本

    Example:
        >>> t(SupportedLang.EN_US, zh_CN="操作成功", en_US="Operation successful")
        'Operation successful'
    """
    return get_text(i18n_text(zh_CN=zh_CN, en_US=en_US), zh_CN, lang)
