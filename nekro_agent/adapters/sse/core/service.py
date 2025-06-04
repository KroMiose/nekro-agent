"""
SSE 服务层
=========

提供高层业务逻辑实现，封装与客户端的交互。

主要功能:
1. 消息发送
2. 用户信息获取
3. 频道信息获取
4. 消息反应设置
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from nekro_agent.adapters.sse.schemas import (
    SseChannelInfo,
    SseEvent,
    SseMessage,
    SseRequest,
    SseUserInfo,
)
from nekro_agent.core import logger

from .client import SseClient, SseClientManager


class SseApiService:
    """SSE API 服务

    封装与客户端的交互逻辑
    """

    def __init__(self, client_manager: SseClientManager):
        """初始化服务

        Args:
            client_manager: 客户端管理器
        """
        self.client_manager = client_manager

    async def send_message_to_clients(self, clients: List[SseClient], message: SseMessage) -> bool:
        """向客户端列表发送消息

        Args:
            clients: 客户端列表
            message: 要发送的消息

        Returns:
            bool: 是否成功发送
        """
        if not clients:
            logger.warning("没有可用的SSE客户端")
            return False

        # 构建请求
        request_id = str(uuid.uuid4())

        for client in clients:
            # 创建请求和响应等待对象
            response_future = asyncio.Future()

            # 注册响应处理器
            async def handle_response(response_data: BaseModel, future=response_future) -> bool:
                # 使用字典转换访问属性，避免类型检查问题
                data_dict = response_data.dict() if hasattr(response_data, "dict") else {}
                success = data_dict.get("success", False)
                future.set_result(success)
                return True

            client.register_handler(request_id, handle_response)

            try:
                # 发送消息请求
                await client.send_event(
                    SseEvent(
                        event="send_message",
                        data=SseRequest(
                            request_id=request_id,
                            data={
                                "channel_id": message.channel_id,
                                "segments": [segment.model_dump() for segment in message.segments],
                            },
                        ),
                    ),
                )

                # 等待响应，设置超时
                try:
                    result = await asyncio.wait_for(response_future, timeout=15)
                    if result:
                        return True
                except asyncio.TimeoutError:
                    logger.warning(f"等待客户端 {client.client_id} 响应超时")
                    continue

            except Exception as e:
                logger.error(f"向客户端 {client.client_id} 发送消息异常: {e}")
                continue

        # 所有客户端均发送失败
        return False

    async def _request_from_client(
        self,
        request_type: str,
        data: Dict[str, Any],
        timeout: float = 10.0,
    ) -> Optional[Dict[str, Any]]:
        """向任一可用客户端发送请求

        Args:
            request_type: 请求类型
            data: 请求数据
            timeout: 超时时间（秒）

        Returns:
            Optional[Dict[str, Any]]: 响应数据，失败则返回None
        """
        # 获取任一可用客户端
        clients = list(self.client_manager.clients.values())
        if not clients:
            logger.warning("没有可用的SSE客户端")
            return None

        client = clients[0]
        request_id = str(uuid.uuid4())

        # 创建请求和响应等待对象
        response_future = asyncio.Future()

        # 注册响应处理器
        async def handle_response(response_data: BaseModel, future=response_future) -> bool:
            # 使用字典转换访问属性，避免类型检查问题
            data_dict = response_data.dict() if hasattr(response_data, "dict") else {}
            success = data_dict.get("success", False)

            if success:
                future.set_result(data_dict.get("data", {}))
            else:
                future.set_result(None)
            return True

        client.register_handler(request_id, handle_response)

        try:
            # 发送请求
            await client.send_event(
                SseEvent(
                    event=request_type,
                    data=SseRequest(
                        request_id=request_id,
                        data=data,
                    ),
                ),
            )

            # 等待响应，设置超时
            return await asyncio.wait_for(response_future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"等待客户端 {client.client_id} 响应超时: {request_type}")
            return None
        except Exception as e:
            logger.error(f"向客户端 {client.client_id} 发送请求异常: {request_type}, {e}")
            return None

    async def get_self_info(self) -> Optional[SseUserInfo]:
        """获取机器人自身信息

        Returns:
            Optional[SseUserInfo]: 机器人信息，失败则返回None
        """
        response = await self._request_from_client("get_self_info", {})

        if not response:
            return None

        try:
            return SseUserInfo(**response)
        except Exception as e:
            logger.error(f"解析机器人信息失败: {e}")
            return None

    async def get_user_info(self, user_id: str) -> Optional[SseUserInfo]:
        """获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            Optional[SseUserInfo]: 用户信息，失败则返回None
        """
        response = await self._request_from_client(
            "get_user_info",
            {
                "user_id": user_id,
            },
        )

        if not response:
            return None

        try:
            return SseUserInfo(**response)
        except Exception as e:
            logger.error(f"解析用户信息失败: {e}")
            return None

    async def get_channel_info(self, channel_id: str) -> Optional[SseChannelInfo]:
        """获取频道信息

        Args:
            channel_id: 频道ID

        Returns:
            Optional[SseChannelInfo]: 频道信息，失败则返回None
        """
        response = await self._request_from_client(
            "get_channel_info",
            {
                "channel_id": channel_id,
            },
        )

        if not response:
            return None

        try:
            return SseChannelInfo(**response)
        except Exception as e:
            logger.error(f"解析频道信息失败: {e}")
            return None

    async def set_message_reaction(self, message_id: str, status: bool = True) -> bool:
        """设置消息反应

        Args:
            message_id: 消息ID
            status: 反应状态

        Returns:
            bool: 是否设置成功
        """
        response = await self._request_from_client(
            "set_message_reaction",
            {
                "message_id": message_id,
                "status": status,
            },
        )

        return response is not None
