from pydantic import Field

from nekro_agent.api import i18n
from nekro_agent.api.plugin import ConfigBase, ExtraField, NekroPlugin

plugin = NekroPlugin(
    name="主动记忆工具",
    module_name="memory_tools",
    description="为主 Agent 提供工作区统一记忆系统的主动检索、详情查看和来源追溯能力",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="主动记忆工具",
        en_US="Active Memory Tools",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="为主 Agent 提供工作区统一记忆系统的主动检索、详情查看和来源追溯能力",
        en_US="Provides active workspace memory search, detail inspection, and origin tracing tools for the main Agent",
    ),
    allow_sleep=True,
    sleep_brief="用于在工作区内主动搜索历史记忆、展开记忆详情和追溯记忆来源，适合处理“之前说过什么”“以前怎么解决过”“历史偏好/决策/经验”这类问题。",
)


@plugin.mount_config()
class MemoryToolsConfig(ConfigBase):
    DEFAULT_SEARCH_LIMIT: int = Field(
        default=6,
        title="主动记忆检索默认条数",
        description="主动调用记忆检索工具时默认返回的结果条数上限",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="主动记忆检索默认条数",
                en_US="Default Active Memory Search Limit",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="主动调用记忆检索工具时默认返回的结果条数上限",
                en_US="Default maximum number of results returned by active memory search tools",
            ),
        ).model_dump(),
    )
memory_tools_config: MemoryToolsConfig = plugin.get_config(MemoryToolsConfig)
