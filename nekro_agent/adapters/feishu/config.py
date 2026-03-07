from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig


class FeishuConfig(BaseAdapterConfig):
    """飞书适配器配置"""

    APP_ID: str = Field(
        default="",
        title="App ID",
        description="飞书开放平台应用的 App ID，从 <a href='https://open.feishu.cn/app' target='_blank'>飞书开放平台</a> 获取",
    )
    APP_SECRET: str = Field(
        default="",
        title="App Secret",
        description="飞书开放平台应用的 App Secret",
        json_schema_extra={"is_secret": True},
    )
