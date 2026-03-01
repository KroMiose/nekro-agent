from pydantic import Field

from nekro_agent.api import i18n
from nekro_agent.api.plugin import ConfigBase, ExtraField, NekroPlugin

# 创建插件实例
plugin = NekroPlugin(
    name="CC 工作区协作",
    module_name="cc_workspace",
    description="将 CC Sandbox（claude-code）工作区能力接入主 Agent，支持任务委托、文件传递与状态查询",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="CC 工作区协作",
        en_US="CC Workspace Collaboration",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="将 CC Sandbox（claude-code）工作区能力接入主 Agent，支持任务委托、文件传递与状态查询",
        en_US="Integrates CC Sandbox (claude-code) workspace capabilities into the main Agent, supporting task delegation, file transfer and status queries",
    ),
)


@plugin.mount_config()
class CCWorkspaceConfig(ConfigBase):
    """CC 工作区协作插件配置"""

    ALLOW_AUTO_CREATE_WORKSPACE: bool = Field(
        default=False,
        title="允许 AI 自动创建/启动工作区",
        description=(
            "启用后，AI 可通过对话自动创建并启动 CC Workspace；"
            "禁用时，AI 仅能使用已由管理员手动创建并启动的工作区"
        ),
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="允许 AI 自动创建/启动工作区",
                en_US="Allow AI to Auto-create/Start Workspaces",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="启用后，AI 可通过对话自动创建并启动 CC Workspace；禁用时，AI 仅能使用已由管理员手动创建并启动的工作区",
                en_US="When enabled, AI can automatically create and start CC Workspaces via conversation; when disabled, AI can only use workspaces manually created and started by administrators",
            ),
        ).model_dump(),
    )


# 获取配置
cc_config: CCWorkspaceConfig = plugin.get_config(CCWorkspaceConfig)
