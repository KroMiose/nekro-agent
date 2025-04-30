"""消息相关 API

此模块提供了与消息发送相关的 API 接口。
"""

from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import logger
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
)
from nekro_agent.services.chat import chat_service
from nekro_agent.tools.common_util import (
    download_file,
)
from nekro_agent.tools.path_convertor import convert_filename_to_container_path

__all__ = [
    "download_from_url",
    "send_file",
    "send_image",
    "send_text",
]


async def send_text(chat_key: str, message: str, ctx: AgentCtx, *, record: bool = True) -> None:
    """发送文本消息

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"
        message (str): 要发送的文本消息
        ctx (AgentCtx): 上下文对象
        record (bool, optional): 是否记录到上下文。默认为 True

    Example:
        ```python
        from nekro_agent.api.message import send_text

        # 发送文本消息到群组（记录到上下文）
        send_text("group_123456", "你好，世界！", ctx)

        # 发送文本消息到群组（不记录到上下文）
        send_text("group_123456", "这是一条临时消息", ctx, record=False)
        ```
    """
    message_ = [AgentMessageSegment(content=message)]
    try:
        await chat_service.send_agent_message(chat_key, message_, ctx, record=record)
    except Exception as e:
        logger.exception(f"发送文本消息失败: {e}")
        raise Exception("发送文本消息失败: 请确保会话标识正确且内容不为空或过长") from e


async def send_file(chat_key: str, file_path: str, ctx: AgentCtx, *, record: bool = True) -> None:
    """发送文件消息

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"
        file_path (str): 文件路径或URL
        ctx (AgentCtx): 上下文对象
        record (bool, optional): 是否记录到上下文。默认为 True

    Example:
        ```python
        from nekro_agent.api.message import send_file

        # 发送文件（记录到上下文）
        send_file("group_123456", "/path/to/file.pdf", ctx)

        # 发送文件（不记录到上下文）
        send_file("group_123456", "/path/to/temp.pdf", ctx, record=False)
        ```
    """
    message_ = [AgentMessageSegment(type=AgentMessageSegmentType.FILE, content=file_path)]
    try:
        await chat_service.send_agent_message(chat_key, message_, ctx, file_mode=True, record=record)
    except Exception as e:
        logger.exception(f"发送文件消息失败: {e}")
        raise Exception(f"发送文件消息失败: {e}") from e


async def send_image(chat_key: str, image_path: str, ctx: AgentCtx, *, record: bool = True) -> None:
    """发送图片消息

    Args:
        chat_key (str): 会话标识，格式为 "{type}_{id}"，例如 "group_123456"
        image_path (str): 图片路径或URL
        ctx (AgentCtx): 上下文对象
        record (bool, optional): 是否记录到上下文。默认为 True

    Example:
        ```python
        from nekro_agent.api.message import send_image

        # 发送图片（记录到上下文）
        send_image("group_123456", "/path/to/image.jpg", ctx)

        # 发送图片（不记录到上下文）
        send_image("group_123456", "/path/to/temp.jpg", ctx, record=False)
        ```
    """
    message_ = [AgentMessageSegment(type=AgentMessageSegmentType.FILE, content=image_path)]
    try:
        await chat_service.send_agent_message(chat_key, message_, ctx, record=record)
    except Exception as e:
        logger.exception(f"发送图片消息失败: {e}")
        raise Exception(f"发送图片消息失败: {e}") from e


async def download_from_url(url: str, ctx: AgentCtx) -> str:
    """从URL下载文件

    Args:
        url (str): 文件URL
        ctx (AgentCtx): 上下文对象

    Returns:
        str: 下载后的文件路径

    Example:
        ```python
        from nekro_agent.api.message import download_from_url

        # 下载文件
        file_path = download_from_url("https://example.com/file.jpg", ctx)
        ```
    """
    try:
        file_path, file_name = await download_file(url, from_chat_key=ctx.from_chat_key)
        return str(convert_filename_to_container_path(file_name))
    except Exception as e:
        logger.exception(f"下载文件失败: {e}")
        raise Exception(f"下载文件失败: {e}") from e
