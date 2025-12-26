"""
SSE 服务层
=========

提供高层业务逻辑实现，封装与客户端的交互。

主要功能:
1. 消息发送
2. 用户信息获取
3. 频道信息获取
4. 消息反应设置
5. 大文件分块推送（解决客户端接收时的"chunk too big"问题）

注意：分块传输是服务端向客户端推送大文件时使用，避免SSE事件过大导致客户端接收错误。
"""

import asyncio
import math
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    from nekro_agent.adapters.sse.adapter import SSEAdapter

from nekro_agent.adapters.sse.sdk.models import (
    ChannelInfo,
    ChunkComplete,
    ChunkData,
    Event,
    GetChannelInfoRequest,
    GetSelfInfoRequest,
    GetUserInfoRequest,
    Request,
    RequestType,
    SendMessage,
    SetMessageReactionRequest,
    SetMessageReactionResponse,
    UserInfo,
)
from nekro_agent.core import logger

from .client import SseClient, SseClientManager

# 分块大小配置
CHUNK_SIZE = 64 * 1024  # 64KB per chunk
MAX_BASE64_SIZE = 1 * 1024 * 1024  # 1MB，超过此大小进行分块传输


class SseApiService:
    """SSE API 服务

    封装与客户端的交互逻辑
    """

    def __init__(
        self,
        client_manager: SseClientManager,
        adapter: Optional["SSEAdapter"] = None,
    ):
        """初始化服务

        Args:
            client_manager: 客户端管理器
            adapter: SSE适配器实例，用于动态获取配置（支持热更新）
        """
        self.client_manager = client_manager
        self.adapter = adapter
    
    @property
    def response_timeout(self) -> float:
        """动态获取响应超时配置（支持热更新）"""
        if self.adapter:
            return self.adapter.config.RESPONSE_TIMEOUT
        return 30.0  # 默认值
    
    @property
    def ignore_response(self) -> bool:
        """动态获取忽略回执配置（支持热更新）"""
        if self.adapter:
            return self.adapter.config.IGNORE_RESPONSE
        return False  # 默认值

    def _should_use_chunked_transfer(self, data: str) -> bool:
        """判断是否应该使用分块传输

        Args:
            data: base64编码的数据

        Returns:
            bool: 是否使用分块传输
        """
        # 估算base64数据的原始大小（base64比原始数据大约33%）
        estimated_size = len(data) * 3 // 4
        return estimated_size > MAX_BASE64_SIZE

    async def _send_chunked_data(self, client: SseClient, data: str, mime_type: str, filename: str, file_type: str) -> bool:
        """分块发送大数据

        Args:
            client: 目标客户端
            data: base64编码的数据
            mime_type: MIME类型
            filename: 文件名
            file_type: 文件类型 (image/file)

        Returns:
            bool: 是否发送成功
        """
        chunk_id = str(uuid.uuid4())
        total_size = len(data) * 3 // 4  # 估算原始大小
        total_chunks = math.ceil(len(data) / CHUNK_SIZE)

        logger.info(f"开始分块传输: {filename}, 大小: {total_size} bytes, 分块数: {total_chunks}")

        try:
            # 发送所有分块
            for i in range(total_chunks):
                start_pos = i * CHUNK_SIZE
                end_pos = min(start_pos + CHUNK_SIZE, len(data))
                chunk_data = data[start_pos:end_pos]

                chunk_event = Event(
                    event=RequestType.FILE_CHUNK.value,
                    data=ChunkData(
                        chunk_id=chunk_id,
                        chunk_index=i,
                        total_chunks=total_chunks,
                        chunk_data=chunk_data,
                        chunk_size=len(chunk_data),
                        total_size=total_size,
                        mime_type=mime_type,
                        filename=filename,
                        file_type=file_type,
                    ),
                )

                await client.send_event(chunk_event)
                logger.debug(f"发送分块 {i+1}/{total_chunks}: {len(chunk_data)} bytes")

                # 稍微延迟以避免过快发送导致客户端处理不过来
                await asyncio.sleep(0.01)

            # 发送传输完成事件
            complete_event = Event(
                event=RequestType.FILE_CHUNK_COMPLETE.value,
                data=ChunkComplete(chunk_id=chunk_id, success=True, message=f"文件 {filename} 传输完成"),
            )
            await client.send_event(complete_event)

        except Exception as e:
            logger.error(f"分块传输失败: {filename}, 错误: {e}")

            # 发送传输失败事件
            try:
                error_event = Event(
                    event=RequestType.FILE_CHUNK_COMPLETE.value,
                    data=ChunkComplete(chunk_id=chunk_id, success=False, message=f"文件 {filename} 传输失败: {e!s}"),
                )
                await client.send_event(error_event)
            except Exception:
                pass  # 忽略发送错误事件的异常

            return False
        else:
            logger.success(f"分块传输完成: {filename}")
            return True

    async def send_message_to_clients(self, clients: List[SseClient], message: SendMessage) -> bool:
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

        # 检查消息段是否包含大文件，直接分块发送
        has_large_files = await self._process_large_files(message, clients)

        # 如果包含大文件，直接返回成功（文件已通过分块方式发送）
        if has_large_files:
            logger.info("消息包含大文件，已通过分块方式发送")
            return True

        # 普通消息正常发送
        return await self._send_normal_message(clients, message)

    async def _send_normal_message(self, clients: List[SseClient], message: SendMessage) -> bool:
        """发送普通消息（不包含大文件）

        Args:
            clients: 客户端列表
            message: 要发送的消息

        Returns:
            bool: 是否成功发送
        """
        # 如果启用了忽略回执模式，直接发送消息并返回成功
        if self.ignore_response:
            logger.warning("⚠️ 已启用忽略回执模式，将不等待客户端确认直接返回成功")
            for client in clients:
                request_id = str(uuid.uuid4())
                try:
                    await client.send_event(
                        Event(
                            event=RequestType.SEND_MESSAGE.value,
                            data=Request(
                                request_id=request_id,
                                data={
                                    "channel_id": message.channel_id,
                                    "channel_name": message.channel_name,
                                    "segments": [segment.model_dump() for segment in message.segments],
                                },
                            ),
                        ),
                    )
                except Exception as e:
                    logger.error(f"向客户端 {client.client_id} 推送消息异常: {e}")
                    continue
                else:
                    logger.info(f"消息已推送到客户端 {client.client_id} (忽略回执模式)")
                    return True  # 只要成功推送到一个客户端就返回成功
            # 所有客户端推送失败
            return False
        
        # 正常模式：等待客户端回执
        for client in clients:
            # 每个客户端使用独立的 request_id
            request_id = str(uuid.uuid4())
            # 创建请求和响应等待对象
            response_future: asyncio.Future[bool] = asyncio.Future()

            # 注册响应处理器（使用默认参数绑定循环变量）
            async def handle_response(
                response_data: BaseModel,
                future: asyncio.Future[bool] = response_future,
                req_id: str = request_id,
            ) -> bool:
                # 检查 Future 状态，避免在已取消或已完成的 Future 上设置结果
                if future.done():
                    logger.warning(f"响应处理器被调用，但 Future 已完成/取消 (request_id={req_id})")
                    return False

                # 使用字典转换访问属性，避免类型检查问题
                data_dict = response_data.dict() if hasattr(response_data, "dict") else {}
                success = data_dict.get("success", False)

                try:
                    future.set_result(success)
                except Exception as e:
                    logger.error(f"设置 Future 结果失败: {e}")
                    return False
                else:
                    return True

            client.register_handler(request_id, handle_response)

            try:
                # 发送消息请求
                await client.send_event(
                    Event(
                        event=RequestType.SEND_MESSAGE.value,
                        data=Request(
                            request_id=request_id,
                            data={
                                "channel_id": message.channel_id,
                                "channel_name": message.channel_name,
                                "segments": [segment.model_dump() for segment in message.segments],
                            },
                        ),
                    ),
                )

                # 等待响应，设置超时
                try:
                    result = await asyncio.wait_for(response_future, timeout=self.response_timeout)
                    if result:
                        return True
                except asyncio.TimeoutError:
                    logger.warning(
                        f"等待客户端 {client.client_id} 响应超时 "
                        f"(request_id={request_id}, timeout={self.response_timeout}s)",
                    )
                    # 超时后取消 Future 并清理 handler，防止延迟响应触发回调
                    if not response_future.done():
                        response_future.cancel()
                    # 注意：handler 已在 handle_response 中被 pop，但如果超时它仍可能存在
                    # 为了保险起见，显式清理
                    handler_name = f"_request_{request_id}"
                    client.handlers.pop(handler_name, None)
                    continue

            except Exception as e:
                logger.error(f"向客户端 {client.client_id} 发送消息异常: {e}")
                # 清理 handler
                handler_name = f"_request_{request_id}"
                client.handlers.pop(handler_name, None)
                continue

        # 所有客户端均发送失败
        return False

    async def _process_large_files(self, message: SendMessage, clients: List[SseClient]) -> bool:
        """检查并处理消息中的大文件，对大文件进行分块传输

        Args:
            message: 原始消息
            clients: 目标客户端列表

        Returns:
            bool: 是否包含大文件（已分块发送）
        """
        has_large_files = False

        for segment in message.segments:
            segment_dict = segment.model_dump()
            segment_type = segment_dict.get("type")

            # 检查是否是图片或文件段，且包含大的base64数据
            if segment_type in ["image", "file"]:
                base64_url = segment_dict.get("base64_url", "")

                if base64_url and base64_url.startswith("data:"):
                    # 提取base64数据部分
                    try:
                        header, data = base64_url.split(",", 1)
                        mime_type = header.split(";")[0].split(":")[1] if ":" in header else "application/octet-stream"

                        if self._should_use_chunked_transfer(data):
                            # 需要分块传输
                            filename = segment_dict.get("name", f"file_{uuid.uuid4().hex[:8]}")
                            has_large_files = True

                            logger.info(f"检测到大文件 {filename}，开始分块传输")

                            # 向所有客户端分块发送文件
                            for client in clients:
                                success = await self._send_chunked_data(
                                    client,
                                    data,
                                    mime_type,
                                    filename,
                                    segment_type or "file",  # 确保不是None
                                )
                                if not success:
                                    logger.error(f"向客户端 {client.client_id} 分块发送文件失败")

                    except Exception as e:
                        logger.error(f"处理大文件失败: {e}")

        return has_large_files

    async def _request_from_client(
        self,
        request_type: RequestType,
        request_data: BaseModel,
        timeout: Optional[float] = None,
    ) -> Optional[BaseModel]:
        """向任一可用客户端发送请求

        Args:
            request_type: 请求类型
            request_data: 请求数据（BaseModel对象）
            timeout: 超时时间（秒），None则使用默认配置

        Returns:
            Optional[BaseModel]: 响应数据，失败则返回None
        """
        # 使用配置的超时时间或传入的超时时间
        actual_timeout = timeout if timeout is not None else self.response_timeout
        
        # 获取任一可用客户端
        clients = list(self.client_manager.clients.values())
        if not clients:
            logger.warning("没有可用的SSE客户端")
            return None

        client = clients[0]
        request_id = str(uuid.uuid4())

        # 创建请求和响应等待对象
        response_future: asyncio.Future[Optional[BaseModel]] = asyncio.Future()

        # 注册响应处理器（捕获 request_id 到局部变量）
        req_id_for_handler = request_id

        async def handle_response(
            response_data: BaseModel,
            future: asyncio.Future[Optional[BaseModel]] = response_future,
        ) -> bool:
            # 检查 Future 状态，避免在已取消或已完成的 Future 上设置结果
            if future.done():
                logger.warning(f"响应处理器被调用，但 Future 已完成/取消 (request_id={req_id_for_handler}, type={request_type})")
                return False

            # 使用字典转换访问属性，避免类型检查问题
            data_dict = response_data.dict() if hasattr(response_data, "dict") else {}
            success = data_dict.get("success", False)

            try:
                if success:
                    # 直接返回原始响应数据，让调用方进行类型转换
                    future.set_result(response_data)
                else:
                    future.set_result(None)
            except Exception as e:
                logger.error(f"设置 Future 结果失败: {e}")
                return False
            else:
                return True

        client.register_handler(request_id, handle_response)

        try:
            # 发送请求
            await client.send_event(
                Event(
                    event=request_type.value,
                    data=Request(
                        request_id=request_id,
                        data=request_data.model_dump(),
                    ),
                ),
            )

            # 等待响应，设置超时
            return await asyncio.wait_for(response_future, timeout=actual_timeout)
        except asyncio.TimeoutError:
            logger.warning(
                f"等待客户端 {client.client_id} 响应超时: {request_type} "
                f"(request_id={request_id}, timeout={actual_timeout}s)",
            )
            # 超时后取消 Future 并清理 handler
            if not response_future.done():
                response_future.cancel()
            handler_name = f"_request_{request_id}"
            client.handlers.pop(handler_name, None)
            return None
        except Exception as e:
            logger.error(f"向客户端 {client.client_id} 发送请求异常: {request_type}, {e}")
            # 清理 handler
            handler_name = f"_request_{request_id}"
            client.handlers.pop(handler_name, None)
            return None

    async def get_self_info(self) -> Optional[UserInfo]:
        """获取机器人自身信息

        Returns:
            Optional[UserInfo]: 机器人信息，失败则返回None
        """
        response = await self._request_from_client(RequestType.GET_SELF_INFO, GetSelfInfoRequest())

        if not response:
            return None

        try:
            # 从响应中提取data字段并转换为UserInfo
            response_dict = response.dict() if hasattr(response, "dict") else {}
            user_data = response_dict.get("data", {})
            return UserInfo(**user_data)
        except Exception as e:
            logger.error(f"解析机器人信息失败: {e}")
            return None

    async def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        """获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            Optional[UserInfo]: 用户信息，失败则返回None
        """
        response = await self._request_from_client(RequestType.GET_USER_INFO, GetUserInfoRequest(user_id=user_id))

        if not response:
            return None

        try:
            # 从响应中提取data字段并转换为UserInfo
            response_dict = response.dict() if hasattr(response, "dict") else {}
            user_data = response_dict.get("data", {})
            return UserInfo(**user_data)
        except Exception as e:
            logger.error(f"解析用户信息失败: {e}")
            return None

    async def get_channel_info(self, channel_id: str) -> Optional[ChannelInfo]:
        """获取频道信息

        Args:
            channel_id: 频道ID

        Returns:
            Optional[ChannelInfo]: 频道信息，失败则返回None
        """
        response = await self._request_from_client(RequestType.GET_CHANNEL_INFO, GetChannelInfoRequest(channel_id=channel_id))

        if not response:
            return None

        try:
            # 从响应中提取data字段并转换为ChannelInfo
            response_dict = response.dict() if hasattr(response, "dict") else {}
            channel_data = response_dict.get("data", {})
            return ChannelInfo(**channel_data)
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
            RequestType.SET_MESSAGE_REACTION,
            SetMessageReactionRequest(message_id=message_id, status=status),
        )

        if not response:
            return False

        try:
            # 从响应中提取data字段并转换为SetMessageReactionResponse
            response_dict = response.dict() if hasattr(response, "dict") else {}
            reaction_data = response_dict.get("data", {})
            reaction_response = SetMessageReactionResponse(**reaction_data)
        except Exception as e:
            logger.error(f"解析消息反应设置结果失败: {e}")
            return False
        else:
            return reaction_response.success
