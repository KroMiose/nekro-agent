"""国际化 API

为插件开发者提供国际化相关的工具和类型定义。

Example:
    ```python
    from nekro_agent.api.i18n import i18n_text, I18nDict, SupportedLang
    from nekro_agent.api.plugin import NekroPlugin, ExtraField
    from pydantic import Field

    # 创建国际化文本
    plugin = NekroPlugin(
        name="我的插件",
        module_name="my_plugin",
        description="这是我的插件",
        i18n_name=i18n_text(
            zh_CN="我的插件",
            en_US="My Plugin",
        ),
        i18n_description=i18n_text(
            zh_CN="这是我的插件",
            en_US="This is my plugin",
        ),
        # ...
    )

    # 在配置中使用国际化
    MY_CONFIG: str = Field(
        default="value",
        title="我的配置",
        description="这是配置描述",
        json_schema_extra=ExtraField(
            i18n_title=i18n_text(
                zh_CN="我的配置",
                en_US="My Config",
            ),
            i18n_description=i18n_text(
                zh_CN="这是配置描述",
                en_US="This is config description",
            ),
        ).model_dump(),
    )
    ```
"""

from nekro_agent.schemas.i18n import (
    I18nDict,
    SupportedLang,
    get_text,
    i18n_text,
)

__all__ = [
    "I18nDict",
    "SupportedLang",
    "get_text",
    "i18n_text",
]

