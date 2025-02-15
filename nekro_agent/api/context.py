"""上下文相关 API

此模块提供了与上下文相关的 API 接口。
"""

from typing import Tuple

__all__ = [
    "get_chat_id",
    "get_chat_type",
    "parse_chat_key",
]


def parse_chat_key(chat_key: str) -> Tuple[str, str]:
    """解析会话标识

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"

    Returns:
        Tuple[str, str]: (会话类型, 会话ID)

    Example:
        ```python
        from nekro_agent.api.context import parse_chat_key

        # 解析会话标识
        chat_type, chat_id = parse_chat_key("group_123456")
        print(chat_type)  # "group"
        print(chat_id)    # "123456"
        ```
    """
    try:
        chat_type, chat_id = chat_key.split("_")
    except Exception as e:
        raise Exception(f"解析会话标识失败: {e}") from e
    else:
        return chat_type, chat_id


def get_chat_type(chat_key: str) -> str:
    """获取会话类型

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"

    Returns:
        str: 会话类型

    Example:
        ```python
        from nekro_agent.api.context import get_chat_type

        # 获取会话类型
        chat_type = get_chat_type("group_123456")
        print(chat_type)  # "group"
        ```
    """
    return parse_chat_key(chat_key)[0]


def get_chat_id(chat_key: str) -> str:
    """获取会话ID

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"

    Returns:
        str: 会话ID

    Example:
        ```python
        from nekro_agent.api.context import get_chat_id

        # 获取会话ID
        chat_id = get_chat_id("group_123456")
        print(chat_id)  # "123456"
        ```
    """
    return parse_chat_key(chat_key)[1]
