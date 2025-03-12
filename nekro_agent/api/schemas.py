"""Schema 类型定义

此模块提供了 Nekro-Agent 的类型定义。
"""

from typing import List, Union

from nekro_agent.schemas.agent_ctx import AgentCtx, WebhookRequest
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
)

__all__ = [
    "AgentCtx",
    "AgentMessageSegment",
    "AgentMessageSegmentType",
    "MessageContent",
    "WebhookRequest",
]

# 消息内容类型
MessageContent = Union[str, List[AgentMessageSegment]]
