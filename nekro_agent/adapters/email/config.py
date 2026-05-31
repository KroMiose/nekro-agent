from contextlib import suppress
from typing import Any, Dict, List, Literal, Optional

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
    RECEIVE_ENABLED: bool = Field(
        default=True,
        title="启用收信",
        description="是否允许此邮箱账户建立 IMAP 连接并接收邮件；关闭后仍可仅用于发信",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="账户配置", en_US="Account Settings"),
            i18n_title=i18n_text(zh_CN="启用收信", en_US="Enable Receiving"),
            i18n_description=i18n_text(
                zh_CN="是否允许此邮箱账户建立 IMAP 连接并接收邮件；关闭后仍可仅用于发信",
                en_US="Whether this account can connect via IMAP and receive emails. When disabled, it can still be used for sending only.",
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
    AUTH_TYPE: Literal["password", "oauth2"] = Field(default="password", title="认证方式")
    TRANSPORT_TYPE: Literal["imap_smtp", "gmail_api", "microsoft_graph"] = Field(default="imap_smtp", title="收发信方式")
    OAUTH_PROVIDER: Literal["", "google", "microsoft"] = Field(default="", title="OAuth 提供商")
    CLIENT_ID: str = Field(default="", title="OAuth Client ID")
    CLIENT_SECRET: str = Field(default="", title="OAuth Client Secret")
    TENANT_ID: str = Field(default="common", title="Microsoft Tenant ID")
    ACCESS_TOKEN: str = Field(default="", title="OAuth Access Token")
    REFRESH_TOKEN: str = Field(default="", title="OAuth Refresh Token")
    TOKEN_EXPIRES_AT: int = Field(default=0, title="OAuth Token 过期时间戳")
    LAST_TEST_SUCCESS: Optional[bool] = Field(default=None, title="最近一次连接测试是否成功")
    LAST_TEST_MESSAGE: str = Field(default="", title="最近一次连接测试消息")
    LAST_TEST_TIME: int = Field(default=0, title="最近一次连接测试时间戳")
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


class StatusMailRecipient(BaseModel):
    EMAIL: str = Field(
        default="",
        title="目标邮箱",
        description="接收运行状态通知的邮箱地址",
        json_schema_extra=ExtraField(
            required=True,
            placeholder="target@example.com",
            i18n_category=i18n_text(zh_CN="邮件通知", en_US="Runtime Email Notification"),
            i18n_title=i18n_text(zh_CN="目标邮箱", en_US="Target Email"),
            i18n_description=i18n_text(
                zh_CN="接收运行状态通知的邮箱地址",
                en_US="Email address that receives runtime status notifications.",
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
    - SESSION_PROCESSING_WITH_EMOJI：邮箱不支持消息 reaction，固定隐藏
    - COMMAND_*：邮箱场景不使用命令系统，固定隐藏并禁用
    """

    RECEIVE_ACCOUNTS: List[EmailAccount] = Field(
        default_factory=list,
        title="邮箱账户列表",
        description="邮箱账户列表，请在 Email 适配器的账户管理页面维护",
        json_schema_extra=ExtraField(
            is_hidden=True,
            sub_item_name="邮箱账户",
            placeholder="请在 Email 适配器的账户管理页面添加邮箱账户",
            i18n_category=i18n_text(zh_CN="邮箱账户", en_US="Email Accounts"),
            i18n_title=i18n_text(zh_CN="邮箱账户列表", en_US="Email Account List"),
            i18n_description=i18n_text(
                zh_CN="邮箱账户列表，请在 Email 适配器的账户管理页面维护。",
                en_US="Email account list. Manage these accounts on the Email adapter account page.",
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
    OAUTH_PROXY: str = Field(
        default="",
        title="国外邮箱登录代理",
        description="用于 Gmail/Outlook 官方登录、授权回调与 Token 刷新的代理地址，例如 http://127.0.0.1:7890。留空则不使用代理",
        json_schema_extra=ExtraField(
            placeholder="http://127.0.0.1:7890",
            i18n_category=i18n_text(zh_CN="邮箱登录", en_US="Email Login"),
            i18n_title=i18n_text(zh_CN="国外邮箱登录代理", en_US="OAuth Proxy"),
            i18n_description=i18n_text(
                zh_CN="用于 Gmail/Outlook 官方登录、授权回调与 Token 刷新的代理地址，例如 http://127.0.0.1:7890。留空则不使用代理。",
                en_US="Proxy URL used for Gmail/Outlook official login, OAuth callback, and token refresh, for example http://127.0.0.1:7890. Leave empty to disable proxy.",
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
    STATUS_MAIL_ENABLED: bool = Field(
        default=False,
        title="启用运行状态邮件通知",
        description="启用后 Bot 上下线时会通过邮件发送通知",
        json_schema_extra=ExtraField(
            i18n_category=i18n_text(zh_CN="邮件通知", en_US="Runtime Email Notification"),
            i18n_title=i18n_text(zh_CN="启用运行状态邮件通知", en_US="Enable Runtime Status Email Notification"),
            i18n_description=i18n_text(
                zh_CN="启用后 Bot 上下线时会通过邮件发送通知",
                en_US="Send email notifications when the bot goes online or offline.",
            ),
        ).model_dump(),
    )
    STATUS_MAIL_SENDER_ACCOUNT: str = Field(
        default="",
        title="通知发信账户",
        description="从邮箱账户列表中选择一个启用了发信的账户，用于发送运行状态通知",
        json_schema_extra=ExtraField(
            ref_email_accounts_send_enabled=True,
            placeholder="user@example.com",
            i18n_category=i18n_text(zh_CN="邮件通知", en_US="Runtime Email Notification"),
            i18n_title=i18n_text(zh_CN="通知发信账户", en_US="Notification Sender Account"),
            i18n_description=i18n_text(
                zh_CN="从邮箱账户列表中选择一个启用了发信的账户，用于发送运行状态通知",
                en_US="Select a send-enabled account from the email account list to send runtime status notifications.",
            ),
        ).model_dump(),
    )
    STATUS_MAIL_TARGETS: List[StatusMailRecipient] = Field(
        default_factory=list,
        title="通知目标邮箱列表",
        description="接收运行状态通知的邮箱列表；为空时默认发送给发件邮箱自身",
        json_schema_extra=ExtraField(
            sub_item_name="目标邮箱",
            i18n_category=i18n_text(zh_CN="邮件通知", en_US="Runtime Email Notification"),
            i18n_title=i18n_text(zh_CN="通知目标邮箱列表", en_US="Notification Target Email List"),
            i18n_description=i18n_text(
                zh_CN="接收运行状态通知的邮箱列表；为空时默认发送给发件邮箱自身",
                en_US="Target email list for runtime notifications. If empty, the sender mailbox itself will be used.",
            ),
        ).model_dump(),
    )
    STATUS_MAIL_MIGRATED: bool = Field(
        default=False,
        title="运行状态邮件通知迁移完成标记",
        description="内部迁移状态标记，用于防止旧全局邮件通知配置重复迁移",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(zh_CN="兼容", en_US="Compatibility"),
            i18n_title=i18n_text(zh_CN="运行状态邮件通知迁移完成标记", en_US="Runtime Mail Migration Completed"),
            i18n_description=i18n_text(
                zh_CN="内部迁移状态标记，用于防止旧全局邮件通知配置重复迁移",
                en_US="Internal migration state flag used to prevent repeated migration of legacy runtime mail settings.",
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
    SESSION_PROCESSING_WITH_EMOJI: bool = Field(
        default=False,
        title="显示处理中表情反馈",
        description="邮箱适配器不支持消息 reaction，固定禁用并隐藏",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(zh_CN="交互", en_US="Interaction"),
            i18n_title=i18n_text(zh_CN="显示处理中表情反馈", en_US="Show Processing Emoji Feedback"),
            i18n_description=i18n_text(
                zh_CN="邮箱适配器不支持消息 reaction，固定禁用并隐藏",
                en_US="The email adapter does not support message reactions, so this option is fixed to disabled and hidden.",
            ),
        ).model_dump(),
    )
    COMMAND_PREFIX: str = Field(
        default="/",
        title="命令前缀",
        description="邮箱适配器不使用命令系统，固定隐藏",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(zh_CN="命令", en_US="Commands"),
            i18n_title=i18n_text(zh_CN="命令前缀", en_US="Command Prefix"),
            i18n_description=i18n_text(
                zh_CN="邮箱适配器不使用命令系统，固定隐藏",
                en_US="The email adapter does not use the command system, so this option is fixed to hidden.",
            ),
        ).model_dump(),
    )
    COMMAND_ENABLED: bool = Field(
        default=False,
        title="启用命令系统",
        description="邮箱适配器不使用命令系统，固定禁用并隐藏",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(zh_CN="命令", en_US="Commands"),
            i18n_title=i18n_text(zh_CN="启用命令系统", en_US="Enable Command System"),
            i18n_description=i18n_text(
                zh_CN="邮箱适配器不使用命令系统，固定禁用并隐藏",
                en_US="The email adapter does not use the command system, so this option is fixed to disabled and hidden.",
            ),
        ).model_dump(),
    )
    COMMAND_UNAUTHORIZED_OUTPUT: bool = Field(
        default=False,
        title="权限不足提示",
        description="邮箱适配器不使用命令系统，固定隐藏",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(zh_CN="命令", en_US="Commands"),
            i18n_title=i18n_text(zh_CN="权限不足提示", en_US="Show Permission Denied Notice"),
            i18n_description=i18n_text(
                zh_CN="邮箱适配器不使用命令系统，固定隐藏",
                en_US="The email adapter does not use the command system, so this option is fixed to hidden.",
            ),
        ).model_dump(),
    )
    COMMAND_ENHANCED_OUTPUT: bool = Field(
        default=False,
        title="命令增强输出",
        description="邮箱适配器未实现平台增强输出，固定隐藏",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(zh_CN="命令", en_US="Commands"),
            i18n_title=i18n_text(zh_CN="命令增强输出", en_US="Enhanced Command Output"),
            i18n_description=i18n_text(
                zh_CN="邮箱适配器未实现平台增强输出，固定隐藏",
                en_US="The email adapter does not implement platform-specific enhanced command output, so this option is fixed to hidden.",
            ),
        ).model_dump(),
    )
    COMMAND_ENHANCED_OUTPUT_MIN_LENGTH: int = Field(
        default=200,
        title="增强输出触发字数",
        description="邮箱适配器未实现平台增强输出，固定隐藏",
        json_schema_extra=ExtraField(
            is_hidden=True,
            i18n_category=i18n_text(zh_CN="命令", en_US="Commands"),
            i18n_title=i18n_text(zh_CN="增强输出触发字数", en_US="Enhanced Output Threshold"),
            i18n_description=i18n_text(
                zh_CN="邮箱适配器未实现平台增强输出，固定隐藏",
                en_US="The email adapter does not implement platform-specific enhanced command output, so this option is fixed to hidden.",
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
        if not isinstance(self.STATUS_MAIL_TARGETS, list):
            self.STATUS_MAIL_TARGETS = []
        for account in self.RECEIVE_ACCOUNTS:
            if not hasattr(account, "RECEIVE_ENABLED"):
                account.RECEIVE_ENABLED = True

        # 互斥校验：最多仅允许一个默认发件人
        def _validate_default_sender() -> None:
            flags = [1 for acc in self.RECEIVE_ACCOUNTS if getattr(acc, "IS_DEFAULT_SENDER", False)]
            if len(flags) > 1:
                raise ValueError("默认发件人只能选择一个：请取消多余的默认标记")

        with suppress(Exception):
            _validate_default_sender()
        return self

    @classmethod
    def load_config(cls, file_path=None, auto_register: bool = True):
        config = super().load_config(file_path=file_path, auto_register=auto_register)
        config._migrate_legacy_status_mail_config()
        return config

    def _migrate_legacy_status_mail_config(self) -> None:
        from nekro_agent.core.config import config as core_config

        legacy_username = core_config.MAIL_USERNAME.strip()
        has_legacy = bool(
            legacy_username
            or core_config.MAIL_PASSWORD.strip()
            or core_config.MAIL_TARGET
            or core_config.MAIL_HOSTNAME.strip()
        )

        if self.STATUS_MAIL_MIGRATED or not has_legacy:
            return

        changed = False
        account_ready = False
        sender_ready = False
        targets_ready = not bool(core_config.MAIL_TARGET)

        if core_config.MAIL_ENABLED and not self.STATUS_MAIL_ENABLED:
            self.STATUS_MAIL_ENABLED = True
            changed = True

        if legacy_username:
            migrated_account = EmailAccount(
                EMAIL_ACCOUNT="自定义",
                CUSTOM_SMTP_HOST=core_config.MAIL_HOSTNAME,
                CUSTOM_SMTP_PORT=core_config.MAIL_PORT,
                CUSTOM_SMTP_SSL_PORT=465 if core_config.MAIL_PORT == 587 else core_config.MAIL_PORT,
                CUSTOM_SMTP_USE_SSL=not core_config.MAIL_STARTTLS,
                ENABLED=True,
                RECEIVE_ENABLED=False,
                USERNAME=legacy_username,
                PASSWORD=core_config.MAIL_PASSWORD,
                SEND_ENABLED=True,
                IS_DEFAULT_SENDER=False,
            )
            existing = next((acc for acc in self.RECEIVE_ACCOUNTS if acc.USERNAME == migrated_account.USERNAME), None)
            if existing is None:
                self.RECEIVE_ACCOUNTS.append(migrated_account)
                changed = True
                account_ready = True
            else:
                original = existing.model_dump()
                existing.PASSWORD = migrated_account.PASSWORD
                existing.SEND_ENABLED = True
                existing.RECEIVE_ENABLED = False
                existing.EMAIL_ACCOUNT = "自定义"
                existing.CUSTOM_SMTP_HOST = core_config.MAIL_HOSTNAME
                existing.CUSTOM_SMTP_PORT = core_config.MAIL_PORT
                existing.CUSTOM_SMTP_SSL_PORT = 465 if core_config.MAIL_PORT == 587 else core_config.MAIL_PORT
                existing.CUSTOM_SMTP_USE_SSL = not core_config.MAIL_STARTTLS
                if existing.model_dump() != original:
                    changed = True
                account_ready = (
                    existing.SEND_ENABLED
                    and not existing.RECEIVE_ENABLED
                    and existing.USERNAME == legacy_username
                )

            if not self.STATUS_MAIL_SENDER_ACCOUNT.strip():
                self.STATUS_MAIL_SENDER_ACCOUNT = legacy_username
                changed = True
            sender_ready = self.STATUS_MAIL_SENDER_ACCOUNT == legacy_username

        if not any(item.EMAIL.strip() for item in self.STATUS_MAIL_TARGETS) and core_config.MAIL_TARGET:
            self.STATUS_MAIL_TARGETS = [
                StatusMailRecipient(EMAIL=target)
                for target in core_config.MAIL_TARGET
                if str(target).strip()
            ]
            changed = True
        if core_config.MAIL_TARGET:
            current_targets = {item.EMAIL.strip() for item in self.STATUS_MAIL_TARGETS if item.EMAIL.strip()}
            targets_ready = current_targets.issuperset({str(target).strip() for target in core_config.MAIL_TARGET if str(target).strip()})

        if legacy_username and not account_ready:
            existing = next((acc for acc in self.RECEIVE_ACCOUNTS if acc.USERNAME == legacy_username), None)
            account_ready = bool(existing and existing.SEND_ENABLED and not existing.RECEIVE_ENABLED)
        if legacy_username and not sender_ready:
            sender_ready = self.STATUS_MAIL_SENDER_ACCOUNT == legacy_username

        if account_ready and sender_ready and targets_ready:
            self.STATUS_MAIL_MIGRATED = True
            changed = True

        if changed:
            with suppress(Exception):
                self.dump_config()
