from typing import Any, Dict, List, Literal, Optional, Tuple

from ..components import BaseComponent
from ..exceptions import ArgumentTypeError, RenderPromptError
from .base import BasePromptCreator


class _Message:
    role: Literal["system", "user", "assistant"]

    def __init__(self, *args, sep: str = "\n"):
        self.message_segments: Tuple[Any] = args
        self.sep: str = sep

    async def resolve(self) -> str:
        ret: List[str] = []
        for m in self.message_segments:
            if isinstance(m, BaseComponent):
                ret.append(await m.render())
            elif isinstance(m, str):
                ret.append(m)
            elif isinstance(m, _Message):
                ret.append(await m.resolve())
            else:
                raise ArgumentTypeError("Invalid message type")
        return self.sep.join(ret)

    async def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": await self.resolve()}


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
    async def render(self) -> List[Dict[str, str]]:
        return [await m.to_dict() for m in self.messages]
        # try:
        #     return [await m.to_dict() for m in self.messages]
        # except Exception as e:
        #     raise RenderPromptError(f"Error rendering prompt: {e}") from e

    @classmethod
    def transform_prompt(cls, message_dicts: List[Dict[str, str]]):

        prompt = ""
        for message_dict in message_dicts:
            role = message_dict["role"]
            content = message_dict["content"]
            prompt += f"<|{role}|>:\n{content}\n\n"

        return prompt
