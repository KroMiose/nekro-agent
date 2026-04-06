from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig, adapter_extra_field


class FeishuConfig(BaseAdapterConfig):
    """飞书适配器配置"""

    APP_ID: str = Field(
        default="",
        title="App ID",
        description="飞书开放平台应用的 App ID，从 <a href='https://open.feishu.cn/app' target='_blank'>飞书开放平台</a> 获取",
        json_schema_extra=adapter_extra_field(
            title_zh="App ID",
            title_en="App ID",
            description_zh="飞书开放平台应用的 App ID，从 <a href='https://open.feishu.cn/app' target='_blank'>飞书开放平台</a> 获取",
            description_en="App ID of your Feishu Open Platform application. Get it from <a href='https://open.feishu.cn/app' target='_blank'>Feishu Open Platform</a>.",
            category_zh="飞书应用",
            category_en="Feishu App",
            required=True,
        ),
    )
    APP_SECRET: str = Field(
        default="",
        title="App Secret",
        description="飞书开放平台应用的 App Secret",
        json_schema_extra=adapter_extra_field(
            title_zh="App Secret",
            title_en="App Secret",
            description_zh="飞书开放平台应用的 App Secret",
            description_en="App Secret of your Feishu Open Platform application.",
            category_zh="飞书应用",
            category_en="Feishu App",
            required=True,
            is_secret=True,
        ),
    )
