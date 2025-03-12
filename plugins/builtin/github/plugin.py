from nekro_agent.services.plugin.base import ConfigBase, NekroPlugin

# 创建插件实例
plugin = NekroPlugin(
    name="GitHub Webhook插件",
    module_name="github",
    description="接收GitHub webhook消息并处理，支持订阅仓库消息",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
)


@plugin.mount_config()
class GitHubConfig(ConfigBase):
    """GitHub配置"""

    WEBHOOK_SECRET: str = ""  # GitHub webhook的密钥，设置后会进行签名验证


# 获取配置和插件存储
config = plugin.get_config(GitHubConfig)
store = plugin.store
