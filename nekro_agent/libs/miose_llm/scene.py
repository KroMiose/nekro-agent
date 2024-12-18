import time
from abc import ABC
from pathlib import Path
from typing import List, Optional, Type, TypeVar, Union

from .clients import BaseClient, ClientResponse
from .creators import BasePromptCreator
from .store import BaseStore
from .tools.tokenizers import BaseTokenizer


class ModelResponse:
    """运行结果类"""

    client_response: ClientResponse
    generate_time: float
    _scene: "BaseScene"

    def __init__(self, client_response, scene: "BaseScene"):
        self.client_response = client_response
        self.generate_time = time.time()
        self._scene = scene

    @property
    def prompt_text(self) -> str:
        """获取提示文本"""
        return self.client_response.prompt_text

    @property
    def response_text(self) -> str:
        """获取响应文本"""
        return self.client_response.response_text

    @property
    def scene(self) -> "BaseScene":
        """获取场景对象"""
        return self._scene

    @property
    def store(self) -> BaseStore:
        """获取Store"""
        return self._scene.store

    def save(self, prompt_file: Union[str, Path], response_file: Union[str, Path]):
        """保存结果到文件"""
        prompt_file = Path(prompt_file) if isinstance(prompt_file, str) else prompt_file
        response_file = (
            Path(response_file) if isinstance(response_file, str) else response_file
        )

        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        response_file.parent.mkdir(parents=True, exist_ok=True)

        with prompt_file.open("w", encoding="utf-8") as f:
            f.write(self.prompt_text)
        with response_file.open("w", encoding="utf-8") as f:
            f.write(self.response_text)

    def feedback(self, rate: float, message: Optional[str] = None):
        """反馈结果"""


class Runner:
    """LLM 执行器"""

    client: BaseClient
    tokenizer: BaseTokenizer
    prompt_creator: BasePromptCreator

    def __init__(
        self,
        client: BaseClient,
        tokenizer: BaseTokenizer,
        prompt_creator: BasePromptCreator,
        name: str = "",
    ):
        self.client = client
        self.tokenizer = tokenizer
        self.prompt_creator = prompt_creator
        self.name = name


class BaseScene(ABC):
    """场景类"""

    runners: List[Runner]
    Store: Type[BaseStore] = BaseStore

    def __init__(self):
        self._store = self.Store()
        self.runners = []

    def attach_runner(self, runner: Runner):
        """添加Runner"""
        self.runners.append(runner)

    @property
    def store(self: "BaseScene") -> BaseStore:
        """获取Store"""
        return self._store

    async def run(
        self: "BaseScene",
        use_runner: Optional[Runner] = None,
        _use_test_output: str = "",
    ) -> ModelResponse:
        _runner = use_runner or self.runners[0]
        cr = ClientResponse(prompt_creator=_runner.prompt_creator)
        if _use_test_output:
            cr.attach_test_output(_use_test_output)
        cr: ClientResponse = await _runner.client.call(
            creator=_runner.prompt_creator,
            cr=cr,
        )
        return ModelResponse(client_response=cr, scene=self)
