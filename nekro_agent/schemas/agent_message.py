from enum import Enum

from pydantic import BaseModel


class AgentMessageSegmentType(str, Enum):
    TEXT = "text"
    FILE = "file"


class AgentMessageSegment(BaseModel):
    type: AgentMessageSegmentType
    content: str

    class Config:
        use_enum_values = True

    def get_prompt(self):
        if self.type == AgentMessageSegmentType.TEXT:
            return f"{self.content}"

        if self.type == AgentMessageSegmentType.FILE:
            return f"[File: {self.content}]"

        return ""
