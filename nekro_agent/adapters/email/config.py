from typing import Any, Dict, List
from pydantic import BaseModel, Field, model_validator
from typing import Literal
from nekro_agent.adapters.interface.base import BaseAdapterConfig
from nekro_agent.core.core_utils import ExtraField


class EmailAccount(BaseModel):
    EMAIL_ACCOUNT: str = Field(
        default="QQ邮箱",
        title="邮箱提供商",
        description="填写邮箱提供商，现在支持QQ邮箱、163邮箱（填写时注意大小写）",
    )
    ENABLED: bool = Field(
        default=True,
        title="启用账户",
        description="是否启用此邮箱账户，设置为否时将跳过连接和轮询",
    )
    USERNAME: str = Field(
        default="",
        title="邮箱用户名",
        description="填写完整邮箱地址，例如 user@example.com",
        json_schema_extra=ExtraField(required=True, placeholder="user@example.com").model_dump(),
    )
    PASSWORD: str = Field(
        default="",
        title="邮箱密码/授权码",
        description="建议使用应用专用密码或 IMAP 授权码（不同服务商名称不同）",
        json_schema_extra=ExtraField(required=True, is_secret=True, placeholder="app-specific password").model_dump(),
    )
    SEND_ENABLED: bool = Field(
        default=False,
        title="启用发信",
        description="是否允许该邮箱账户用于SMTP发信",
    )
    IS_DEFAULT_SENDER: bool = Field(
        default=False,
        title="默认发件人",
        description="设为默认发件人",
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
        json_schema_extra=ExtraField(sub_item_name="邮箱账户", placeholder="添加你的邮箱账户").model_dump(),
    )
    POLL_INTERVAL: int = Field(
        default=30,
        title="轮询间隔(秒)",
        description="每次轮询之间的等待时长。适当增大可减轻服务器压力",
        json_schema_extra=ExtraField(placeholder="30").model_dump(),
    )
    FETCH_UNSEEN_ONLY: bool = Field(
        default=True,
        title="仅拉取未读",
        description="启用后仅处理未读邮件，避免重复",
        json_schema_extra=ExtraField().model_dump(),
    )
    MAX_PER_POLL: int = Field(
        default=50,
        title="每次最大抓取数",
        description="单次轮询最大抓取的邮件数量上限",
        json_schema_extra=ExtraField(placeholder="50").model_dump(),
    )
    MARK_AS_SEEN_AFTER_FETCH: bool = Field(
        default=True,
        title="读取后标记已读",
        description="启用后在读取并收集消息后将邮件标记为已读(\Seen)",
        json_schema_extra=ExtraField().model_dump(),
    )
    IMAP_TIMEOUT: int = Field(
        default=60,
        title="IMAP 连接超时(秒)",
        description="IMAP 连接和操作的超时时间，适用于所有邮箱账户",
        json_schema_extra=ExtraField(placeholder="60").model_dump(),
    )
    EMAIL_NOTIFICATIONS_ENABLED: bool = Field(
        default=False,
        title="启用新邮件通知",
        description="是否在接收到新邮件后自动触发通知和 AI 处理",
        json_schema_extra=ExtraField().model_dump(),
    )
    EMAIL_NOTIFICATIONS_CHAT_KEY: str = Field(
        default="",
        title="新邮件通知聊天频道",
        description="接收新邮件通知的聊天频道标识（例如 onebot_v11-group_xxx）",
        json_schema_extra=ExtraField().model_dump(),
    )
    SESSION_ENABLE_AT: bool = Field(
        default=False,
        title="禁用 @ 功能",
        description="邮箱适配器不需要 @ 功能，固定禁用并隐藏",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
    )
    SESSION_PROCESSING_WITH_EMOJI: bool = Field(
        default=False,
        title="禁用处理中表情",
        description="邮箱适配器不需要处理表情反馈，固定禁用并隐藏",
        json_schema_extra=ExtraField(is_hidden=True).model_dump(),
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
        try:
            flags = [1 for acc in self.RECEIVE_ACCOUNTS if getattr(acc, "IS_DEFAULT_SENDER", False)]
            if len(flags) > 1:
                raise ValueError("默认发件人只能选择一个：请取消多余的默认标记")
        except Exception:
            pass
        return self
