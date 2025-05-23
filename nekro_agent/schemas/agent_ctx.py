from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import BaseModel

from nekro_agent.adapters.utils import adapter_utils

if TYPE_CHECKING:
    from nekro_agent.adapters.interface import BaseAdapter
    from nekro_agent.models.db_chat_channel import DBChatChannel


class WebhookRequest(BaseModel):
    """Webhook 请求"""

    headers: Dict[str, str]
    body: Dict[str, Any]


class AgentCtx(BaseModel):
    container_key: Optional[str] = None
    from_chat_key: Optional[str] = None
    webhook_request: Optional[WebhookRequest] = None
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    channel_type: Optional[str] = None
    adapter_key: Optional[str] = None

    @property
    def chat_key(self) -> str:
        if not self.from_chat_key:
            raise ValueError("missing from_chat_key")
        return self.from_chat_key

    @property
    def adapter(self) -> "BaseAdapter":
        if not self.adapter_key:
            raise ValueError("missing adapter_key")
        return adapter_utils.get_adapter(self.adapter_key)

    @classmethod
    def create_by_db_chat_channel(
        cls,
        db_chat_channel: "DBChatChannel",
        container_key: Optional[str] = None,
        from_chat_key: Optional[str] = None,
        webhook_request: Optional[WebhookRequest] = None,
    ) -> "AgentCtx":
        """从数据库聊天频道创建 AgentCtx"""
        return cls(
            container_key=container_key,
            from_chat_key=from_chat_key or db_chat_channel.chat_key,
            channel_id=db_chat_channel.channel_id,
            channel_name=db_chat_channel.channel_name,
            channel_type=db_chat_channel.channel_type,
            adapter_key=db_chat_channel.adapter_key,
            webhook_request=webhook_request,
        )

    @classmethod
    async def create_by_chat_key(
        cls,
        chat_key: str,
        container_key: Optional[str] = None,
        from_chat_key: Optional[str] = None,
        webhook_request: Optional[WebhookRequest] = None,
    ) -> "AgentCtx":
        """从聊天频道创建 AgentCtx"""
        from nekro_agent.models.db_chat_channel import DBChatChannel

        db_chat_channel = await DBChatChannel.get_channel(chat_key=chat_key)
        return cls.create_by_db_chat_channel(db_chat_channel, container_key, from_chat_key, webhook_request)

    @classmethod
    async def create_by_webhook(
        cls,
        webhook_request: WebhookRequest,
    ) -> "AgentCtx":
        """从 Webhook 请求创建 AgentCtx"""
        return cls(webhook_request=webhook_request)
