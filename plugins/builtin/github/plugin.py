from pydantic import Field

from nekro_agent.api import i18n
from nekro_agent.api.plugin import ConfigBase, ExtraField, NekroPlugin

# 创建插件实例
plugin = NekroPlugin(
    name="GitHub 消息推送",
    module_name="github",
    description="接收 GitHub Webhook 消息并处理，支持订阅仓库消息",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="GitHub 消息推送",
        en_US="GitHub Push Notifications",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="接收 GitHub Webhook 消息并处理，支持订阅仓库消息",
        en_US="Receives and processes GitHub Webhook messages with repository subscription support",
    ),
)


@plugin.mount_config()
class GitHubConfig(ConfigBase):
    """GitHub配置"""

    WEBHOOK_SECRET: str = Field(
        default="",
        title="GitHub Webhook 密钥",
        json_schema_extra=ExtraField(
            is_secret=True,
            i18n_title=i18n.i18n_text(
                zh_CN="GitHub Webhook 密钥",
                en_US="GitHub Webhook Secret",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="GitHub Webhook 的密钥，设置后会进行签名验证",
                en_US="GitHub Webhook secret, signature verification will be performed when set",
            ),
        ).model_dump(),
        description="GitHub Webhook 的密钥，设置后会进行签名验证",
    )


# 获取配置和插件存储
config: GitHubConfig = plugin.get_config(GitHubConfig)
store = plugin.store
