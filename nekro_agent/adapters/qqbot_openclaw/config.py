from typing import Literal

from pydantic import Field

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text

QQBOT_API_BASE_URL = "https://api.sgroup.qq.com"
QQBOT_TOKEN_BASE_URL = "https://bots.qq.com"
QQBOT_MARKDOWN_ENABLED = True
QQBOT_TEXT_CHUNK_LIMIT = 5000
QQBOT_MEDIA_SIZE_LIMIT_MB = {
    "image": 20,
    "voice": 20,
    "video": 30,
    "file": 100,
}


class QQBotOpenClawConfig(BaseAdapterConfig):
    """QQBot OpenClaw 渠道适配器配置。"""

    SESSION_ENABLE_AT: bool = Field(default=True, json_schema_extra=ExtraField(is_hidden=True).model_dump())
    SESSION_PROCESSING_WITH_EMOJI: bool = Field(default=False, json_schema_extra=ExtraField(is_hidden=True).model_dump())
    COMMAND_ENHANCED_OUTPUT: bool = Field(default=False, json_schema_extra=ExtraField(is_hidden=True).model_dump())
    COMMAND_ENHANCED_OUTPUT_MIN_LENGTH: int = Field(default=200, json_schema_extra=ExtraField(is_hidden=True).model_dump())

    APP_ID: str = Field(
        default="",
        title="App ID",
        description="在 QQ 开放平台 OpenClaw 专用入口创建机器人后获得的 AppID",
        json_schema_extra=ExtraField(
            required=True,
            is_need_restart=True,
            placeholder="例如: 102146862",
            i18n_category=i18n_text(zh_CN="OpenClaw QQBot", en_US="OpenClaw QQBot"),
            i18n_title=i18n_text(zh_CN="机器人 AppID", en_US="Bot AppID"),
            i18n_description=i18n_text(
                zh_CN=(
                    "在“接入维护”页扫码进入 QQ 开放平台 OpenClaw 专用入口并创建机器人后，"
                    "复制页面提供的 AppID。扫码不是 Nekro 本地登录态，运行时仍需要此凭据。"
                ),
                en_US=(
                    "Scan the QR code on the Onboarding tab, create a bot in the QQ Open Platform "
                    "OpenClaw entry, then copy the AppID shown there. The QR scan is not a local "
                    "Nekro login session; this runtime credential is still required."
                ),
            ),
        ).model_dump(),
    )
    CLIENT_SECRET: str = Field(
        default="",
        title="AppSecret",
        description="在 QQ 开放平台 OpenClaw 专用入口创建机器人后获得的 AppSecret",
        json_schema_extra=ExtraField(
            required=True,
            is_secret=True,
            is_need_restart=True,
            placeholder="粘贴创建机器人后显示的 AppSecret",
            i18n_category=i18n_text(zh_CN="OpenClaw QQBot", en_US="OpenClaw QQBot"),
            i18n_title=i18n_text(zh_CN="机器人 AppSecret", en_US="Bot AppSecret"),
            i18n_description=i18n_text(
                zh_CN=(
                    "创建机器人后复制 AppSecret。它用于换取 OpenClaw QQBot Gateway 的 AccessToken；"
                    "离开开放平台页面后可能无法再次明文查看，请妥善保存。"
                ),
                en_US=(
                    "Copy the AppSecret after creating the bot. It is used to obtain the OpenClaw "
                    "QQBot Gateway AccessToken; it may not be shown in plaintext again after leaving "
                    "the platform page."
                ),
            ),
        ).model_dump(),
    )
    GROUP_POLICY: Literal["open", "allowlist", "disabled"] = Field(
        default="open",
        title="群策略",
        description="open 接收所有群；allowlist 仅接收白名单；disabled 禁用群聊",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="群聊策略", en_US="Group Policy"),
            i18n_title=i18n_text(zh_CN="群策略", en_US="Group Policy"),
            i18n_description=i18n_text(
                zh_CN="open 接收所有群；allowlist 仅接收白名单；disabled 禁用群聊。",
                en_US="open accepts all groups; allowlist accepts configured groups only; disabled disables group chat.",
            ),
        ).model_dump(),
    )
    GROUP_ALLOW_FROM: list[str] = Field(
        default_factory=list,
        title="群白名单",
        description="GROUP_POLICY=allowlist 时允许的 group_openid；填 * 表示全部允许",
        json_schema_extra=ExtraField(
            sub_item_name="group_openid",
            i18n_category=i18n_text(zh_CN="群聊策略", en_US="Group Policy"),
            i18n_title=i18n_text(zh_CN="群白名单", en_US="Group Allowlist"),
            i18n_description=i18n_text(
                zh_CN="GROUP_POLICY=allowlist 时允许的 group_openid；填 * 表示全部允许。",
                en_US="Allowed group_openid values when GROUP_POLICY=allowlist. Use * to allow all.",
            ),
        ).model_dump(),
    )
    DEFAULT_REQUIRE_MENTION: bool = Field(
        default=True,
        title="普通群消息默认需要 @",
        description="普通群消息默认只记录上下文，不触发回复；关闭后普通群消息可触发",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="群聊策略", en_US="Group Policy"),
            i18n_title=i18n_text(zh_CN="普通群消息默认需要 @", en_US="Require Mention by Default"),
            i18n_description=i18n_text(
                zh_CN="普通群消息默认只记录上下文，不触发回复；关闭后普通群消息可触发。",
                en_US="Normal group messages are collected without triggering by default; disable to let them trigger.",
            ),
        ).model_dump(),
    )
    IGNORE_OTHER_MENTIONS: bool = Field(
        default=False,
        title="忽略只 @ 其他人的群消息",
        description="当群消息包含 @ 但没有 @ 本机器人时，是否忽略触发",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(zh_CN="群聊策略", en_US="Group Policy"),
            i18n_title=i18n_text(zh_CN="忽略只 @ 其他人的群消息", en_US="Ignore Other Mentions"),
            i18n_description=i18n_text(
                zh_CN="当群消息包含 @ 但没有 @ 本机器人时，是否忽略触发。",
                en_US="Ignore trigger when a group message mentions others but not this bot.",
            ),
        ).model_dump(),
    )
    GROUP_HISTORY_LIMIT: int = Field(
        default=50,
        ge=0,
        le=500,
        title="群上下文记录上限",
        description="跟随 OpenClaw 默认的群历史上下文记录上限",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(zh_CN="群聊策略", en_US="Group Policy"),
            i18n_title=i18n_text(zh_CN="群上下文记录上限", en_US="Group History Limit"),
            i18n_description=i18n_text(
                zh_CN="跟随 OpenClaw 默认的群历史上下文记录上限。",
                en_US="OpenClaw-style group history collection limit.",
            ),
        ).model_dump(),
    )
    PROACTIVE_SEND_ENABLED: bool = Field(
        default=True,
        title="允许主动发送",
        description="没有最近入站消息或引用消息时仍尝试主动发送；失败会记录并返回给调用方",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="发送", en_US="Sending"),
            i18n_title=i18n_text(zh_CN="允许主动发送", en_US="Allow Proactive Sending"),
            i18n_description=i18n_text(
                zh_CN="没有最近入站消息或引用消息时仍尝试主动发送；失败会记录并返回给调用方。",
                en_US="Try proactive sends when no recent inbound/ref message exists; failures are logged and returned.",
            ),
        ).model_dump(),
    )
