from pydantic import BaseModel


class AgentCtx(BaseModel):
    container_key: str
    from_chat_key: str
