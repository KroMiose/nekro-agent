from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text


class WebAdapterConfig(BaseAdapterConfig):
    """网页适配器配置。"""

    ENABLED: bool = Field(
        default=True,
        title="启用网页适配器",
        description="关闭后 WebUI 网页聊天入口不可用，修改后需要重启应用生效",
        json_schema_extra=ExtraField(
            is_need_restart=True,
            i18n_category=i18n_text(zh_CN="基础设置", en_US="Basic Settings"),
            i18n_title=i18n_text(zh_CN="启用网页适配器", en_US="Enable Web Adapter"),
            i18n_description=i18n_text(
                zh_CN="关闭后 WebUI 网页聊天入口不可用，修改后需要重启应用生效",
                en_US="When disabled, the WebUI web chat entry is unavailable. Restart the application after changes.",
            ),
        ).model_dump(),
    )

    MESSAGE_MAX_LENGTH: int = Field(
        default=8000,
        ge=1,
        le=32000,
        title="网页消息最大长度",
        description="单条网页用户文本消息允许的最大字符数",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="消息", en_US="Messages"),
            i18n_title=i18n_text(zh_CN="网页消息最大长度", en_US="Web Message Max Length"),
            i18n_description=i18n_text(
                zh_CN="单条网页用户文本消息允许的最大字符数",
                en_US="Maximum number of characters allowed for a single web user text message.",
            ),
        ).model_dump(),
    )

    FILE_UPLOAD_MAX_SIZE_MB: int = Field(
        default=100,
        ge=1,
        le=512,
        title="网页文件上传大小限制",
        description="单个网页用户上传文件允许的最大大小（MB）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="消息", en_US="Messages"),
            i18n_title=i18n_text(zh_CN="网页文件上传大小限制", en_US="Web File Upload Size Limit"),
            i18n_description=i18n_text(
                zh_CN="单个网页用户上传文件允许的最大大小（MB）",
                en_US="Maximum size in MB allowed for a single web user file upload.",
            ),
        ).model_dump(),
    )

    WEB_USER_NAME_TEMPLATE: str = Field(
        default="web_user_{id}",
        min_length=1,
        max_length=64,
        title="网页用户名称模板",
        description="网页用户显示名称模板，支持 {id} 和 {username} 占位符；渲染为空或 admin 时会回退为 web_user_{id}",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="用户", en_US="User"),
            i18n_title=i18n_text(zh_CN="网页用户名称模板", en_US="Web User Name Template"),
            i18n_description=i18n_text(
                zh_CN="网页用户显示名称模板，支持 {id} 和 {username} 占位符；渲染为空或 admin 时会回退为 web_user_{id}。",
                en_US=(
                    "Display name template for web users. Supports {id} and {username}; "
                    "falls back to web_user_{id} when empty or rendered as admin."
                ),
            ),
        ).model_dump(),
    )

    WEBUI_ADMIN_AS_COMMAND_SUPERUSER: bool = Field(
        default=False,
        title="WebUI 管理员作为命令超级用户",
        description="启用后，Web Chat 中由已登录 WebUI 管理员映射出的网页用户可执行超级用户命令",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="命令", en_US="Commands"),
            i18n_title=i18n_text(
                zh_CN="WebUI 管理员作为命令超级用户",
                en_US="Treat WebUI Admin as Command Superuser",
            ),
            i18n_description=i18n_text(
                zh_CN="启用后，Web Chat 中由已登录 WebUI 管理员映射出的网页用户可执行超级用户命令。",
                en_US=(
                    "When enabled, web users mapped from authenticated WebUI administrators in Web Chat "
                    "can execute superuser commands."
                ),
            ),
        ).model_dump(),
    )
