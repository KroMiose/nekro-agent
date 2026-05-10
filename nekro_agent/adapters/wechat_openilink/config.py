from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text


class WeChatOpenILinkConfig(BaseAdapterConfig):
    """微信适配器配置（wechatbot-sdk）"""

    BASE_URL: str = Field(
        default="https://ilinkai.weixin.qq.com",
        title="iLink API Base URL",
        description="微信 iLink API 地址",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="WeChatBot", en_US="WeChatBot"),
            i18n_title=i18n_text(zh_CN="API 地址", en_US="API Base URL"),
            i18n_description=i18n_text(
                zh_CN="微信 iLink API 地址",
                en_US="Base URL for WeChat iLink API.",
            ),
        ).model_dump(),
    )

    CRED_PATH: str = Field(
        default="data/nekro_agent/configs/wechat_openilink/credentials.json",
        title="凭据文件路径",
        description="扫码登录后的凭据保存路径（建议使用项目内可持久化目录）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="WeChatBot", en_US="WeChatBot"),
            i18n_title=i18n_text(zh_CN="凭据文件路径", en_US="Credential Path"),
            i18n_description=i18n_text(
                zh_CN="扫码登录后的凭据保存路径（建议使用项目内可持久化目录）",
                en_US="Credential file path for persisted login session (recommend a project-persistent directory).",
            ),
        ).model_dump(),
    )

    LOGIN_TIMEOUT_SECONDS: int = Field(
        default=180,
        title="登录超时",
        description="二维码登录等待超时时间（秒）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="WeChatBot", en_US="WeChatBot"),
            i18n_title=i18n_text(zh_CN="登录超时", en_US="Login Timeout"),
            i18n_description=i18n_text(
                zh_CN="二维码登录等待超时时间（秒）",
                en_US="Timeout in seconds for waiting QR login completion.",
            ),
        ).model_dump(),
    )

    TREAT_PRIVATE_AS_TOME: bool = Field(
        default=True,
        title="私聊默认触发",
        description="私聊消息是否默认视为 @ 机器人并触发 AI",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="交互", en_US="Interaction"),
            i18n_title=i18n_text(zh_CN="私聊默认触发", en_US="Treat Private as To-Me"),
            i18n_description=i18n_text(
                zh_CN="私聊消息是否默认视为 @ 机器人并触发 AI",
                en_US="Whether private messages should be treated as to-me by default.",
            ),
        ).model_dump(),
    )

    GROUP_REQUIRE_MENTION: bool = Field(
        default=True,
        title="群聊仅 @ 触发",
        description="群聊消息仅在识别到 @ 机器人时触发 AI",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="交互", en_US="Interaction"),
            i18n_title=i18n_text(zh_CN="群聊仅 @ 触发", en_US="Group Requires Mention"),
            i18n_description=i18n_text(
                zh_CN="群聊消息仅在识别到 @ 机器人时触发 AI",
                en_US="Only trigger AI in group chats when the bot is mentioned.",
            ),
        ).model_dump(),
    )

    DEDUP_WINDOW_SECONDS: int = Field(
        default=120,
        title="消息去重窗口",
        description="重复消息去重窗口时长（秒）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="WeChatBot", en_US="WeChatBot"),
            i18n_title=i18n_text(zh_CN="消息去重窗口", en_US="Dedup Window"),
            i18n_description=i18n_text(
                zh_CN="重复消息去重窗口时长（秒）",
                en_US="Time window in seconds for inbound message deduplication.",
            ),
        ).model_dump(),
    )
