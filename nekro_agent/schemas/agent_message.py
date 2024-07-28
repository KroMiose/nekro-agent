from enum import Enum
from typing import List

from pydantic import BaseModel


class AgentMessageSegmentType(str, Enum):
    """消息段类型枚举"""

    TEXT = "text"
    FILE = "file"


class AgentMessageSegment(BaseModel):
    """由 Agent 发送消息使用的消息段

    Attributes:
        type: 消息段类型
        content: 消息段内容

    Example:
        ```python
        AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content="Hello, world!")  # 文本消息段
        AgentMessageSegment(type=AgentMessageSegmentType.FILE, content="shared/file.txt")  # 文件消息段
        ```
    """

    type: AgentMessageSegmentType = AgentMessageSegmentType.TEXT
    content: str

    class Config:
        use_enum_values = True

    def get_prompt(self):
        if self.type == AgentMessageSegmentType.TEXT:
            return f"{self.content}"

        if self.type == AgentMessageSegmentType.FILE:
            return f"[File: {self.content}]"

        return ""


def convert_agent_message_to_prompt(agent_messages: List[AgentMessageSegment]) -> str:
    prompt = ""
    for message in agent_messages:
        prompt += message.get_prompt() + " "

    return prompt
