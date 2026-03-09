from pydantic import Field

from nekro_agent.api import i18n
from nekro_agent.api.plugin import ConfigBase, ExtraField, NekroPlugin

# 创建插件实例
plugin = NekroPlugin(
    name="Claude Code 协作",
    module_name="cc_workspace",
    description="将 CC Sandbox（claude-code）工作区能力接入主 Agent，支持任务委托、文件传递与状态查询",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="Claude Code 协作",
        en_US="Claude Code Collaboration",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="将 CC Sandbox（claude-code）工作区能力接入主 Agent，支持任务委托、文件传递与状态查询",
        en_US="Integrates CC Sandbox (claude-code) workspace capabilities into the main Agent, supporting task delegation, file transfer and status queries",
    ),
    allow_sleep=True,
    sleep_brief="用于将复杂任务委托给 Claude Code (CC) 独立 Agent 工作区，适合编程、文件处理、网络搜索和长流程复杂协作任务。**请在复杂任务中积极启用，而不是试图自行处理！**",
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
    SHARED_DIR_MAX_FILES: int = Field(
        default=10,
        title="共享目录展示文件数量",
        description="在 prompt 中展示的 CC 共享目录（/workspace/default/shared/）最近更新文件数量上限",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="共享目录展示文件数量",
                en_US="Shared Directory Display File Count",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="在 prompt 中展示的 CC 共享目录最近更新文件数量上限",
                en_US="Maximum number of recently updated files to display from the CC shared directory in prompts",
            ),
        ).model_dump(),
    )
    MERGE_CC_AS_SELF: bool = Field(
        default=True,
        title="合并 CC 能力到主人设",
        description=(
            "启用后，AI 将 CC 工作区的能力视为自己的一部分，不向用户暴露 CC Agent 的存在；"
            "禁用时，AI 会以协作模式向用户说明正在委托给 CC Workspace"
        ),
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="合并 CC 能力到主人设",
                en_US="Merge CC Capabilities into Persona",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="启用后，AI 将 CC 工作区的能力视为自己的一部分，不向用户暴露 CC Agent 的存在；禁用时，AI 会以协作模式向用户说明正在委托给 CC Workspace",
                en_US="When enabled, the AI treats CC workspace capabilities as its own and does not reveal CC Agent's existence to users; when disabled, the AI operates in collaboration mode and explains CC delegation to users",
            ),
        ).model_dump(),
    )


# 获取配置
cc_config: CCWorkspaceConfig = plugin.get_config(CCWorkspaceConfig)
