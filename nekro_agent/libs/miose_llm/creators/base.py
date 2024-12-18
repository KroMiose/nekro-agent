from abc import ABC, abstractmethod
from typing import Any


class BasePromptCreator(ABC):
    """Prompt 构建器基类"""

    @abstractmethod
    async def render(self) -> Any:
        """动态渲染 Prompt 模板为目标 LLM 支持的格式"""
