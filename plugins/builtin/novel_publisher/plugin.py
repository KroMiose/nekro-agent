"""小说自动发布插件 - 插件定义和配置

支持 AI 生成原创小说内容，可按配置周期自动发布到指定群聊，并保存已生成的小说避免重复。
"""

from typing import Any, List

from pydantic import Field, field_validator

from nekro_agent.api import i18n
from nekro_agent.api.plugin import ConfigBase, ExtraField, NekroPlugin

plugin = NekroPlugin(
    name="小说自动发布",
    module_name="novel_publisher",
    description="调用 AI 自动生成原创小说，支持定时发布到指定群聊并保存历史",
    version="1.0.0",
    author="NekroMeow",
    url="https://github.com/NekroMeow/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="小说自动发布",
        en_US="Novel Auto Publisher",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="调用 AI 自动生成原创小说，支持定时发布到指定群聊并保存历史",
        en_US="Auto-generate original novels via AI, with scheduled publishing to target chats",
    ),
    sleep_brief="用于自动生成和发布原创小说内容，在涉及小说创作、定时发布等场景时激活。",
)


@plugin.mount_config()
class NovelPublishConfig(ConfigBase):
    """小说发布插件配置"""

    ENABLE_AUTO_PUBLISH: bool = Field(
        default=False,
        title="启用自动发布",
        description="开启后，将按照设定的 Cron 周期自动生成并发布小说",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(zh_CN="启用自动发布", en_US="Enable Auto Publish"),
            i18n_description=i18n.i18n_text(
                zh_CN="开启后，将按照设定的 Cron 周期自动生成并发布小说",
                en_US="When enabled, novels will be auto-generated and published on the configured cron schedule",
            ),
        ).model_dump(),
    )

    TARGET_CHAT_KEYS: List[str] = Field(
        default=[],
        title="目标群聊列表",
        description="小说将自动发布到这些群聊，格式如 group_123456",
        json_schema_extra=ExtraField(
            sub_item_name="群聊",
            i18n_title=i18n.i18n_text(zh_CN="目标群聊列表", en_US="Target Chat List"),
            i18n_description=i18n.i18n_text(
                zh_CN="小说将自动发布到这些群聊，格式如 group_123456",
                en_US="Novels will be published to these chats, e.g. group_123456",
            ),
        ).model_dump(),
    )

    PUBLISH_CRON: str = Field(
        default="0 9 * * *",
        title="发布周期 (Cron)",
        description="Cron 表达式，默认每天 9:00 发布。格式：分 时 日 月 周",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(zh_CN="发布周期 (Cron)", en_US="Publish Cron"),
            i18n_description=i18n.i18n_text(
                zh_CN="Cron 表达式，默认每天 9:00 发布。格式：分 时 日 月 周",
                en_US="Cron expression, default 9:00 daily. Format: min hour day month dow",
            ),
        ).model_dump(),
    )

    DEFAULT_THEME: str = Field(
        default="奇幻冒险",
        title="默认小说主题",
        description="自动生成小说时使用的默认主题",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(zh_CN="默认小说主题", en_US="Default Novel Theme"),
            i18n_description=i18n.i18n_text(
                zh_CN="自动生成小说时使用的默认主题",
                en_US="Default theme used for auto-generated novels",
            ),
        ).model_dump(),
    )

    DEFAULT_STYLE: str = Field(
        default="轻松幽默",
        title="默认写作风格",
        description="自动生成小说时使用的默认写作风格",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(zh_CN="默认写作风格", en_US="Default Writing Style"),
            i18n_description=i18n.i18n_text(
                zh_CN="自动生成小说时使用的默认写作风格",
                en_US="Default writing style used for auto-generated novels",
            ),
        ).model_dump(),
    )

    DEFAULT_WORD_COUNT: int = Field(
        default=800,
        ge=100,
        le=5000,
        title="默认字数要求",
        description="自动生成小说时的目标字数（100-5000）",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(zh_CN="默认字数要求", en_US="Default Word Count"),
            i18n_description=i18n.i18n_text(
                zh_CN="自动生成小说时的目标字数（100-5000）",
                en_US="Target word count for auto-generated novels (100-5000)",
            ),
        ).model_dump(),
    )

    MODEL_GROUP: str = Field(
        default="default",
        title="模型组",
        description="用于生成小说的 AI 模型组名称",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(zh_CN="模型组", en_US="Model Group"),
            i18n_description=i18n.i18n_text(
                zh_CN="用于生成小说的 AI 模型组名称",
                en_US="AI model group name for novel generation",
            ),
        ).model_dump(),
    )

    RANDOM_DELAY_MAX: int = Field(
        default=60,
        ge=0,
        le=600,
        title="多群聊发布随机延迟最大秒数",
        description="向多个群聊发布时的随机延迟上限（秒），防止并发过高",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(zh_CN="多群聊发布随机延迟最大秒数", en_US="Max Random Delay Between Chats"),
            i18n_description=i18n.i18n_text(
                zh_CN="向多个群聊发布时的随机延迟上限（秒），防止并发过高",
                en_US="Max random delay (seconds) when publishing to multiple chats",
            ),
        ).model_dump(),
    )

    @field_validator("TARGET_CHAT_KEYS", mode="before")
    @classmethod
    def validate_chat_keys(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            if not v.strip():
                return []
            return [key.strip() for key in v.strip().split("\n") if key.strip()]
        return []


config = plugin.get_config(NovelPublishConfig)
