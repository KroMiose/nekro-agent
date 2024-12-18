import time
from abc import ABC, abstractmethod
from asyncio import get_event_loop
from typing import Any, ClassVar, List, Optional, Tuple, Union

from ..creators import BasePromptCreator
from ..exceptions import ClientError


class ClientResponse:
    """LLM 客户端响应对象"""

    prompt_creator: BasePromptCreator
    prompt_text: str
    response_text: str
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    start_time: float
    finish_time: float
    duration: float
    _is_finished: bool = False
    _test_output: Optional[str] = None

    def __init__(
        self,
        prompt_creator,
    ):
        self.prompt_creator = prompt_creator
        self.start_time = time.time()

    def update_token_info(
        self,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
    ):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens

    def finish(self, prompt_text: str, response_text: str):
        if self._is_finished:
            raise ClientError("Client response has already been finished.")
        self.prompt_text = prompt_text
        self.response_text = response_text
        self.finish_time = time.time()
        self.duration = self.finish_time - self.start_time
        self._is_finished = True

    def attach_test_output(self, test_output: str):
        self._test_output = test_output

    @property
    def test_output(self) -> Optional[str]:
        return self._test_output


class BaseClient(ABC):
    """LLM 客户端基类"""

    supported_creator = BasePromptCreator

    def __init__(self, name):
        self.name = name

    def gen_response(self, *args, **kwargs):
        return get_event_loop().run_until_complete(
            self.async_gen_response(*args, **kwargs),
        )

    async def async_gen_response(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def call(
        self, creator: BasePromptCreator, cr: ClientResponse,
    ) -> ClientResponse:
        """调用 LLM 客户端获取响应

        Args:
            creator (BasePromptCreator): 用于生成请求的 PromptCreator 对象

        Returns:
            Tuple[str, str]: 提示词文本, 响应文本
        """
        raise NotImplementedError
