from __future__ import annotations

"""
SSE 客户端SDK
============

用于开发与SSE适配器通信的客户端的SDK。
提供消息模型、通信工具和事件处理框架。
"""

import asyncio
import base64
import contextlib
import hashlib
import json
import time
import uuid
from functools import wraps
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union, cast

import httpx
from loguru import logger
from pydantic import BaseModel, Field

from .chunk_receiver import ChunkReceiver

# 从统一模型导入所需的类型
from .models import (
    AtSegment,
    ChannelInfo,
    ChunkComplete,
    ChunkData,
    ClientCommand,
    FileChunkResponse,
    FileSegment,
    GetChannelInfoRequest,
    GetSelfInfoRequest,
    GetUserInfoRequest,
    ImageSegment,
    MessageSegment,
    MessageSegmentUnion,
    ReceiveMessage,
    RequestType,
    SendMessage,
    SendMessageRequest,
    SendMessageResponse,
    SetMessageReactionRequest,
    SetMessageReactionResponse,
    TextSegment,
    UserInfo,
    at,
    file,
    image,
    text,
)
from .utils import retry_decorator

# 添加返回类型变量T用于泛型函数
T = TypeVar("T")


# 事件处理器类型
EventHandler = Callable[[str, Any], Awaitable[Optional[BaseModel]]]


class SSEClient:
    """SSE客户端"""

    def __init__(
        self,
        server_url: str,
        platform: str,
        client_name: str,
        client_version: str,
        access_key: Optional[str] = None,
        auto_reconnect: bool = True,
        reconnect_interval: int = 5,
        set_logger: Any = None,
    ):
        """初始化SSE客户端

        Args:
            server_url: 服务器URL，例如 http://localhost:8080
            platform: 平台标识，例如 wechat, qq, telegram 等
            client_name: 客户端名称
            client_version: 客户端版本号
            access_key: 访问密钥（可选）
            auto_reconnect: 是否自动重连
            reconnect_interval: 重连间隔（秒）
            set_logger: 自定义logger对象，不设置则使用默认的loguru logger
        """
        self.server_url = server_url.rstrip("/")
        self.platform = platform
        self.client_name = client_name
        self.client_version = client_version
        self.access_key = access_key
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.logger = set_logger or logger

        self.client_id: Optional[str] = None
        self.session: Optional[httpx.AsyncClient] = None
        self.sse_task: Optional[asyncio.Task] = None
        self.subscribed_channels: set[str] = set()
        self.running = False
        self.event_handlers: Dict[str, EventHandler] = {}

        # 分块接收相关（仅用于接收服务端推送的大文件）
        self.chunk_buffers: Dict[str, Any] = (
            {}
        )  # chunk_id -> {chunks: [], total_chunks: int, ...}
        self.chunk_timeouts: Dict[str, float] = {}  # chunk_id -> timeout_timestamp
        self.chunk_timeout_duration = 300  # 5分钟超时

        # 响应发送队列和重试机制
        self.pending_responses: asyncio.Queue = asyncio.Queue()  # 待发送的响应队列
        self.response_retry_task: Optional[asyncio.Task] = None  # 响应重试后台任务
        self.max_response_retries = 5  # 响应最大重试次数
        self.response_retry_interval = 2.0  # 响应重试间隔(秒)

        # 统计信息(用于诊断)
        self.stats = {
            "total_events_received": 0,
            "total_responses_sent": 0,
            "total_responses_failed": 0,
            "total_responses_retried": 0,
            "total_responses_abandoned": 0,
        }

        # 实例化分块接收器
        self._chunk_receiver = ChunkReceiver(self._on_file_received)

        # 注册默认事件处理器
        self.register_handler(RequestType.SEND_MESSAGE.value, self._handle_send_message)
        self.register_handler(
            RequestType.GET_USER_INFO.value, self._handle_get_user_info,
        )
        self.register_handler(
            RequestType.GET_CHANNEL_INFO.value, self._handle_get_channel_info,
        )
        self.register_handler(
            RequestType.GET_SELF_INFO.value, self._handle_get_self_info,
        )
        self.register_handler(
            RequestType.SET_MESSAGE_REACTION.value, self._handle_set_message_reaction,
        )
        self.register_handler(
            RequestType.FILE_CHUNK.value,
            lambda _, data: self._chunk_receiver.handle_file_chunk(data),
        )
        self.register_handler(
            RequestType.FILE_CHUNK_COMPLETE.value,
            lambda _, data: self._async_wrapper(
                self._chunk_receiver.handle_file_chunk_complete(data),
            ),
        )

    def _create_session(self) -> httpx.AsyncClient:
        """创建并配置httpx.AsyncClient"""
        # httpx的超时配置
        timeout = httpx.Timeout(
            connect=30.0,  # 连接超时
            read=300.0,    # 读取超时
            write=30.0,    # 写入超时
            pool=10.0,     # 连接池超时
        )
        
        # httpx的连接限制配置
        limits = httpx.Limits(
            max_connections=100,      # 最大连接数
            max_keepalive_connections=30,  # 最大保活连接数
            keepalive_expiry=300.0,   # 保活过期时间
        )
        
        return httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
            http2=True,  # 启用HTTP/2支持,提升性能
        )

    def _convert_dict_to_segment(self, seg_dict: Dict[str, Any]) -> MessageSegmentUnion:
        """将字典转换为具体的消息段对象

        Args:
            seg_dict: 消息段字典

        Returns:
            MessageSegmentUnion: 具体的消息段对象
        """
        if not isinstance(seg_dict, dict):
            # 如果已经是消息段对象，直接返回
            return cast(MessageSegmentUnion, seg_dict)

        seg_type = seg_dict.get("type")

        try:
            if seg_type == "text":
                return TextSegment(**seg_dict)
            if seg_type == "image":
                return ImageSegment(**seg_dict)
            if seg_type == "file":
                return FileSegment(**seg_dict)
            if seg_type == "at":
                return AtSegment(**seg_dict)
            # 默认返回文本段
            return text(seg_dict.get("content", str(seg_dict)))
        except Exception as e:
            # 如果转换失败，降级为文本段
            self.logger.warning(f"消息段转换失败，降级为文本段: {e}")
            return text(seg_dict.get("content", str(seg_dict)))

    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """注册事件处理器

        Args:
            event_type: 事件类型
            handler: 处理器函数，接收事件数据，返回响应数据
        """
        self.event_handlers[event_type] = handler

    async def start(self) -> None:
        """启动客户端"""
        if self.running:
            self.logger.info("客户端已经在运行")
            return

        self.session = self._create_session()
        self.running = True
        await self._chunk_receiver.start()

        if not await self.register():
            self.logger.error("客户端注册失败，启动中止")
            await self.stop()
            return

        self.sse_task = asyncio.create_task(self._connect_sse())

        # 启动响应重试后台任务
        if self.response_retry_task is None or self.response_retry_task.done():
            self.response_retry_task = asyncio.create_task(self._response_retry_loop())

    async def stop(self) -> None:
        """停止客户端"""
        if not self.running:
            return
        self.running = False
        await self._chunk_receiver.stop()

        if self.sse_task:
            self.sse_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.sse_task
            self.sse_task = None

        # 停止响应重试任务
        if self.response_retry_task:
            self.response_retry_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.response_retry_task
            self.response_retry_task = None

        if self.session:
            await self.session.aclose()
            self.session = None
        self.logger.info("客户端已停止")

    @retry_decorator(retry_count=3, initial_delay=1.0, max_delay=5.0)
    async def _post_command(
        self, command: "ClientCommand", data: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """向服务端发送POST命令的辅助方法

        自动重试3次，使用指数退避策略
        """
        if not self.session:
            raise RuntimeError("客户端会话未启动")

        url = f"{self.server_url}/api/adapters/sse/connect"
        payload = data or {}
        payload["cmd"] = command.value

        headers = {}
        if self.client_id:
            headers["X-Client-ID"] = self.client_id
        if self.access_key:
            headers["X-Access-Key"] = self.access_key

        try:
            # 使用json.dumps进行序列化，以正确显示枚举等特殊类型
            # 使用default=str来处理一些无法直接序列化的类型
            payload_json = json.dumps(payload, ensure_ascii=False, default=str)
            payload_json = (
                payload_json[:256] + "..." + payload_json[-256:]
                if len(payload_json) > 512
                else payload_json
            )
            self.logger.debug(
                f"发送命令: {command.value}, URL: {url}, Payload: {payload_json}",
            )
        except Exception:
            # 如果序列化失败，回退到原始方式，并记录警告
            self.logger.warning("日志记录时序列化Payload失败，回退到原始格式")
            payload_str = str(payload)
            payload_str = (
                payload_str[:256] + "..." + payload_str[-256:]
                if len(payload_str) > 512
                else payload_str
            )
            self.logger.debug(
                f"发送命令: {command.value}, URL: {url}, Payload: {payload}",
            )

        return await self.session.post(url, json=payload, headers=headers)

    async def register(self) -> bool:
        """注册客户端"""
        register_data = {
            "platform": self.platform,
            "client_name": self.client_name,
            "client_version": self.client_version,
        }
        try:
            response = await self._post_command(ClientCommand.REGISTER, register_data)
        except Exception:
            self.logger.exception("注册过程中发生异常")
            return False
        else:
            if response.status_code == 200:
                result = response.json()
                self.client_id = result.get("client_id")
                self.logger.success(f"客户端注册成功: {self.client_id}")
                return True

            error_text = response.text
            self.logger.error(f"客户端注册失败 ({response.status_code}): {error_text}")
            return False

    async def _connect_sse(self) -> None:
        """连接并处理SSE事件流"""
        if not self.session:
            self.session = self._create_session()

        retry_count = 0
        max_retries = -1 if self.auto_reconnect else 0

        while self.running and (max_retries == -1 or retry_count <= max_retries):
            try:
                url = f"{self.server_url}/api/adapters/sse/connect?client_name={self.client_name}&platform={self.platform}"
                if self.client_id:
                    url += f"&client_id={self.client_id}"
                if self.access_key:
                    url += f"&access_key={self.access_key}"

                self.logger.info(f"连接SSE URL: {url}")
                assert self.session is not None
                
                # httpx使用stream方式处理SSE
                async with self.session.stream("GET", url) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        self.logger.error(
                            f"SSE连接失败 ({response.status_code}): {error_text.decode('utf-8')}",
                        )
                        if not self.auto_reconnect:
                            break
                        await asyncio.sleep(self.reconnect_interval)
                        retry_count += 1
                        continue

                    retry_count = 0
                    self.logger.success("SSE连接成功，开始处理事件流")
                    await self._process_sse_stream(response)

            except asyncio.CancelledError:
                self.logger.info("SSE连接任务已取消")
                break
            except Exception:
                self.logger.exception("SSE连接出现异常")
                if not self.auto_reconnect:
                    break
                await asyncio.sleep(self.reconnect_interval)
                retry_count += 1

            if self.running and self.auto_reconnect:
                self.logger.info(f"{self.reconnect_interval}秒后尝试重连...")
                await asyncio.sleep(self.reconnect_interval)

    async def _process_sse_stream(self, response: httpx.Response) -> None:
        """从响应中处理SSE事件流"""
        event_type, event_data = None, ""
        
        # httpx使用aiter_lines()逐行读取流式响应
        async for line in response.aiter_lines():
            if not self.running:
                break
            
            line = line.strip()
            if not line:
                if event_type and event_data:
                    await self._dispatch_event(event_type, event_data)
                event_type, event_data = None, ""
                continue
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                event_data += line[5:].strip()

    async def _dispatch_event(self, event_type: str, event_data: str) -> None:
        """解析并分发SSE事件"""
        try:
            data = json.loads(event_data)
        except json.JSONDecodeError:
            self.logger.warning(f"无法解析事件数据为JSON: {event_data}")
            data = {"text": event_data}

        if event_type == "connected":
            self.logger.info(f"SSE连接成功: {data}")
            self.client_id = data.get("client_id", self.client_id)
            for channel_id in list(self.subscribed_channels):
                await self.subscribe_channel(channel_id)
        elif event_type == "heartbeat":
            pass
        elif event_type in self.event_handlers:
            await self._handle_registered_event(event_type, data)
        else:
            self.logger.warning(f"收到未知事件类型: {event_type}")

    async def _handle_registered_event(
        self, event_type: str, data: Dict[str, Any],
    ) -> None:
        """处理已注册的事件"""
        self.stats["total_events_received"] += 1

        request_id = data.get("request_id")
        request_data = data.get("data", {})
        handler = self.event_handlers[event_type]

        model_map = {
            RequestType.SEND_MESSAGE.value: SendMessageRequest,
            RequestType.GET_USER_INFO.value: GetUserInfoRequest,
            RequestType.GET_CHANNEL_INFO.value: GetChannelInfoRequest,
            RequestType.GET_SELF_INFO.value: GetSelfInfoRequest,
            RequestType.SET_MESSAGE_REACTION.value: SetMessageReactionRequest,
        }
        model = model_map.get(event_type)

        # 无论如何都要确保发送响应
        response_sent = False

        try:
            pydantic_data = model(**request_data) if model else request_data
            result = await handler(event_type, pydantic_data)

            if request_id and result:
                # 业务处理成功,发送成功响应
                response_sent = await self._send_response(
                    request_id, True, result.model_dump(),
                )
                if not response_sent:
                    self.logger.warning(
                        f"事件 '{event_type}' 处理成功,但响应发送失败,已加入重试队列 (req_id: {request_id})",
                    )
            elif request_id and not result:
                # handler返回None,也算处理完成,发送空响应
                self.logger.warning(
                    f"事件 '{event_type}' 处理器返回None (req_id: {request_id})",
                )
                response_sent = await self._send_response(request_id, True, {})

        except Exception as e:
            self.logger.exception(f"处理事件 '{event_type}' 时发生异常")
            if request_id:
                # 业务处理失败,发送失败响应
                response_sent = await self._send_response(
                    request_id, False, {"error": str(e)},
                )
                if not response_sent:
                    self.logger.warning(
                        f"事件 '{event_type}' 处理失败,且错误响应也发送失败,已加入重试队列 (req_id: {request_id})",
                    )

        # 最终检查:如果request_id存在但响应没有发送,强制加入队列
        if request_id and not response_sent:
            self.logger.error(f"响应未能发送,强制加入重试队列 (req_id: {request_id})")
            await self._enqueue_response_for_retry(
                request_id,
                False,
                {"error": "响应发送失败"},
                retry_count=0,
            )

    async def subscribe_channel(self, channel_ids: Union[str, List[str]]) -> bool:
        """订阅频道"""
        channels = [channel_ids] if isinstance(channel_ids, str) else channel_ids
        try:
            response = await self._post_command(
                ClientCommand.SUBSCRIBE, {"channel_ids": channels},
            )
        except Exception:
            self.logger.exception(f"订阅频道 {channels} 异常")
            return False
        else:
            if response.status_code == 200:
                for channel_id in channels:
                    self.subscribed_channels.add(channel_id)
                self.logger.success(f"订阅频道成功: {channels}")
                return True
            self.logger.error(
                f"订阅频道失败 ({response.status_code}): {response.text}",
            )
            return False

    async def unsubscribe_channel(self, channel_ids: Union[str, List[str]]) -> bool:
        """取消订阅频道"""
        channels = [channel_ids] if isinstance(channel_ids, str) else channel_ids
        try:
            response = await self._post_command(
                ClientCommand.UNSUBSCRIBE, {"channel_ids": channels},
            )
        except Exception:
            self.logger.exception(f"取消订阅频道 {channels} 异常")
            return False
        else:
            if response.status_code == 200:
                for channel_id in channels:
                    self.subscribed_channels.discard(channel_id)
                self.logger.success(f"取消订阅频道成功: {channels}")
                return True
            self.logger.error(
                f"取消订阅失败 ({response.status_code}): {response.text}",
            )
            return False

    async def send_message(self, channel_id: str, message: ReceiveMessage) -> bool:
        """发送消息到服务器"""
        try:
            command_data = {"channel_id": channel_id, "message": message.model_dump()}
            response = await self._post_command(ClientCommand.MESSAGE, command_data)
        except Exception:
            self.logger.exception(f"发送消息到 {channel_id} 异常")
            return False
        else:
            if response.status_code == 200:
                self.logger.success(f"消息发送成功: {channel_id}")
                return True
            self.logger.exception(
                f"消息发送失败 ({response.status_code}): {response.text}",
            )
            return False

    async def _send_response(
        self, request_id: str, success: bool, data: Dict[str, Any],
    ) -> bool:
        """向服务器发送响应

        如果立即发送失败,会将响应加入队列进行异步重试
        """
        response_data = {"request_id": request_id, "success": success, "data": data}

        # 尝试立即发送
        try:
            response = await self._post_command(ClientCommand.RESPONSE, response_data)
            if response.status_code == 200:
                self.logger.debug(f"响应发送成功 (req_id: {request_id})")
                self.stats["total_responses_sent"] += 1
                return True

            # HTTP状态码非200,记录警告并加入重试队列
            self.logger.warning(
                f"响应发送失败 HTTP {response.status_code} (req_id: {request_id}), 加入重试队列",
            )
            self.stats["total_responses_failed"] += 1
            await self._enqueue_response_for_retry(
                request_id, success, data, retry_count=0,
            )

        except Exception as e:
            # 网络异常或其他错误,加入重试队列
            self.logger.warning(
                f"响应发送异常 (req_id: {request_id}): {e}, 加入重试队列",
            )
            self.stats["total_responses_failed"] += 1
            await self._enqueue_response_for_retry(
                request_id, success, data, retry_count=0,
            )
            return False
        else:
            return False

    async def _enqueue_response_for_retry(
        self,
        request_id: str,
        success: bool,
        data: Dict[str, Any],
        retry_count: int,
    ) -> None:
        """将响应加入重试队列"""
        retry_item = {
            "request_id": request_id,
            "success": success,
            "data": data,
            "retry_count": retry_count,
            "enqueued_at": time.time(),
        }
        await self.pending_responses.put(retry_item)
        self.logger.debug(
            f"响应已加入重试队列 (req_id: {request_id}, 重试次数: {retry_count})",
        )

    async def _response_retry_loop(self) -> None:
        """响应重试后台循环任务"""
        self.logger.info("响应重试后台任务已启动")

        while self.running:
            try:
                # 从队列中获取待重试的响应(超时时间避免无限阻塞)
                try:
                    retry_item = await asyncio.wait_for(
                        self.pending_responses.get(),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    continue

                request_id = retry_item["request_id"]
                success = retry_item["success"]
                data = retry_item["data"]
                retry_count = retry_item["retry_count"]

                # 检查是否超过最大重试次数
                if retry_count >= self.max_response_retries:
                    self.logger.error(
                        f"响应重试次数已达上限 {self.max_response_retries}, 放弃 (req_id: {request_id})",
                    )
                    self.stats["total_responses_abandoned"] += 1
                    continue

                # 等待一段时间后重试
                await asyncio.sleep(self.response_retry_interval)

                # 尝试重新发送响应
                self.logger.info(
                    f"正在重试发送响应 (req_id: {request_id}, 第 {retry_count + 1} 次重试)",
                )

                response_data = {
                    "request_id": request_id,
                    "success": success,
                    "data": data,
                }

                try:
                    response = await self._post_command(
                        ClientCommand.RESPONSE, response_data,
                    )

                    if response.status_code == 200:
                        self.logger.success(
                            f"响应重试发送成功 (req_id: {request_id}, 重试 {retry_count + 1} 次)",
                        )
                        self.stats["total_responses_sent"] += 1
                        self.stats["total_responses_retried"] += 1
                    else:
                        # 仍然失败,继续加入队列
                        self.logger.warning(
                            f"响应重试失败 HTTP {response.status_code} (req_id: {request_id}, 第 {retry_count + 1} 次重试)",
                        )
                        await self._enqueue_response_for_retry(
                            request_id,
                            success,
                            data,
                            retry_count + 1,
                        )

                except Exception as e:
                    self.logger.warning(
                        f"响应重试异常 (req_id: {request_id}, 第 {retry_count + 1} 次重试): {e}",
                    )
                    await self._enqueue_response_for_retry(
                        request_id,
                        success,
                        data,
                        retry_count + 1,
                    )

            except asyncio.CancelledError:
                self.logger.info("响应重试后台任务已取消")
                break
            except Exception:
                self.logger.exception("响应重试后台任务发生未预期的异常")
                await asyncio.sleep(1.0)

        self.logger.info("响应重试后台任务已退出")

    # 以下方法为默认事件处理器，需要被子类重写
    async def _handle_send_message(
        self, _event_type: str, data: SendMessageRequest,
    ) -> SendMessageResponse:
        """处理发送消息请求（可重写）"""
        self.logger.info(f"收到发送消息请求: {data.model_dump_json(indent=2)}")
        # 默认实现：打印日志并模拟成功
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        return SendMessageResponse(message_id=message_id, success=True)

    async def _handle_get_user_info(
        self, _event_type: str, data: GetUserInfoRequest,
    ) -> UserInfo:
        """处理获取用户信息请求（可重写）"""
        self.logger.info(f"收到获取用户信息请求: {data.user_id}")
        # 默认实现：返回模拟数据
        return UserInfo(
            user_id=data.user_id,
            user_name=f"用户_{data.user_id}",
            platform_name=self.platform,
            user_avatar=None,
            user_nickname=None,
        )

    async def _handle_get_channel_info(
        self, _event_type: str, data: GetChannelInfoRequest,
    ) -> ChannelInfo:
        """处理获取频道信息请求（可重写）"""
        self.logger.info(f"收到获取频道信息请求: {data.channel_id}")
        # 默认实现：返回模拟数据
        return ChannelInfo(
            channel_id=data.channel_id,
            channel_name=f"频道_{data.channel_id}",
            channel_avatar=None,
            member_count=None,
            owner_id=None,
            is_admin=False,
        )

    async def _handle_get_self_info(
        self, _event_type: str, _data: GetSelfInfoRequest,
    ) -> UserInfo:
        """处理获取自身信息请求（可重写）"""
        self.logger.info("收到获取自身信息请求")
        # 默认实现：返回模拟数据
        return UserInfo(
            user_id="self_id",
            user_name="我自己",
            platform_name=self.platform,
            user_avatar=None,
            user_nickname=None,
        )

    async def _handle_set_message_reaction(
        self,
        _event_type: str,
        data: SetMessageReactionRequest,
    ) -> SetMessageReactionResponse:
        """处理设置消息反应请求（可重写）"""
        self.logger.info(f"收到设置消息反应请求: {data.message_id} -> {data.status}")
        # 默认实现：简单返回成功
        return SetMessageReactionResponse(
            success=True, message=f"消息反应设置{'成功' if data.status else '取消'}",
        )

    async def _on_file_received(
        self, filename: str, file_bytes: bytes, mime_type: str, _file_type: str,
    ) -> None:
        """文件接收完成回调（可重写）"""
        self.logger.info(f"收到文件: {filename} ({len(file_bytes)} bytes, {mime_type})")
        # 默认实现：保存文件到当前目录
        try:
            safe_filename = (
                "".join(c for c in filename if c.isalnum() or c in "._-")
                or f"file_{int(time.time())}"
            )
            file_path = Path(safe_filename)
            file_path.write_bytes(file_bytes)
            self.logger.success(f"文件已保存: {file_path}")
        except Exception:
            self.logger.exception("保存文件失败")

    async def _async_wrapper(self, result: Any) -> Any:
        """简单的异步包装器"""
        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息

        Returns:
            Dict: 包含各项统计数据的字典
        """
        return {
            **self.stats,
            "pending_responses_count": self.pending_responses.qsize(),
            "client_running": self.running,
            "client_id": self.client_id,
            "subscribed_channels_count": len(self.subscribed_channels),
        }
