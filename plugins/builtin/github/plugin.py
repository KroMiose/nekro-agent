from pydantic import Field

from nekro_agent.api.plugin import ConfigBase, NekroPlugin

# 创建插件实例
plugin = NekroPlugin(
    name="GitHub 消息推送",
    module_name="github",
    description="接收 GitHub Webhook 消息并处理，支持订阅仓库消息",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_config()
class GitHubConfig(ConfigBase):
    """GitHub配置"""

    WEBHOOK_SECRET: str = Field(
        default="",
        title="GitHub Webhook 密钥",
        json_schema_extra={"is_secret": True},
        description="GitHub Webhook 的密钥，设置后会进行签名验证",
    )


# 获取配置和插件存储
config: GitHubConfig = plugin.get_config(GitHubConfig)
store = plugin.store
