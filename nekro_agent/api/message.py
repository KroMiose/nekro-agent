"""消息相关 API

此模块提供了与消息发送相关的 API 接口。
"""

from typing import Optional

from nekro_agent.adapters.utils import adapter_utils
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import logger
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
)
from nekro_agent.services.chat.universal_chat_service import universal_chat_service
from nekro_agent.tools.common_util import (
    download_file,
)
from nekro_agent.tools.path_convertor import convert_filename_to_sandbox_upload_path

__all__ = [
    "download_from_url",
    "send_file",
    "send_image",
    "send_text",
]


async def send_text(
    chat_key: str,
    message: str,
    ctx: AgentCtx,
    *,
    record: bool = True,
    ref_msg_id: Optional[str] = None,
) -> None:
    """发送文本消息

    Args:
        chat_key (str): 会话标识，格式为 "{adapter_key}-{type}_{id}"，例如 "platform-group_123456"
        message (str): 要发送的文本消息
        ctx (AgentCtx): 上下文对象
        record (bool, optional): 是否记录到上下文。默认为 True

    Example:
        ```python
        from nekro_agent.api.message import send_text

        # 发送文本消息到群组（记录到上下文）
        send_text(chat_key, "你好，世界！", ctx)

        # 发送文本消息到群组（不记录到上下文）
        send_text(chat_key, "这是一条临时消息", ctx, record=False)
        ```
    """
    message_ = [AgentMessageSegment(content=message)]
    try:
        adapter = await adapter_utils.get_adapter_for_ctx(ctx)
        await universal_chat_service.send_agent_message(chat_key, message_, adapter, ctx, record=record, ref_msg_id=ref_msg_id)
    except Exception as e:
        logger.exception(f"发送文本消息失败: {e}")
        raise Exception("发送文本消息失败: 请确保会话标识正确且内容不为空或过长") from e


async def send_file(
    chat_key: str,
    file_path: str,
    ctx: AgentCtx,
    *,
    record: bool = True,
    ref_msg_id: Optional[str] = None,
) -> None:
    """发送文件消息

    Args:
        chat_key (str): 会话标识，格式为 "{adapter_key}-{type}_{id}"，例如 "platform-group_123456"
        file_path (str): 文件路径或URL
        ctx (AgentCtx): 上下文对象
        record (bool, optional): 是否记录到上下文。默认为 True

    Example:
        ```python
        from nekro_agent.api.message import send_file

        # 发送文件（记录到上下文）
        send_file(chat_key, "/path/to/file.pdf", ctx)

        # 发送文件（不记录到上下文）
        send_file(chat_key, "/path/to/temp.pdf", ctx, record=False)
        ```
    """
    message_ = [AgentMessageSegment(type=AgentMessageSegmentType.FILE, content=file_path)]
    try:
        adapter = await adapter_utils.get_adapter_for_ctx(ctx)
        await universal_chat_service.send_agent_message(
            chat_key,
            message_,
            adapter,
            ctx,
            file_mode=True,
            record=record,
            ref_msg_id=ref_msg_id,
        )
    except Exception as e:
        logger.exception(f"发送文件消息失败: {e}")
        raise Exception(f"发送文件消息失败: {e}") from e


async def send_image(
    chat_key: str, image_path: str, ctx: AgentCtx, *, record: bool = True, ref_msg_id: Optional[str] = None,
) -> None:
    """发送图片消息

    Args:
        chat_key (str): 会话标识，格式为 "{adapter_key}-{type}_{id}"，例如 "platform-group_123456"
        image_path (str): 图片路径或URL
        ctx (AgentCtx): 上下文对象
        record (bool, optional): 是否记录到上下文。默认为 True

    Example:
        ```python
        from nekro_agent.api.message import send_image

        # 发送图片（记录到上下文）
        send_image(chat_key, "/path/to/image.jpg", ctx)

        # 发送图片（不记录到上下文）
        send_image(chat_key, "/path/to/temp.jpg", ctx, record=False)
        ```
    """
    message_ = [AgentMessageSegment(type=AgentMessageSegmentType.FILE, content=image_path)]
    try:
        adapter = await adapter_utils.get_adapter_for_ctx(ctx)
        await universal_chat_service.send_agent_message(chat_key, message_, adapter, ctx, record=record, ref_msg_id=ref_msg_id)
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
        file_path, file_name = await download_file(url, from_chat_key=ctx.chat_key)
        return str(convert_filename_to_sandbox_upload_path(file_name))
    except Exception as e:
        logger.exception(f"下载文件失败: {e}")
        raise Exception(f"下载文件失败: {e}") from e
