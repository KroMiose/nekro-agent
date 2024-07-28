from enum import Enum
from typing import Any, Coroutine

from miose_toolkit_llm.components import BaseComponent

from nekro_agent.core import logger
from nekro_agent.tools.collector import agent_collector

REPLY_INSTRUCTION = """
## Response Format

Your response must adhere to one of the following formats:

1. **Text Response (for simple answers):** The content text will be directly sent to the corresponding conversation.
2. **Script Response (Python script for response):** The script will be executed in a pre-prepared container, allowing interaction with given APIs and conversation resources.

## Example Responses:

1. **Text Response**

```
text:> Hello!
```

2. **Script Response**

```
script:>
def add(a, b):
    return a + b

... # Do anything you need
```

## Container Environment and API Documentation

### Python Version: 3.10.13

### Directory Structure:

- Your working directory: /app
- Shared resources directory: /app/shared (read-write, used for interacting with user resources. Files to be sent to the user must be saved in this directory first)
- User uploaded resources directory: /app/uploads (read-only, used for accessing user uploaded resources)

### Installed Dependencies (excluding dependencies referenced by the following):

- requests = "^2.27.1"
- matplotlib = "^3.9.1"
- numpy = "^2.0.1"
- opencv-python = "^4.10.0.84"

### Predefined Variables or Methods (no need to declare in the script):

{AGENT_METHOD_PROMPT}

### Notes:

- If the program encounters an error (exit code is not 0), I will send you the error message for you to fix. Particularly, if you need to wait for the program's result and adjust your code accordingly, you can use print statements to display the result and then use `exit(1)` to exit the program. This will trigger a new program execution.
- Please avoid excessive console output in your program to prevent exceeding the context length.
- Your files will not be reflected in the chat conversation unless you explicitly call the API to send them.
- 除非特殊要求，否则你应该尽可能用中文回复！
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
        return REPLY_INSTRUCTION.strip().format(AGENT_METHOD_PROMPT="\n\n".join(agent_collector.gen_method_prompts()))

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
