from typing import Optional

from pydantic import BaseModel


class AgentCtx(BaseModel):
    container_key: Optional[str] = None
    from_chat_key: str
