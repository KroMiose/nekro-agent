import base64
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from ..components import BaseComponent
from ..exceptions import ArgumentTypeError, RenderPromptError
from .base import BasePromptCreator


class ImageMessageSegment:

    def __init__(self, image_url: str):
        self.image_url = image_url

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "image_url",
            "image_url": {"url": self.image_url},
        }

    @classmethod
    def from_path(cls, path: str) -> "ImageMessageSegment":
        if path.endswith(".png"):
            return cls(f"data:image/png;base64,{base64.b64encode(Path(path).read_bytes()).decode('utf-8')}")
        if path.endswith((".jpg", ".jpeg")):
            return cls(f"data:image/jpeg;base64,{base64.b64encode(Path(path).read_bytes()).decode('utf-8')}")
        if path.endswith(".gif"):
            return cls(f"data:image/gif;base64,{base64.b64encode(Path(path).read_bytes()).decode('utf-8')}")
        raise ValueError(f"Unsupported image format: {path}")

    @classmethod
    def from_url(cls, url: str) -> "ImageMessageSegment":
        return cls(url)


class _Message:
    role: Literal["system", "user", "assistant"]

    def __init__(self, *args, sep: str = "\n"):
        self.message_segments: Tuple[Any] = args
        self.sep: str = sep

    async def resolve(self) -> List[Union[str, ImageMessageSegment]]:
        ret: List[Union[str, ImageMessageSegment]] = []
        for m in self.message_segments:
            if isinstance(m, BaseComponent):
                ret.append(await m.render())
            elif isinstance(m, str):
                ret.append(m)
            elif isinstance(m, _Message):
                ret.extend(await m.resolve())
            elif isinstance(m, ImageMessageSegment):
                ret.append(m)
            else:
                raise ArgumentTypeError("Invalid message type")
        return ret

    async def to_dict(self) -> Dict[str, Union[str, List[Dict[str, Any]]]]:
        resolved: List[Union[str, ImageMessageSegment]] = await self.resolve()

        # 如果只包含文本，直接返回字符串格式
        if all(isinstance(item, str) for item in resolved):
            return {"role": self.role, "content": self.sep.join(resolved)}  # type: ignore

        # 包含图片时，需要构建content列表
        content: List[Dict[str, Any]] = []
        current_text: List[str] = []

        def flush_text():
            if current_text:
                content.append({"type": "text", "text": self.sep.join(current_text)})
                current_text.clear()

        for item in resolved:
            if isinstance(item, str):
                current_text.append(item)
            elif isinstance(item, ImageMessageSegment):
                flush_text()
                content.append(item.to_dict())

        flush_text()  # 确保最后的文本也被添加

        return {"role": self.role, "content": content}


class SystemMessage(_Message):
    role = "system"


class UserMessage(_Message):
    role = "user"


class AiMessage(_Message):
    role = "assistant"


class OpenAIPromptCreator(BasePromptCreator):

    messages: List[_Message]
    temperature: Optional[float]
    top_p: Optional[float]
    presence_penalty: Optional[float]
    frequency_penalty: Optional[float]
    max_tokens: Optional[int]
    stop_words: Optional[List[str]]

    def __init__(
        self,
        *args,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_words: Optional[List[str]] = None,
    ) -> None:
        self.messages = []
        for arg in args:
            if isinstance(arg, _Message):
                self.messages.append(arg)
            else:
                raise ArgumentTypeError("Invalid message type")
        self.temperature = temperature
        self.top_p = top_p
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.max_tokens = max_tokens
        self.stop_words = stop_words

    # Override
    async def render(self) -> List[Dict[str, Union[str, List[Dict[str, str]]]]]:
        return [await m.to_dict() for m in self.messages]

    @classmethod
    def transform_prompt(cls, message_dicts: List[Dict[str, Union[str, List[Dict[str, str]]]]]):
        def truncate_base64(text: str) -> str:
            # 检查是否为 base64 图片数据
            if text.startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/gif;base64,")):
                prefix = text[: text.index("base64,") + 7]  # 保留前缀
                base64_content = text[len(prefix) :]
                if len(base64_content) > 32:
                    return f"{prefix}{base64_content[:16]}...{base64_content[-16:]}"
            return text

        prompt = ""
        for message_dict in message_dicts:
            role = message_dict["role"]
            content = message_dict["content"]

            # 处理内容可能是字符串或列表的情况
            if isinstance(content, str):
                content = truncate_base64(content)
            elif isinstance(content, list):
                # 处理多模态内容
                processed_content = []
                for item in content:
                    if item["type"] == "text":
                        processed_content.append(item["text"])
                    elif item["type"] == "image_url":
                        url = item["image_url"]["url"] # type: ignore
                        processed_content.append(f"[Image: {truncate_base64(url)}]")
                content = "\n".join(processed_content)

            prompt += f"<|{role}|>:\n{content}\n\n"

        return prompt
