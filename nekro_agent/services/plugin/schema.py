from enum import Enum
from typing import Any, Callable, Coroutine


class SandboxMethodType(str, Enum):
    """沙盒方法类型

    用于描述方法的类型，如工具方法, 行为方法等；方法类型区别主要在于对返回值的处理方式。

    * TOOL: 工具方法
        提供给 LLM 使用的工具，返回值可以是任意类型，LLM 可获取返回值作进一步处理

    * AGENT: 代理方法
        用于提供 LLM 交互反馈，其返回值必须为 str 类型，描述 LLM 行为的结果，返回后会被添加到上下文中再次调用

    * BEHAVIOR: 行为方法
        用于提供 LLM 交互反馈，其返回值必须为 str 类型，描述 LLM 行为的结果，返回后会被添加到上下文中但不触发再次调用

    * MULTIMODAL_AGENT: 多模态 Agent
        用于提供 LLM 交互反馈，其返回值为一段 多模态 message，描述 LLM 行为的结果，返回后会被添加到上下文中再次调用
    """

    TOOL = "tool"
    AGENT = "agent"
    BEHAVIOR = "behavior"
    MULTIMODAL_AGENT = "multimodal_agent"


class WebhookMethod:
    """Webhook 方法"""

    def __init__(self, name: str, description: str, func: Callable[..., Coroutine[Any, Any, Any]]):
        self.name = name
        self.description = description
        self.func = func


class SandboxMethod:
    """沙盒方法"""

    def __init__(
        self,
        method_type: SandboxMethodType,
        name: str,
        description: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
    ):
        self.method_type = method_type
        self.name = name
        self.description = description
        self.func = func


class PromptInjectMethod:
    """提示注入方法"""

    def __init__(self, name: str, description: str, func: Callable[..., Coroutine[Any, Any, str]]):
        self.name = name
        self.description = description
        self.func = func
