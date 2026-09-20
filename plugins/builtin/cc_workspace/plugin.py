from typing import Any

from pydantic import Field, model_validator

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
        title="允许 AI 自动创建并绑定工作区",
        description=(
            "仅控制创建：启用后，AI 可通过对话为未绑定的频道自动创建 CC Workspace 并绑定；"
            "禁用时，工作区只能由管理员在工作区管理页面手动创建并绑定"
        ),
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="允许 AI 自动创建并绑定工作区",
                en_US="Allow AI to Auto-create and Bind Workspaces",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="仅控制创建：启用后，AI 可通过对话为未绑定的频道自动创建 CC Workspace 并绑定；禁用时，工作区只能由管理员在工作区管理页面手动创建并绑定",
                en_US="Controls creation only: when enabled, AI can automatically create and bind a CC Workspace for an unbound channel via conversation; when disabled, workspaces can only be created and bound manually by administrators on the workspace management page",
            ),
        ).model_dump(),
    )
    ALLOW_AUTO_START_SANDBOX: bool = Field(
        default=False,
        title="允许 AI 自动唤醒工作区沙盒",
        description=(
            "仅控制唤醒：启用后，AI 可启动已绑定但处于停止状态的沙盒容器（含主程序重启后的重新唤醒）；"
            "禁用时，沙盒只能由管理员在工作区管理页面手动启动"
        ),
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="允许 AI 自动唤醒工作区沙盒",
                en_US="Allow AI to Auto-start Workspace Sandboxes",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="仅控制唤醒：启用后，AI 可启动已绑定但处于停止状态的沙盒容器（含主程序重启后的重新唤醒）；禁用时，沙盒只能由管理员在工作区管理页面手动启动",
                en_US="Controls wake-up only: when enabled, AI can start a bound sandbox that is currently stopped (including re-waking it after a main-process restart); when disabled, sandboxes can only be started manually by administrators on the workspace management page",
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
    MEMORY_SUMMARY_MAX_LENGTH: int = Field(
        default=1200,
        title="记忆摘要最大长度",
        description="CC 工作区记忆摘要（_na_context.md）在 prompt 中展示的最大字符数，超出时会提示 CC 整理摘要",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="记忆摘要最大长度",
                en_US="Memory Summary Max Length",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="CC 工作区记忆摘要在 prompt 中展示的最大字符数，超出时会提示 CC 整理摘要",
                en_US="Maximum characters for CC workspace memory summary in prompts; when exceeded, CC will be prompted to clean up the summary",
            ),
        ).model_dump(),
    )
    CC_DATA_TIMEOUT: float = Field(
        default=300.0,
        title="SSE 数据超时时间（秒）",
        description="CC 执行任务时，若在此时间内未收到任何有效 data: 事件（keep-alive 不计），则主动终止 SSE 流并中止任务",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="SSE 数据超时时间（秒）",
                en_US="SSE Data Timeout (seconds)",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="CC 执行任务时，若在此时间内未收到任何有效 data: 事件（keep-alive 不计），则主动终止 SSE 流并中止任务",
                en_US="When CC is executing a task, if no valid data: event is received within this period (keep-alive excluded), the SSE stream will be terminated and the task aborted",
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

    @model_validator(mode="before")
    @classmethod
    def _inherit_start_sandbox_grant(cls, data: Any) -> Any:
        """旧配置缺少唤醒轴时沿用创建轴，避免升级后静默改变既有授权范围"""
        if not isinstance(data, dict) or "ALLOW_AUTO_START_SANDBOX" in data:
            return data
        create_default = cls.model_fields["ALLOW_AUTO_CREATE_WORKSPACE"].default
        return {**data, "ALLOW_AUTO_START_SANDBOX": data.get("ALLOW_AUTO_CREATE_WORKSPACE", create_default)}


# 获取配置
cc_config: CCWorkspaceConfig = plugin.get_config(CCWorkspaceConfig)
