"""动态头像插件配置"""

from pydantic import Field

from nekro_agent.api import i18n
from nekro_agent.api.plugin import ConfigBase, ExtraField, NekroPlugin

# 创建插件实例
plugin = NekroPlugin(
    name="dynamic_avatar",
    module_name="dynamic_avatar",
    description="动态头像管理，支持情绪切换、指令切换、定时切换",
    version="0.1.0",
    author="KroMiose",
    url="https://github.com/KroMiose/nekro-agent",
    i18n_name=i18n.i18n_text(
        zh_CN="动态头像",
        en_US="Dynamic Avatar",
    ),
    i18n_description=i18n.i18n_text(
        zh_CN="根据情绪或指令自动切换头像",
        en_US="Auto-switch avatar based on emotion or command",
    ),
    allow_sleep=True,
    sleep_brief="动态头像功能休眠",
)


@plugin.mount_config()
class DynamicAvatarConfig(ConfigBase):
    """动态头像配置"""

    ENABLE_DYNAMIC_AVATAR: bool = Field(
        default=True,
        title="启用动态头像",
        description="关闭后将禁用所有头像自动切换功能，仅保留手动切换",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="启用动态头像",
                en_US="Enable Dynamic Avatar",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="关闭后将禁用所有头像自动切换功能",
                en_US="Disable to stop all auto avatar switching",
            ),
        ).model_dump(),
    )

    AUTO_EMOTION_SWITCH: bool = Field(
        default=True,
        title="自动情绪切换",
        description="当 Agent 情绪变化时，自动切换到对应的头像配置",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="自动情绪切换",
                en_US="Auto Emotion Switch",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="当 Agent 情绪变化时，自动切换到对应的头像配置",
                en_US="Auto switch avatar when agent emotion changes",
            ),
        ).model_dump(),
    )

    DEFAULT_AVATAR_NAME: str = Field(
        default="NekroAgent",
        title="默认头像名称",
        description="不使用动态头像时的默认显示名称",
        json_schema_extra=ExtraField(
            i18n_title=i18n.i18n_text(
                zh_CN="默认头像名称",
                en_US="Default Avatar Name",
            ),
            i18n_description=i18n.i18n_text(
                zh_CN="不使用动态头像时的默认显示名称",
                en_US="Default display name when not using dynamic avatar",
            ),
        ).model_dump(),
    )


# 获取配置
config: DynamicAvatarConfig = plugin.get_config(DynamicAvatarConfig)
