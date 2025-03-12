"""LLM 相关 API

此模块提供了与 LLM 模型交互相关的 API 接口。
"""

from typing import Dict, List

# from nekro_agent.tools.llm import get_chat_response as _get_chat_response

__all__ = [
    "get_chat_response",
]


async def get_chat_response(
    messages: List[Dict[str, str]],
    model_group: str = "",
) -> str:
    """获取 LLM 模型的回复

    Args:
        messages (List[Dict[str, str]]): 消息列表，格式为 [{"role": "user", "content": "你好"}]
        model_group (str, optional): 使用的模型组名称。默认为空字符串，使用配置文件中的默认模型组

    Returns:
        str: LLM 模型的回复文本

    Example:
        ```python
        from nekro_agent.api import llm

        # 获取模型回复
        response = await llm.get_chat_response([
            {"role": "user", "content": "你好，请帮我写一首诗"}
        ])
        print(response)
        ```
    """
    return await _get_chat_response(
        messages=messages,
        model_group=model_group,
    ) 