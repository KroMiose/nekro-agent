from enum import Enum
from typing import Any, Coroutine

from miose_toolkit_llm.components import BaseComponent

from nekro_agent.core import logger

REPLY_INSTRUCTION = """
## 回复格式

你的回答必须使用以下两种格式之一:

1. 文本回复(适用于简单回答): 内容文本将被直接发送到对应会话中
2. 脚本流程回复(编写 Python 脚本解答问题) : 脚本将在预先准备的容器中执行，可以在其中调用给定 API 与会话等资源进行交互

## 示例回复:

1. 文本回复

```
text:>你好！
```

2. 脚本流程回复

```
script:>
import requests

requests.post(f"{CHAT_API}/send_message", )
```

## 容器环境与接口说明

### Python 版本: 3.10.13

### 目录说明

- 你的工作目录: /app
- 共享资源目录: /app/shared (可读写，用于与用户交互资源，需要通过接口发送的文件资源必须先保存到该目录)
- 用户上传资源目录: /app/uploads (只读，用于获取用户上传资源)

### 已安装依赖 (省略已被下列依赖引用的依赖):

- requests = "^2.27.1"
- matplotlib = "^3.9.1"
- numpy = "^2.0.1"

### 预置变量说明 (不需要在脚本中声明)

- CHAT_API: 聊天服务的基础 API 地址

### 可用接口: 请严格按照以下接口说明使用接口

- /chat/send_msg: 向会话发送消息

Parameters:
    chat_key: 会话 ID

Body:
    message_segments(body): 消息片段

Returns:
    bool: 是否发送成功

Usage:
    requests.post(
        f"{CHAT_API}/chat/send_msg?chat_key=group_123456",
        json=[
            {"type": "text", "content": "Hello!"},
            {"type": "file", "content": "shared/output.txt"},
            {"type": "file", "content": "https://example.com/image.jpg"},
        ]
    )
"""


class ChatResponseType(str, Enum):
    TEXT = "text"
    SCRIPT = "script"


class ChatResponseResolver(BaseComponent):
    """自定义结果解析器"""

    ret_type: ChatResponseType
    ret_content: str

    @classmethod
    def example(cls) -> str:
        return REPLY_INSTRUCTION.strip()

    def resolve_from_text(self, response_text: str) -> "ChatResponseResolver":
        """从响应文本中解析结果 处理脑瘫模型返回的各种奇怪文本"""
        response_text = response_text.strip()
        if response_text.startswith("```python"):
            response_text = response_text.strip()[10:]
            self.ret_type = ChatResponseType.SCRIPT
            if response_text.endswith("```"):
                response_text = response_text.strip()[:-3]
            if response_text.strip().startswith("script:>"):
                response_text = response_text.strip()[8:]
            self.ret_content = response_text
            return self

        if response_text.startswith("```"):
            response_text = response_text.strip()[3:]
        if response_text.endswith("```"):
            response_text = response_text.strip()[:-3]

        try:
            _ret_type, ret_content = response_text.split(":>", 1)
        except ValueError as e:
            raise ValueError(f"Invalid response format: \n{response_text}\nError: {e}") from e

        self.ret_type = ChatResponseType(_ret_type.strip().lower())
        self.ret_content = ret_content.strip()

        return self

    def render(self, *args, **kwargs) -> Coroutine[Any, Any, str]:
        return super().render(*args, **kwargs)
