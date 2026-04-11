from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text


class FeishuConfig(BaseAdapterConfig):
    """飞书适配器配置"""

    APP_ID: str = Field(
        default="",
        title="App ID",
        description="飞书开放平台应用的 App ID，从 <a href='https://open.feishu.cn/app' target='_blank'>飞书开放平台</a> 获取",
        json_schema_extra=ExtraField(
            required=True,
            i18n_category=i18n_text(zh_CN="飞书应用", en_US="Feishu App"),
            i18n_title=i18n_text(zh_CN="App ID", en_US="App ID"),
            i18n_description=i18n_text(
                zh_CN="飞书开放平台应用的 App ID，从 <a href='https://open.feishu.cn/app' target='_blank'>飞书开放平台</a> 获取",
                en_US="App ID of your Feishu Open Platform application. Get it from <a href='https://open.feishu.cn/app' target='_blank'>Feishu Open Platform</a>.",
            ),
        ).model_dump(),
    )
    APP_SECRET: str = Field(
        default="",
        title="App Secret",
        description="飞书开放平台应用的 App Secret",
        json_schema_extra=ExtraField(
            required=True,
            is_secret=True,
            i18n_category=i18n_text(zh_CN="飞书应用", en_US="Feishu App"),
            i18n_title=i18n_text(zh_CN="App Secret", en_US="App Secret"),
            i18n_description=i18n_text(
                zh_CN="飞书开放平台应用的 App Secret",
                en_US="App Secret of your Feishu Open Platform application.",
            ),
        ).model_dump(),
    )
