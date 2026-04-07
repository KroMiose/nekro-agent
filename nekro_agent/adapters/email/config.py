from contextlib import suppress
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, model_validator

from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField
from nekro_agent.schemas.i18n import i18n_text


class EmailAccount(BaseModel):
    EMAIL_ACCOUNT: str = Field(
        default="QQ邮箱",
        title="邮箱提供商",
        description="填写邮箱提供商：QQ邮箱、163邮箱、Gmail、Outlook、自定义（选择'自定义'时需填写下方自定义服务器配置）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="邮箱提供商", en_US="Email Provider"),
            i18n_description=i18n_text(
                zh_CN="填写邮箱提供商：QQ邮箱、163邮箱、Gmail、Outlook、自定义（选择'自定义'时需填写下方自定义服务器配置）",
                en_US="Select the email provider: QQ Mail, 163 Mail, Gmail, Outlook, or Custom. If Custom is selected, fill in the custom server settings below.",
            ),
        ).model_dump(),
    )
    CUSTOM_IMAP_HOST: str = Field(
        default="",
        title="自定义 IMAP 主机",
        description="仅当邮箱提供商为'自定义'时需要填写，例如 imap.example.com",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="自定义 IMAP 主机", en_US="Custom IMAP Host"),
            i18n_description=i18n_text(
                zh_CN="仅当邮箱提供商为'自定义'时需要填写，例如 imap.example.com",
                en_US="Only required when the email provider is set to Custom, for example imap.example.com.",
            ),
        ).model_dump(),
    )
    CUSTOM_IMAP_PORT: int = Field(
        default=993,
        title="自定义 IMAP 端口",
        description="仅当邮箱提供商为'自定义'时生效，默认 993（SSL）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="自定义 IMAP 端口", en_US="Custom IMAP Port"),
            i18n_description=i18n_text(
                zh_CN="仅当邮箱提供商为'自定义'时生效，默认 993（SSL）",
                en_US="Only takes effect when the email provider is set to Custom. Default is 993 (SSL).",
            ),
        ).model_dump(),
    )
    CUSTOM_SMTP_HOST: str = Field(
        default="",
        title="自定义 SMTP 主机",
        description="仅当邮箱提供商为'自定义'时需要填写，例如 smtp.example.com",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="自定义 SMTP 主机", en_US="Custom SMTP Host"),
            i18n_description=i18n_text(
                zh_CN="仅当邮箱提供商为'自定义'时需要填写，例如 smtp.example.com",
                en_US="Only required when the email provider is set to Custom, for example smtp.example.com.",
            ),
        ).model_dump(),
    )
    CUSTOM_SMTP_PORT: int = Field(
        default=587,
        title="自定义 SMTP 端口",
        description="仅当邮箱提供商为'自定义'时生效，默认 587（STARTTLS）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="自定义 SMTP 端口", en_US="Custom SMTP Port"),
            i18n_description=i18n_text(
                zh_CN="仅当邮箱提供商为'自定义'时生效，默认 587（STARTTLS）",
                en_US="Only takes effect when the email provider is set to Custom. Default is 587 (STARTTLS).",
            ),
        ).model_dump(),
    )
    CUSTOM_SMTP_SSL_PORT: int = Field(
        default=465,
        title="自定义 SMTP SSL 端口",
        description="仅当邮箱提供商为'自定义'时生效，默认 465",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="自定义 SMTP SSL 端口", en_US="Custom SMTP SSL Port"),
            i18n_description=i18n_text(
                zh_CN="仅当邮箱提供商为'自定义'时生效，默认 465",
                en_US="Only takes effect when the email provider is set to Custom. Default is 465.",
            ),
        ).model_dump(),
    )
    CUSTOM_SMTP_USE_SSL: bool = Field(
        default=True,
        title="自定义 SMTP 使用 SSL",
        description="仅当邮箱提供商为'自定义'时生效，是否优先使用 SSL 连接 SMTP",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="自定义 SMTP 使用 SSL", en_US="Use SSL for Custom SMTP"),
            i18n_description=i18n_text(
                zh_CN="仅当邮箱提供商为'自定义'时生效，是否优先使用 SSL 连接 SMTP",
                en_US="Only takes effect when the email provider is set to Custom. Controls whether SSL should be preferred for SMTP connections.",
            ),
        ).model_dump(),
    )
    ENABLED: bool = Field(
        default=True,
        title="启用账户",
        description="是否启用此邮箱账户，设置为否时将跳过连接和轮询",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="启用账户", en_US="Enable Account"),
            i18n_description=i18n_text(
                zh_CN="是否启用此邮箱账户，设置为否时将跳过连接和轮询",
                en_US="Whether to enable this email account. If disabled, connection and polling will be skipped.",
            ),
        ).model_dump(),
    )
    USERNAME: str = Field(
        default="",
        title="邮箱用户名",
        description="填写完整邮箱地址，例如 user@example.com",
        json_schema_extra=ExtraField(
            required=True,
            placeholder="user@example.com",
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="邮箱用户名", en_US="Email Username"),
            i18n_description=i18n_text(
                zh_CN="填写完整邮箱地址，例如 user@example.com",
                en_US="Enter the full email address, for example user@example.com.",
            ),
        ).model_dump(),
    )
    PASSWORD: str = Field(
        default="",
        title="邮箱密码/授权码",
        description="建议使用应用专用密码或 IMAP 授权码（不同服务商名称不同）",
        json_schema_extra=ExtraField(
            required=True,
            is_secret=True,
            placeholder="app-specific password",
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="邮箱密码/授权码", en_US="Email Password / App Password"),
            i18n_description=i18n_text(
                zh_CN="建议使用应用专用密码或 IMAP 授权码（不同服务商名称不同）",
                en_US="It is recommended to use an app-specific password or IMAP authorization code, depending on the provider.",
            ),
        ).model_dump(),
    )
    SEND_ENABLED: bool = Field(
        default=False,
        title="启用发信",
        description="是否允许该邮箱账户用于SMTP发信",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="启用发信", en_US="Enable Sending"),
            i18n_description=i18n_text(
                zh_CN="是否允许该邮箱账户用于SMTP发信",
                en_US="Whether this email account can be used to send mail through SMTP.",
            ),
        ).model_dump(),
    )
    IS_DEFAULT_SENDER: bool = Field(
        default=False,
        title="默认发件人",
        description="设为默认发件人",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="默认发件人", en_US="Default Sender"),
            i18n_description=i18n_text(
                zh_CN="设为默认发件人",
                en_US="Use this account as the default sender.",
            ),
        ).model_dump(),
    )


class EmailConfig(BaseAdapterConfig):
    """Email 适配器配置项说明

    - RECEIVE_ACCOUNTS：用于接收邮件的 IMAP 账户列表
    - POLL_INTERVAL：轮询间隔秒；适当增大可减少服务器压力
    - FETCH_UNSEEN_ONLY：仅拉取未读邮件，避免重复处理
    - MAX_PER_POLL：单次轮询最大抓取数，防止突发大量邮件造成阻塞
    - MARK_AS_SEEN_AFTER_FETCH：读取后标记邮件为已读
    - IMAP_TIMEOUT：IMAP 连接和操作的超时时间
    - SESSION_ENABLE_AT：聊天中的 @ 功能已禁用（邮箱场景不需要）
    - SESSION_PROCESSING_WITH_EMOJI：沿用适配器基类配置，是否生效取决于适配器是否支持
    """

    RECEIVE_ACCOUNTS: List[EmailAccount] = Field(
        default_factory=list,
        title="邮箱账户列表",
        description="用于接收邮件的 IMAP 账户列表（主机、端口、SSL、用户名、密码）",
        json_schema_extra=ExtraField(
            required=True,
            sub_item_name="邮箱账户",
            placeholder="添加你的邮箱账户",
            i18n_category=i18n_text(zh_CN="邮箱账户", en_US="Email Accounts"),
            i18n_title=i18n_text(zh_CN="邮箱账户列表", en_US="Email Account List"),
            i18n_description=i18n_text(
                zh_CN="用于接收邮件的 IMAP 账户列表（主机、端口、SSL、用户名、密码）",
                en_US="List of IMAP accounts used to receive emails, including host, port, SSL, username, and password.",
            ),
        ).model_dump(),
    )
    POLL_INTERVAL: int = Field(
        default=30,
        title="轮询间隔(秒)",
        description="每次轮询之间的等待时长。适当增大可减轻服务器压力",
        json_schema_extra=ExtraField(
            placeholder="30",
            i18n_category=i18n_text(zh_CN="轮询", en_US="Polling"),
            i18n_title=i18n_text(zh_CN="轮询间隔(秒)", en_US="Polling Interval (s)"),
            i18n_description=i18n_text(
                zh_CN="每次轮询之间的等待时长。适当增大可减轻服务器压力",
                en_US="Wait time between polling cycles. Increasing it appropriately can reduce server pressure.",
            ),
        ).model_dump(),
    )
    FETCH_UNSEEN_ONLY: bool = Field(
        default=True,
        title="仅拉取未读",
        description="启用后仅处理未读邮件，避免重复",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="轮询", en_US="Polling"),
            i18n_title=i18n_text(zh_CN="仅拉取未读", en_US="Fetch Unseen Only"),
            i18n_description=i18n_text(
                zh_CN="启用后仅处理未读邮件，避免重复",
                en_US="When enabled, only unseen emails will be processed to avoid duplicates.",
            ),
        ).model_dump(),
    )
    MAX_PER_POLL: int = Field(
        default=50,
        title="每次最大抓取数",
        description="单次轮询最大抓取的邮件数量上限",
        json_schema_extra=ExtraField(
            placeholder="50",
            i18n_category=i18n_text(zh_CN="轮询", en_US="Polling"),
            i18n_title=i18n_text(zh_CN="每次最大抓取数", en_US="Max Emails Per Poll"),
            i18n_description=i18n_text(
                zh_CN="单次轮询最大抓取的邮件数量上限",
                en_US="Maximum number of emails fetched in a single polling cycle.",
            ),
        ).model_dump(),
    )
    MARK_AS_SEEN_AFTER_FETCH: bool = Field(
        default=True,
        title="读取后标记已读",
        description=r"启用后在读取并收集消息后将邮件标记为已读(\Seen)",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="轮询", en_US="Polling"),
            i18n_title=i18n_text(zh_CN="读取后标记已读", en_US="Mark as Seen After Fetch"),
            i18n_description=i18n_text(
                zh_CN=r"启用后在读取并收集消息后将邮件标记为已读(\Seen)",
                en_US=r"When enabled, emails will be marked as seen (\Seen) after they are fetched and collected.",
            ),
        ).model_dump(),
    )
    IMAP_TIMEOUT: int = Field(
        default=60,
        title="IMAP 连接超时(秒)",
        description="IMAP 连接和操作的超时时间，适用于所有邮箱账户",
        json_schema_extra=ExtraField(
            placeholder="60",
            i18n_category=i18n_text(zh_CN="轮询", en_US="Polling"),
            i18n_title=i18n_text(zh_CN="IMAP 连接超时(秒)", en_US="IMAP Timeout (s)"),
            i18n_description=i18n_text(
                zh_CN="IMAP 连接和操作的超时时间，适用于所有邮箱账户",
                en_US="Timeout for IMAP connections and operations, applied to all email accounts.",
            ),
        ).model_dump(),
    )
    EMAIL_NOTIFICATIONS_ENABLED: bool = Field(
        default=False,
        title="启用新邮件通知",
        description="是否在接收到新邮件后自动触发通知和 AI 处理",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通知", en_US="Notifications"),
            i18n_title=i18n_text(zh_CN="启用新邮件通知", en_US="Enable New Email Notifications"),
            i18n_description=i18n_text(
                zh_CN="是否在接收到新邮件后自动触发通知和 AI 处理",
                en_US="Whether to automatically trigger notifications and AI processing when new emails are received.",
            ),
        ).model_dump(),
    )
    EMAIL_NOTIFICATIONS_CHAT_KEY: str = Field(
        default="",
        title="新邮件通知聊天频道",
        description="接收新邮件通知的聊天频道标识（例如 onebot_v11-group_xxx）",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="通知", en_US="Notifications"),
            i18n_title=i18n_text(zh_CN="新邮件通知聊天频道", en_US="New Email Notification Channel"),
            i18n_description=i18n_text(
                zh_CN="接收新邮件通知的聊天频道标识（例如 onebot_v11-group_xxx）",
                en_US="Chat channel key used to receive new email notifications, for example onebot_v11-group_xxx.",
            ),
        ).model_dump(),
    )
    SESSION_ENABLE_AT: bool = Field(
        default=False,
        title="禁用 @ 功能",
        description="邮箱适配器不需要 @ 功能，固定禁用并隐藏",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(zh_CN="兼容", en_US="Compatibility"),
            i18n_title=i18n_text(zh_CN="禁用 @ 功能", en_US="Disable @ Mention"),
            i18n_description=i18n_text(
                zh_CN="邮箱适配器不需要 @ 功能，固定禁用并隐藏",
                en_US="The email adapter does not need @ mention support, so this option is fixed to disabled and hidden.",
            ),
        ).model_dump(),
    )
    @model_validator(mode="after")
    def _validate_mode(self):
        # 不强制报错，允许未配置情况下正常加载配置文件，保持行为不变
        if not isinstance(self.POLL_INTERVAL, int) or self.POLL_INTERVAL <= 0:
            self.POLL_INTERVAL = 30
        if not isinstance(self.MAX_PER_POLL, int) or self.MAX_PER_POLL <= 0:
            self.MAX_PER_POLL = 50
        if not isinstance(self.IMAP_TIMEOUT, int) or self.IMAP_TIMEOUT <= 0:
            self.IMAP_TIMEOUT = 30

        # 互斥校验：最多仅允许一个默认发件人
        def _validate_default_sender() -> None:
            flags = [1 for acc in self.RECEIVE_ACCOUNTS if getattr(acc, "IS_DEFAULT_SENDER", False)]
            if len(flags) > 1:
                raise ValueError("默认发件人只能选择一个：请取消多余的默认标记")

        with suppress(Exception):
            _validate_default_sender()
        return self
