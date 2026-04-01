
"""通用消息服务

这个服务负责处理跨平台的消息发送逻辑，包含所有与具体协议端无关的通用处理。
协议端特定的逻辑通过 adapter.forward_message 接口委托给各自的适配器实现。
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Union

from nekro_agent.adapters.interface.base import BaseAdapter
from nekro_agent.adapters.interface.schemas.platform import (
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegment,
    PlatformSendSegmentType,
)
from nekro_agent.adapters.utils import adapter_utils
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.config import config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.schemas.agent_message import (
    AgentMessageSegment,
    AgentMessageSegmentType,
)
from nekro_agent.services.agent.resolver import fix_raw_response
from nekro_agent.tools.common_util import download_file
from nekro_agent.tools.path_convertor import (
    convert_to_host_path,
    is_url_path,
)

logger = get_sub_logger("message_pipeline")


class UniversalChatService:
    """通用消息服务 - 处理跨平台的消息发送逻辑"""

    def __init__(self):
        pass

    async def send_operation_message(self, chat_key: str, message: str):
        """发送操作消息（通用方法）

        Args:
            chat_key (str): 聊天频道标识
            message (str): 操作消息内容
        """

        adapter = await adapter_utils.get_adapter_for_chat(chat_key)
        await self.send_agent_message(
            chat_key=chat_key,
            messages=f"{config.AI_COMMAND_OUTPUT_PREFIX} {message}".strip(),
            adapter=adapter,
        )

    async def send_agent_message(
        self,
        chat_key: str,
        messages: Union[List[AgentMessageSegment], str],
        adapter: BaseAdapter,
        ctx: Optional[AgentCtx] = None,
        file_mode: bool = False,
        record: bool = False,
        ref_msg_id: Optional[str] = None,
    ):
        """发送机器人消息

        Args:
            chat_key (str): 聊天的唯一标识
            messages (Union[List[AgentMessageSegment], str]): 机器人消息
            adapter (BaseAdapter): 适配器实例
            ctx (Optional[AgentCtx], optional): 机器人上下文. Defaults to None.
            file_mode (bool, optional): 是否为文件发送模式（影响文件类型的消息段生成）. Defaults to False.
            record (bool, optional): 是否记录聊天记录. Defaults to False.

        Raises:
            ValueError: 聊天类型错误
        """
        if isinstance(messages, str):
            messages = [AgentMessageSegment(type=AgentMessageSegmentType.TEXT, content=messages)]

        # 预处理消息段
        processed_segments = await self._preprocess_messages(messages, chat_key, ctx, file_mode)

        # 检查是否有有效的消息段
        if not processed_segments:
            logger.warning("Empty Message, skip sending")
            if config.DEBUG_IN_CHAT:
                # 发送调试消息
                debug_request = PlatformSendRequest(
                    chat_key=chat_key,
                    segments=[PlatformSendSegment(type=PlatformSendSegmentType.TEXT, content="[Debug] 无消息回复")],
                )
                await adapter.forward_message(debug_request)
            return

        # 构建协议端发送请求
        send_request = PlatformSendRequest(
            chat_key=chat_key,
            segments=processed_segments,
            ref_msg_id=ref_msg_id,
        )

        # 发送消息
        try:
            plt_response: PlatformSendResponse = await adapter.forward_message(send_request)
        except Exception as e:
            logger.exception(f"发送消息失败: {e}")
            if config.DEBUG_IN_CHAT:
                debug_request = PlatformSendRequest(
                    chat_key=chat_key,
                    segments=[
                        PlatformSendSegment(
                            type=PlatformSendSegmentType.TEXT,
                            content="[Debug] 发送消息失败，请检查协议端状态",
                        ),
                    ],
                )
                await adapter.forward_message(debug_request)
            else:
                raise

        if not plt_response.success:
            logger.error(f"适配器发送消息失败，错误: {plt_response.error_message}")
            raise ValueError(f"适配器发送消息失败，错误: {plt_response.error_message}")

        # 记录聊天记录
        if record:
            from nekro_agent.services.message_service import message_service

            await message_service.push_bot_message(chat_key, messages, plt_response, ref_msg_id=ref_msg_id)

    async def _preprocess_messages(
        self,
        messages: List[AgentMessageSegment],
        chat_key: str,
        ctx: Optional[AgentCtx],
        file_mode: bool,
    ) -> List[PlatformSendSegment]:
        """预处理消息段，将 AgentMessageSegment 转换为 PlatformSendSegment

        Args:
            messages: 原始的 Agent 消息段列表
            chat_key: 聊天频道标识
            ctx: 上下文
            file_mode: 是否为文件模式（用于决定 FILE 类型文件生成 FILE 还是 IMAGE 消息段）

        Returns:
            List[PlatformSendSegment]: 预处理后的平台消息段列表
        """
        processed_segments: List[PlatformSendSegment] = []

        for agent_message in messages:
            content = agent_message.content
            agent_message_type = AgentMessageSegmentType(agent_message.type)

            if agent_message_type == AgentMessageSegmentType.TEXT:
                # 处理文本消息 - 只做基本的修复，不解析@
                content = fix_raw_response(content)

                if content.strip():
                    processed_segments.append(PlatformSendSegment(type=PlatformSendSegmentType.TEXT, content=content))

                logger.info(f"Sending agent message: {content}")

            elif agent_message_type in (
                AgentMessageSegmentType.IMAGE,
                AgentMessageSegmentType.FILE,
            ):
                segment_type = (
                    PlatformSendSegmentType.IMAGE
                    if agent_message_type == AgentMessageSegmentType.IMAGE
                    else (PlatformSendSegmentType.FILE if file_mode else PlatformSendSegmentType.IMAGE)
                )
                processed_segment = await self._preprocess_file_segment(
                    agent_message=agent_message,
                    chat_key=chat_key,
                    ctx=ctx,
                    content=content,
                    segment_type=segment_type,
                )
                processed_segments.extend(processed_segment)
            else:
                raise ValueError(f"Invalid agent message type: {agent_message.type}")

        return processed_segments

    async def _preprocess_file_segment(
        self,
        agent_message: AgentMessageSegment,
        chat_key: str,
        ctx: Optional[AgentCtx],
        content: str,
        segment_type: PlatformSendSegmentType,
    ) -> List[PlatformSendSegment]:
        """预处理图片/文件类消息段。"""
        try:
            if is_url_path(content):
                file_path, _ = await download_file(content, from_chat_key=chat_key)
                processed_file_path = file_path
                agent_message.content = str(file_path)
            else:
                content_path = Path(content)
                if content_path.is_absolute() and content_path.exists():
                    host_path = content_path
                else:
                    host_path = convert_to_host_path(
                        content_path,
                        chat_key=chat_key,
                        container_key=ctx.container_key if ctx else None,
                    )

                if host_path and host_path.exists():
                    processed_file_path = str(host_path)
                    agent_message.content = str(host_path)
                else:
                    logger.warning(f"Invalid or non-existent file path: {content}")
                    return [
                        PlatformSendSegment(
                            type=PlatformSendSegmentType.TEXT,
                            content=f"Invalid file path: {content}",
                        ),
                    ]

            logger.info(f"Sending agent file: {processed_file_path}")
            return [PlatformSendSegment(type=segment_type, file_path=processed_file_path)]
        except asyncio.CancelledError:
            raise
        except ValueError as e:
            logger.error(f"Path conversion error: {e}")
            return [PlatformSendSegment(type=PlatformSendSegmentType.TEXT, content=str(e))]
        except Exception as e:
            logger.exception(f"Unexpected file preprocessing error: {e}")
            return [PlatformSendSegment(type=PlatformSendSegmentType.TEXT, content=f"File processing failed: {e}")]


# 全局实例
universal_chat_service = UniversalChatService()
