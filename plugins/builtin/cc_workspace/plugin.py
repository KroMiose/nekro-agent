from nekro_agent.api import i18n
from nekro_agent.api.plugin import NekroPlugin

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
