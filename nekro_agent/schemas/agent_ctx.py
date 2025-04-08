from typing import Any, Dict, Optional

from pydantic import BaseModel


class WebhookRequest(BaseModel):
    """Webhook 请求"""

    headers: Dict[str, str]
    body: Dict[str, Any]


class AgentCtx(BaseModel):
    container_key: Optional[str] = None
    from_chat_key: str
    extra_data: Dict[str, Any] = {}
    webhook_request: Optional[WebhookRequest] = None
