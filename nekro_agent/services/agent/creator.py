import base64
from pathlib import Path
from typing import Any, Dict, List, Literal, Union

import magic
from jinja2 import Environment

from .templates.base import PromptTemplate
from .templates.base import env as default_env

mime = magic.Magic(mime=True)


class OpenAIChatMessage:
    """OpenAI 聊天消息"""

    def __init__(self, role: Literal["user", "assistant", "system"], content: List[Dict[str, Any]]):
        self.role: Literal["user", "assistant", "system"] = role
        self.content = content

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        将连续的文本内容进行聚合，例如:
        [{"type": "text", "text": "你好 "}, {"type": "text", "text": "世界"}]
        会被聚合为:
        [{"type": "text", "text": "你好 世界"}]
        """

        if all(_c["type"] == "text" for _c in self.content):
            return {"role": self.role, "content": "".join(_c["text"] for _c in self.content)}

        merged_content: List[Dict[str, Any]] = []
        current_text = ""
        for segment in self.content:
            if segment["type"] == "text":
                current_text += segment["text"]
            else:
                if current_text:
                    merged_content.append({"type": "text", "text": current_text})
                    current_text = ""
                merged_content.append(segment)
        if current_text:
            merged_content.append({"type": "text", "text": current_text})
        return {"role": self.role, "content": merged_content}

    @classmethod
    def from_text(cls, role: Literal["user", "assistant", "system"], text: str) -> "OpenAIChatMessage":
        """从文本生成消息"""
        return cls(role, [ContentSegment.text_content(text)])

    @classmethod
    def from_template(
        cls,
        role: Literal["user", "assistant", "system"],
        template: PromptTemplate,
        env: Environment = default_env,
    ) -> "OpenAIChatMessage":
        """添加 Jinja2 模板渲染片段"""
        return cls(role, [ContentSegment.text_content(template.render(env))])

    @classmethod
    def create_empty(cls, role: Literal["user", "assistant", "system"]) -> "OpenAIChatMessage":
        """创建空消息"""
        return cls(role, [])

    def add(self, segment: Dict[str, Any]) -> "OpenAIChatMessage":
        """添加内容片段"""
        self.content.append(segment)
        return self

    def batch_add(self, segments: List[Dict[str, Any]]) -> "OpenAIChatMessage":
        """批量添加内容片段"""
        self.content.extend(segments)
        return self

    def extend(self, other: "OpenAIChatMessage") -> "OpenAIChatMessage":
        """合并消息"""
        if self.role != other.role:
            raise ValueError("消息角色不一致")
        if isinstance(other.content, str):
            other.content = [ContentSegment.text_content(other.content)]
        return OpenAIChatMessage(self.role, self.content + other.content)

    def tidy(self) -> "OpenAIChatMessage":
        """整理消息合并所有连续的文本内容"""
        merged_content: List[Dict[str, Any]] = []
        current_text = ""
        for segment in self.content:
            if segment["type"] == "text":
                current_text += segment["text"]
            else:
                if current_text:
                    merged_content.append({"type": "text", "text": current_text})
                    current_text = ""
                merged_content.append(segment)
        if current_text:
            merged_content.append({"type": "text", "text": current_text})
        return OpenAIChatMessage(self.role, merged_content)


class ContentSegment:
    """内容片段生成器"""

    @staticmethod
    def image_content(image_url: str) -> Dict[str, Any]:
        """生成图片内容片段"""
        return {"type": "image_url", "image_url": {"url": image_url}}

    @staticmethod
    def image_content_from_bytes(image_bytes: bytes, image_type: str) -> Dict[str, Any]:
        """根据图片字节生成图片内容片段"""
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/{image_type};base64,{base64.b64encode(image_bytes).decode()}"},
        }

    @staticmethod
    def image_content_from_path(image_path: Union[str, Path]) -> Dict[str, Any]:
        """根据图片路径生成图片内容片段"""
        if isinstance(image_path, str) and image_path.startswith("data:"):
            return {
                "type": "image_url",
                "image_url": {"url": image_path},
            }

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"图片路径不存在: {path}")

        file_bytes = path.read_bytes()
        mime_type = mime.from_buffer(file_bytes)
        mime_type = "image/png" if mime_type == "image/gif" else mime_type

        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{base64.b64encode(file_bytes).decode()}"},
        }

    @staticmethod
    def text_content(text: str) -> Dict[str, Any]:
        """生成文本内容片段"""
        return {"type": "text", "text": text}
