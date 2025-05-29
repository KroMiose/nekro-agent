"""
SSE 适配器
=========

该适配器实现了基于SSE (Server-Sent Events)的双向通信协议，
允许各种客户端通过HTTP与NekroAgent进行消息交换。

核心概念:
1. 适配器(Adapter): 负责协议与平台之间的转换
2. 客户端(Client): 连接到适配器的外部程序
3. 频道(Channel): 消息的交换场所，可以是群聊或私聊
4. 消息(Message): 在频道中交换的内容，包含各种消息段

适配器使用 channel_id 作为内部标识，格式为: `sse-{platform}-{channel_id}`
但对外部客户端，只暴露platform和channel_id概念。
"""

from typing import List, Type

from fastapi import APIRouter
from pydantic import Field

from nekro_agent.adapters.interface.schemas.platform import (
    PlatformChannel,
    PlatformSendRequest,
    PlatformSendResponse,
    PlatformSendSegmentType,
    PlatformUser,
)
from nekro_agent.core import logger
from nekro_agent.schemas.chat_message import ChatType

from ..interface.base import BaseAdapter, BaseAdapterConfig
from .commands import set_client_manager
from .core.client import SseClientManager
from .core.message import SseMessageConverter
from .core.service import SseApiService


class SSEConfig(BaseAdapterConfig):
    """SSE 适配器配置"""


class SSEAdapter(BaseAdapter):
    """SSE 协议适配器

    负责:
    1. 处理客户端连接与消息
    2. 转换消息格式
    3. 管理频道订阅
    """

    def __init__(self, config_cls: Type[BaseAdapterConfig] = SSEConfig):
        """初始化SSE适配器"""
        super().__init__(config_cls)
        # 核心组件
        self.client_manager = SseClientManager()
        self.message_converter = SseMessageConverter()
        self.service = SseApiService(self.client_manager)

        # 设置全局client_manager变量，确保commands.py中可以访问
        set_client_manager(self.client_manager)

    def get_adapter_router(self) -> APIRouter:
        from .routers import router, set_router_client_manager

        # 设置路由模块的client_manager
        set_router_client_manager(self.client_manager)

        return router

    async def init(self) -> None:
        """初始化适配器"""
        # 启动客户端管理器
        await self.client_manager.start()

        logger.info(f"SSE适配器 [{self.key}] 已初始化")

    async def cleanup(self) -> None:
        """清理适配器"""
        return

    @property
    def key(self) -> str:
        """适配器唯一标识"""
        return "sse"

    @property
    def chat_key_rules(self) -> List[str]:
        """聊天标识规则说明"""
        return [
            "群聊: `sse-{platform}_group_{id}` (例如 sse-platform_group_123456)",
            "私聊: `sse-{platform}_private_{id}` (例如 sse-platform_private_user123)",
        ]

    def build_channel_id(self, platform: str, channel_id: str) -> str:
        """构建聊天标识

        Args:
            platform: 平台标识
            channel_id: 频道ID

        Returns:
            str: 聊天标识
        """
        return f"sse-{platform}-{channel_id}"

    async def forward_message(self, request: PlatformSendRequest) -> PlatformSendResponse:
        """推送消息到客户端

        Args:
            request: 包含要发送的消息段和目标channel_id

        Returns:
            PlatformSendResponse: 发送结果
        """
        try:
            # 解析channel_id
            _, channel_id = self.parse_chat_key(request.chat_key)

            # 转换消息
            sse_message = await self.message_converter.platform_to_sse_message(
                channel_id=channel_id,
                segments=request.segments,
            )

            # 获取订阅该频道的客户端
            clients = self.client_manager.get_clients_by_channel(channel_id)
            if not clients:
                logger.warning(f"没有客户端处理频道 {channel_id}")
                return PlatformSendResponse(success=False, error_message=f"没有客户端处理频道 {channel_id}")

            # 发送消息
            response = await self.service.send_message_to_clients(clients=clients, message=sse_message)

            if response:
                return PlatformSendResponse(success=True)
            return PlatformSendResponse(success=False, error_message="所有客户端发送消息失败")

        except Exception as e:
            logger.error(f"发送SSE消息失败: {e}")
            return PlatformSendResponse(success=False, error_message=f"发送SSE消息失败: {e!s}")

    async def get_self_info(self) -> PlatformUser:
        """获取自身信息"""
        response = await self.service.get_self_info()

        if not response:
            return PlatformUser(user_id="unknown", user_name="未知SSE机器人")

        return PlatformUser(user_id=response.user_id, user_name=response.user_name, user_avatar=response.user_avatar or "")

    async def get_user_info(self, user_id: str, channel_id: str) -> PlatformUser:  # noqa: ARG002
        """获取用户信息"""
        response = await self.service.get_user_info(user_id)

        if not response:
            return PlatformUser(user_id=user_id, user_name=user_id)

        return PlatformUser(user_id=response.user_id, user_name=response.user_name, user_avatar=response.user_avatar or "")

    async def get_channel_info(self, channel_id: str) -> PlatformChannel:
        """获取频道信息

        Args:
            channel_id: 频道ID，格式为 group_xxx 或 private_xxx

        Returns:
            PlatformChannel: 频道信息
        """
        # 判断频道类型
        channel_type = ChatType.GROUP if channel_id.startswith("group_") else ChatType.PRIVATE

        response = await self.service.get_channel_info(channel_id)

        if not response:
            return PlatformChannel(channel_id=channel_id, channel_name=channel_id, channel_type=channel_type)

        return PlatformChannel(
            channel_id=response.channel_id,
            channel_name=response.channel_name,
            channel_type=channel_type,
            channel_avatar=response.channel_avatar or "",
        )

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:
        """设置消息反应"""
        return await self.service.set_message_reaction(message_id, status)
