from pydantic import Field

from nekro_agent.api import i18n
from nekro_agent.api.plugin import ConfigBase, ExtraField, NekroPlugin

plugin = NekroPlugin(
    name="知识库工具",
    module_name="kb_tools",
    description="为主 Agent 提供工作区知识库搜索、全文读取和源文件获取能力",
    version="0.1.0",
    author="liugu",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="知识库工具",
        en_US="Knowledge Base Tools",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="为主 Agent 提供工作区知识库搜索、全文读取和源文件获取能力",
        en_US="Provides workspace knowledge base search, full-text reading, and source-file access for the main Agent",
    ),
    allow_sleep=True,
    sleep_brief="用于在绑定工作区中搜索手册、规则、FAQ、设计文档等静态知识，并继续读取全文或取出源文件。",
)


@plugin.mount_config()
class KBToolsConfig(ConfigBase):
    DEFAULT_SEARCH_LIMIT: int = Field(
        default=4,
        title="知识库检索默认条数",
        description="主动调用知识库检索工具时默认返回的结果数量上限",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="知识库检索默认条数",
                en_US="Default KB Search Limit",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="主动调用知识库检索工具时默认返回的结果数量上限",
                en_US="Default maximum number of results returned by KB search tools",
            ),
        ).model_dump(),
    )

    DEFAULT_FULLTEXT_MAX_CHARS: int = Field(
        default=18000,
        title="全文读取默认最大字符数",
        description="读取知识库规范化全文时默认返回的最大字符数（硬上限 32000 字符）",
    )

    PROMPT_CATALOG_LIMIT: int = Field(
        default=12,
        title="Prompt 注入知识库目录条数",
        description="每轮向 Agent 运行时上下文注入的知识库基础信息最大条数，仅包含文档元数据摘要，不包含正文",
    )


kb_tools_config: KBToolsConfig = plugin.get_config(KBToolsConfig)
