from contextlib import suppress
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, model_validator

from nekro_agent.adapters.interface.base import BaseAdapterConfig, adapter_extra_field


class EmailAccount(BaseModel):
    EMAIL_ACCOUNT: str = Field(
        default="QQ邮箱",
        title="邮箱提供商",
        description="填写邮箱提供商：QQ邮箱、163邮箱、Gmail、Outlook、自定义（选择'自定义'时需填写下方自定义服务器配置）",
        json_schema_extra=adapter_extra_field(
            title_zh="邮箱提供商",
            title_en="Email Provider",
            description_zh="填写邮箱提供商：QQ邮箱、163邮箱、Gmail、Outlook、自定义（选择'自定义'时需填写下方自定义服务器配置）",
            description_en="Select the email provider: QQ Mail, 163 Mail, Gmail, Outlook, or Custom. If Custom is selected, fill in the custom server settings below.",
            category_zh="账户配置",
            category_en="Account Settings",
        ),
    )
    CUSTOM_IMAP_HOST: str = Field(
        default="",
        title="自定义 IMAP 主机",
        description="仅当邮箱提供商为'自定义'时需要填写，例如 imap.example.com",
        json_schema_extra=adapter_extra_field(
            title_zh="自定义 IMAP 主机",
            title_en="Custom IMAP Host",
            description_zh="仅当邮箱提供商为'自定义'时需要填写，例如 imap.example.com",
            description_en="Only required when the email provider is set to Custom, for example imap.example.com.",
            category_zh="账户配置",
            category_en="Account Settings",
        ),
    )
    CUSTOM_IMAP_PORT: int = Field(
        default=993,
        title="自定义 IMAP 端口",
        description="仅当邮箱提供商为'自定义'时生效，默认 993（SSL）",
        json_schema_extra=adapter_extra_field(
            title_zh="自定义 IMAP 端口",
            title_en="Custom IMAP Port",
            description_zh="仅当邮箱提供商为'自定义'时生效，默认 993（SSL）",
            description_en="Only takes effect when the email provider is set to Custom. Default is 993 (SSL).",
            category_zh="账户配置",
            category_en="Account Settings",
        ),
    )
    CUSTOM_SMTP_HOST: str = Field(
        default="",
        title="自定义 SMTP 主机",
        description="仅当邮箱提供商为'自定义'时需要填写，例如 smtp.example.com",
        json_schema_extra=adapter_extra_field(
            title_zh="自定义 SMTP 主机",
            title_en="Custom SMTP Host",
            description_zh="仅当邮箱提供商为'自定义'时需要填写，例如 smtp.example.com",
            description_en="Only required when the email provider is set to Custom, for example smtp.example.com.",
            category_zh="账户配置",
            category_en="Account Settings",
        ),
    )
    CUSTOM_SMTP_PORT: int = Field(
        default=587,
        title="自定义 SMTP 端口",
        description="仅当邮箱提供商为'自定义'时生效，默认 587（STARTTLS）",
        json_schema_extra=adapter_extra_field(
            title_zh="自定义 SMTP 端口",
            title_en="Custom SMTP Port",
            description_zh="仅当邮箱提供商为'自定义'时生效，默认 587（STARTTLS）",
            description_en="Only takes effect when the email provider is set to Custom. Default is 587 (STARTTLS).",
            category_zh="账户配置",
            category_en="Account Settings",
        ),
    )
    CUSTOM_SMTP_SSL_PORT: int = Field(
        default=465,
        title="自定义 SMTP SSL 端口",
        description="仅当邮箱提供商为'自定义'时生效，默认 465",
        json_schema_extra=adapter_extra_field(
            title_zh="自定义 SMTP SSL 端口",
            title_en="Custom SMTP SSL Port",
            description_zh="仅当邮箱提供商为'自定义'时生效，默认 465",
            description_en="Only takes effect when the email provider is set to Custom. Default is 465.",
            category_zh="账户配置",
            category_en="Account Settings",
        ),
    )
    CUSTOM_SMTP_USE_SSL: bool = Field(
        default=True,
        title="自定义 SMTP 使用 SSL",
        description="仅当邮箱提供商为'自定义'时生效，是否优先使用 SSL 连接 SMTP",
        json_schema_extra=adapter_extra_field(
            title_zh="自定义 SMTP 使用 SSL",
            title_en="Use SSL for Custom SMTP",
            description_zh="仅当邮箱提供商为'自定义'时生效，是否优先使用 SSL 连接 SMTP",
            description_en="Only takes effect when the email provider is set to Custom. Controls whether SSL should be preferred for SMTP connections.",
            category_zh="账户配置",
            category_en="Account Settings",
        ),
    )
    ENABLED: bool = Field(
        default=True,
        title="启用账户",
        description="是否启用此邮箱账户，设置为否时将跳过连接和轮询",
        json_schema_extra=adapter_extra_field(
            title_zh="启用账户",
            title_en="Enable Account",
            description_zh="是否启用此邮箱账户，设置为否时将跳过连接和轮询",
            description_en="Whether to enable this email account. If disabled, connection and polling will be skipped.",
            category_zh="账户配置",
            category_en="Account Settings",
        ),
    )
    USERNAME: str = Field(
        default="",
        title="邮箱用户名",
        description="填写完整邮箱地址，例如 user@example.com",
        json_schema_extra=adapter_extra_field(
            title_zh="邮箱用户名",
            title_en="Email Username",
            description_zh="填写完整邮箱地址，例如 user@example.com",
            description_en="Enter the full email address, for example user@example.com.",
            category_zh="账户配置",
            category_en="Account Settings",
            required=True,
            placeholder="user@example.com",
        ),
    )
    PASSWORD: str = Field(
        default="",
        title="邮箱密码/授权码",
        description="建议使用应用专用密码或 IMAP 授权码（不同服务商名称不同）",
        json_schema_extra=adapter_extra_field(
            title_zh="邮箱密码/授权码",
            title_en="Email Password / App Password",
            description_zh="建议使用应用专用密码或 IMAP 授权码（不同服务商名称不同）",
            description_en="It is recommended to use an app-specific password or IMAP authorization code, depending on the provider.",
            category_zh="账户配置",
            category_en="Account Settings",
            required=True,
            is_secret=True,
            placeholder="app-specific password",
        ),
    )
    SEND_ENABLED: bool = Field(
        default=False,
        title="启用发信",
        description="是否允许该邮箱账户用于SMTP发信",
        json_schema_extra=adapter_extra_field(
            title_zh="启用发信",
            title_en="Enable Sending",
            description_zh="是否允许该邮箱账户用于SMTP发信",
            description_en="Whether this email account can be used to send mail through SMTP.",
            category_zh="账户配置",
            category_en="Account Settings",
        ),
    )
    IS_DEFAULT_SENDER: bool = Field(
        default=False,
        title="默认发件人",
        description="设为默认发件人",
        json_schema_extra=adapter_extra_field(
            title_zh="默认发件人",
            title_en="Default Sender",
            description_zh="设为默认发件人",
            description_en="Use this account as the default sender.",
            category_zh="账户配置",
            category_en="Account Settings",
        ),
    )


class EmailConfig(BaseAdapterConfig):
    """Email 适配器配置项说明

    - RECEIVE_ACCOUNTS：用于接收邮件的 IMAP 账户列表
    - POLL_INTERVAL：轮询间隔秒；适当增大可减少服务器压力
    - FETCH_UNSEEN_ONLY：仅拉取未读邮件，避免重复处理
    - MAX_PER_POLL：单次轮询最大抓取数，防止突发大量邮件造成阻塞
    - MARK_AS_SEEN_AFTER_FETCH：读取后标记邮件为已读
    - IMAP_TIMEOUT：IMAP 连接和操作的超时时间
    - SESSION_ENABLE_AT / SESSION_PROCESSING_WITH_EMOJI：聊天相关功能已禁用（只读适配器不需要）
    """

    RECEIVE_ACCOUNTS: List[EmailAccount] = Field(
        default_factory=list,
        title="邮箱账户列表",
        description="用于接收邮件的 IMAP 账户列表（主机、端口、SSL、用户名、密码）",
        json_schema_extra=adapter_extra_field(
            title_zh="邮箱账户列表",
            title_en="Email Account List",
            description_zh="用于接收邮件的 IMAP 账户列表（主机、端口、SSL、用户名、密码）",
            description_en="List of IMAP accounts used to receive emails, including host, port, SSL, username, and password.",
            category_zh="邮箱账户",
            category_en="Email Accounts",
            sub_item_name="邮箱账户",
            placeholder="添加你的邮箱账户",
            required=True,
        ),
    )
    POLL_INTERVAL: int = Field(
        default=30,
        title="轮询间隔(秒)",
        description="每次轮询之间的等待时长。适当增大可减轻服务器压力",
        json_schema_extra=adapter_extra_field(
            title_zh="轮询间隔(秒)",
            title_en="Polling Interval (s)",
            description_zh="每次轮询之间的等待时长。适当增大可减轻服务器压力",
            description_en="Wait time between polling cycles. Increasing it appropriately can reduce server pressure.",
            category_zh="轮询",
            category_en="Polling",
            placeholder="30",
        ),
    )
    FETCH_UNSEEN_ONLY: bool = Field(
        default=True,
        title="仅拉取未读",
        description="启用后仅处理未读邮件，避免重复",
        json_schema_extra=adapter_extra_field(
            title_zh="仅拉取未读",
            title_en="Fetch Unseen Only",
            description_zh="启用后仅处理未读邮件，避免重复",
            description_en="When enabled, only unseen emails will be processed to avoid duplicates.",
            category_zh="轮询",
            category_en="Polling",
        ),
    )
    MAX_PER_POLL: int = Field(
        default=50,
        title="每次最大抓取数",
        description="单次轮询最大抓取的邮件数量上限",
        json_schema_extra=adapter_extra_field(
            title_zh="每次最大抓取数",
            title_en="Max Emails Per Poll",
            description_zh="单次轮询最大抓取的邮件数量上限",
            description_en="Maximum number of emails fetched in a single polling cycle.",
            category_zh="轮询",
            category_en="Polling",
            placeholder="50",
        ),
    )
    MARK_AS_SEEN_AFTER_FETCH: bool = Field(
        default=True,
        title="读取后标记已读",
        description=r"启用后在读取并收集消息后将邮件标记为已读(\Seen)",
        json_schema_extra=adapter_extra_field(
            title_zh="读取后标记已读",
            title_en="Mark as Seen After Fetch",
            description_zh=r"启用后在读取并收集消息后将邮件标记为已读(\Seen)",
            description_en=r"When enabled, emails will be marked as seen (\Seen) after they are fetched and collected.",
            category_zh="轮询",
            category_en="Polling",
        ),
    )
    IMAP_TIMEOUT: int = Field(
        default=60,
        title="IMAP 连接超时(秒)",
        description="IMAP 连接和操作的超时时间，适用于所有邮箱账户",
        json_schema_extra=adapter_extra_field(
            title_zh="IMAP 连接超时(秒)",
            title_en="IMAP Timeout (s)",
            description_zh="IMAP 连接和操作的超时时间，适用于所有邮箱账户",
            description_en="Timeout for IMAP connections and operations, applied to all email accounts.",
            category_zh="轮询",
            category_en="Polling",
            placeholder="60",
        ),
    )
    EMAIL_NOTIFICATIONS_ENABLED: bool = Field(
        default=False,
        title="启用新邮件通知",
        description="是否在接收到新邮件后自动触发通知和 AI 处理",
        json_schema_extra=adapter_extra_field(
            title_zh="启用新邮件通知",
            title_en="Enable New Email Notifications",
            description_zh="是否在接收到新邮件后自动触发通知和 AI 处理",
            description_en="Whether to automatically trigger notifications and AI processing when new emails are received.",
            category_zh="通知",
            category_en="Notifications",
        ),
    )
    EMAIL_NOTIFICATIONS_CHAT_KEY: str = Field(
        default="",
        title="新邮件通知聊天频道",
        description="接收新邮件通知的聊天频道标识（例如 onebot_v11-group_xxx）",
        json_schema_extra=adapter_extra_field(
            title_zh="新邮件通知聊天频道",
            title_en="New Email Notification Channel",
            description_zh="接收新邮件通知的聊天频道标识（例如 onebot_v11-group_xxx）",
            description_en="Chat channel key used to receive new email notifications, for example onebot_v11-group_xxx.",
            category_zh="通知",
            category_en="Notifications",
        ),
    )
    SESSION_ENABLE_AT: bool = Field(
        default=False,
        title="禁用 @ 功能",
        description="邮箱适配器不需要 @ 功能，固定禁用并隐藏",
        json_schema_extra=adapter_extra_field(
            title_zh="禁用 @ 功能",
            title_en="Disable @ Mention",
            description_zh="邮箱适配器不需要 @ 功能，固定禁用并隐藏",
            description_en="The email adapter does not need @ mention support, so this option is fixed to disabled and hidden.",
            category_zh="兼容",
            category_en="Compatibility",
            is_hidden=True,
        ),
    )
    SESSION_PROCESSING_WITH_EMOJI: bool = Field(
        default=False,
        title="禁用处理中表情",
        description="邮箱适配器不需要处理表情反馈，固定禁用并隐藏",
        json_schema_extra=adapter_extra_field(
            title_zh="禁用处理中表情",
            title_en="Disable Processing Emoji Feedback",
            description_zh="邮箱适配器不需要处理表情反馈，固定禁用并隐藏",
            description_en="The email adapter does not need processing emoji feedback, so this option is fixed to disabled and hidden.",
            category_zh="兼容",
            category_en="Compatibility",
            is_hidden=True,
        ),
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
