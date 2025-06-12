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

import aiohttp
from loguru import logger
from pydantic import BaseModel, Field

# 从统一模型导入所需的类型
from .models import (
    AtSegment,
    ChannelInfo,
    ChunkComplete,
    ChunkData,
    FileChunkResponse,
    FileSegment,
    GetChannelInfoRequest,
    GetSelfInfoRequest,
    GetUserInfoRequest,
    ImageSegment,
    LocationSegment,
    MessageSegment,
    MessageSegmentUnion,
    ReceiveMessage,
    RequestType,
    SendMessage,
    SendMessageRequest,
    SendMessageResponse,
    SetMessageReactionRequest,
    SetMessageReactionResponse,
    StickerSegment,
    TextSegment,
    UserInfo,
    at,
    file,
    image,
    text,
)

# 添加返回类型变量T用于泛型函数
T = TypeVar("T")


# 添加重试装饰器
async def with_retry(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    retry_count: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 5.0,
    backoff_factor: float = 2.0,
    retry_exceptions: tuple = (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ConnectionError,
    ),
    **kwargs: Any,
) -> T:
    """网络请求重试装饰器

    Args:
        func: 异步函数
        retry_count: 最大重试次数
        initial_delay: 初始延迟时间(秒)
        max_delay: 最大延迟时间(秒)
        backoff_factor: 退避系数，每次重试延迟时间为上次的backoff_factor倍
        retry_exceptions: 需要重试的异常类型

    Returns:
        原函数的返回值
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(retry_count + 1):
        try:
            return await func(*args, **kwargs)
        except retry_exceptions as e:
            last_exception = e
            if attempt == retry_count:
                break

            # 记录重试信息
            logger.warning(f"请求失败，正在进行第{attempt+1}次重试: {e!s}")

            # 计算下次重试等待时间（指数退避）
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)

    # 所有重试都失败了，抛出最后一个异常
    if last_exception:
        raise last_exception

    # 理论上不会到这里，但为了类型安全
    raise RuntimeError("重试失败且没有异常")


def retry_decorator(
    retry_count: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 5.0,
    backoff_factor: float = 2.0,
    retry_exceptions: tuple = (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ConnectionError,
    ),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """可配置的重试装饰器

    Args:
        retry_count: 最大重试次数
        initial_delay: 初始延迟时间(秒)
        max_delay: 最大延迟时间(秒)
        backoff_factor: 退避系数，每次重试延迟时间为上次的backoff_factor倍
        retry_exceptions: 需要重试的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await with_retry(
                func,
                *args,
                retry_count=retry_count,
                initial_delay=initial_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                retry_exceptions=retry_exceptions,
                **kwargs,
            )

        return wrapper

    return decorator


# 所有模型类型已从 .models 模块导入，这里不再重复定义


# 消息段构造函数已从 .models 模块导入，这里不再重复定义


# 事件处理器类型
EventHandler = Callable[[str, Any], Awaitable[Optional[Any]]]


class SSEClient:
    """SSE客户端"""

    def __init__(
        self,
        server_url: str,
        platform: str,
        client_name: str,
        client_version: str,
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
            auto_reconnect: 是否自动重连
            reconnect_interval: 重连间隔（秒）
            set_logger: 自定义logger对象，不设置则使用默认的loguru logger
        """
        self.server_url = server_url.rstrip("/")
        self.platform = platform
        self.client_name = client_name
        self.client_version = client_version
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.logger = set_logger or logger

        self.client_id: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.sse_task: Optional[asyncio.Task] = None
        self.subscribed_channels: set[str] = set()
        self.running = False
        self.event_handlers: Dict[str, EventHandler] = {}

        # 分块接收相关（仅用于接收服务端推送的大文件）
        self.chunk_buffers: Dict[str, Any] = {}  # chunk_id -> {chunks: [], total_chunks: int, ...}
        self.chunk_timeouts: Dict[str, float] = {}  # chunk_id -> timeout_timestamp
        self.chunk_timeout_duration = 300  # 5分钟超时

        # 注册默认事件处理器
        self.register_handler(RequestType.SEND_MESSAGE.value, self._handle_send_message)
        self.register_handler(RequestType.GET_USER_INFO.value, self._handle_get_user_info)
        self.register_handler(RequestType.GET_CHANNEL_INFO.value, self._handle_get_channel_info)
        self.register_handler(RequestType.GET_SELF_INFO.value, self._handle_get_self_info)
        self.register_handler(RequestType.SET_MESSAGE_REACTION.value, self._handle_set_message_reaction)
        # 注册分块接收处理器（仅处理服务端推送的大文件）
        self.register_handler(RequestType.FILE_CHUNK.value, self._handle_file_chunk)
        self.register_handler(RequestType.FILE_CHUNK_COMPLETE.value, self._handle_file_chunk_complete)

    def _convert_dict_to_segment(self, seg_dict: Dict[str, Any]) -> MessageSegmentUnion:
        """将字典转换为具体的消息段对象

        Args:
            seg_dict: 消息段字典

        Returns:
            MessageSegmentUnion: 具体的消息段对象
        """
        if not isinstance(seg_dict, dict):
            # 如果已经是消息段对象，直接返回
            return seg_dict

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
            if seg_type == "sticker":
                # 使用简单的创建方式，避免复杂的导入问题
                from .models import StickerSegment

                return StickerSegment(**seg_dict)
            if seg_type == "location":
                # 使用简单的创建方式，避免复杂的导入问题
                from .models import LocationSegment

                return LocationSegment(**seg_dict)
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

        # 配置session，重点解决SSE接收时的"chunk too big"问题
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )

        timeout = aiohttp.ClientTimeout(
            total=None,  # 不设置总超时时间
            connect=30,  # 连接超时30秒
            sock_read=300,  # socket读取超时5分钟，用于接收大文件分块
        )

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            read_bufsize=2 * 1024 * 1024,  # 2MB读取缓冲区，处理SSE大chunk
            max_line_size=8 * 1024 * 1024,  # 8MB最大行大小，防止SSE chunk too big
            max_field_size=16 * 1024 * 1024,  # 16MB最大字段大小，防止SSE chunk too big
        )
        self.running = True

        # 注册客户端
        success = await self.register()
        if not success:
            self.logger.error("客户端注册失败")
            self.running = False
            if self.session:
                await self.session.close()
                self.session = None
            return

        # 启动SSE监听
        self.sse_task = asyncio.create_task(self._connect_sse())

        # 启动分块清理任务（清理接收缓冲区）
        asyncio.create_task(self._chunk_cleanup_loop())

    async def stop(self) -> None:
        """停止客户端"""
        self.running = False

        if self.sse_task:
            self.sse_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.sse_task
            self.sse_task = None

        if self.session:
            await self.session.close()
            self.session = None

    @retry_decorator(retry_count=3, initial_delay=1.0)
    async def register(self) -> bool:
        """注册客户端"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        # 修改为正确的URL
        url = f"{self.server_url}/api/adapters/sse/connect"
        self.logger.info(f"注册客户端URL: {url}")

        register_data = {
            "cmd": "register",
            "platform": self.platform,
            "client_name": self.client_name,
            "client_version": self.client_version,
        }

        # 修改：打印请求数据
        self.logger.debug(f"注册客户端数据: {register_data}")

        # 确保session不为None
        assert self.session is not None
        async with self.session.post(url, json=register_data) as response:
            if response.status == 200:
                result = await response.json()
                self.client_id = result.get("client_id")
                self.logger.success(f"客户端注册成功: {self.client_id}")
                return True

            text = await response.text()
            self.logger.error(f"客户端注册失败: {response.status} - {text}")
            return False

    async def _connect_sse(self) -> None:
        """连接SSE事件流"""
        if not self.session:
            # 重新创建session（如果被意外关闭）
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )

            timeout = aiohttp.ClientTimeout(
                total=None,  # 不设置总超时时间
                connect=30,  # 连接超时30秒
                sock_read=300,  # socket读取超时5分钟，用于接收大文件分块
            )

            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                read_bufsize=2 * 1024 * 1024,  # 2MB读取缓冲区，处理SSE大chunk
                max_line_size=8 * 1024 * 1024,  # 8MB最大行大小，防止SSE chunk too big
                max_field_size=16 * 1024 * 1024,  # 16MB最大字段大小，防止SSE chunk too big
            )

        retry_count = 0
        max_retries = -1 if self.auto_reconnect else 1

        while self.running and (max_retries == -1 or retry_count < max_retries):
            try:
                # 修改为正确的URL
                url = f"{self.server_url}/api/adapters/sse/connect?client_name={self.client_name}&platform={self.platform}"
                if self.client_id:
                    url += f"&client_id={self.client_id}"

                # 修改：打印连接URL
                self.logger.info(f"连接SSE URL: {url}")

                # 确保session不为None
                assert self.session is not None
                async with self.session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"SSE连接失败 ({response.status}): {error_text}")
                        if not self.auto_reconnect:
                            return
                        await asyncio.sleep(self.reconnect_interval)
                        retry_count += 1
                        continue

                    # 重置重试计数
                    retry_count = 0
                    self.logger.success("SSE连接成功，开始处理事件流")

                    # 处理SSE事件流
                    event_type = None
                    event_data = ""
                    async for line in response.content:
                        if not self.running:
                            break

                        line = line.decode("utf-8").strip()
                        if not line:
                            # 空行表示一个事件的结束，处理收集的数据
                            if event_type and event_data:
                                try:
                                    # 尝试解析为JSON
                                    try:
                                        data = json.loads(event_data)
                                    except json.JSONDecodeError:
                                        # 如果不是JSON格式，则作为字符串处理
                                        data = {"text": event_data}

                                    await self._handle_event(event_type, data)
                                except Exception:
                                    self.logger.exception(
                                        f"处理事件发生异常，事件类型: {event_type}, 数据长度: {len(event_data)}",
                                    )

                                # 重置事件数据
                                event_type = None
                                event_data = ""
                            continue

                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                        elif line.startswith("data:"):
                            # 累积数据行
                            data_part = line[5:].strip()
                            if event_data:
                                event_data += "\n" + data_part
                            else:
                                event_data = data_part
                        elif line.startswith("id:"):
                            # 处理事件ID
                            pass
                        elif line.startswith("retry:"):
                            # 处理重连间隔
                            pass

            except asyncio.CancelledError:
                self.logger.info("SSE连接已取消")
                break
            except Exception:
                self.logger.exception("SSE连接异常")
                if not self.auto_reconnect:
                    break
                await asyncio.sleep(self.reconnect_interval)
                retry_count += 1

            # 如果需要重连，先等待一段时间
            if self.running and self.auto_reconnect:
                await asyncio.sleep(self.reconnect_interval)

    async def _handle_event(
        self,
        event_type: str,
        data: Union[Dict[str, Any], str],
    ) -> None:
        """处理SSE事件"""
        # 如果数据是字符串而不是字典，尝试转换为字典
        if isinstance(data, str):
            try:
                data = {"text": data}
            except Exception:
                # 无法解析，使用简单字典
                data = {"text": data}

        if event_type == "connected":
            self.logger.info(f"SSE连接成功: {data}")
            self.client_id = data.get("client_id", self.client_id)

            # 重新订阅之前的频道
            for channel_id in list(self.subscribed_channels):
                await self.subscribe_channel(channel_id)

        elif event_type == "heartbeat":
            # 服务端心跳，不需要响应
            pass

        elif event_type in self.event_handlers:
            # 调用对应的事件处理器
            request_id = None
            request_data = data

            # 如果是请求事件
            if isinstance(data, dict) and "request_id" in data:
                request_id = data["request_id"]
                request_data = data.get("data", {})

            try:
                # 根据事件类型创建对应的请求模型
                if event_type == RequestType.SEND_MESSAGE.value and isinstance(request_data, dict):
                    # 转换segments从dict到具体的消息段对象
                    segments_data = request_data.get("segments", [])
                    segments = []
                    for seg_dict in segments_data:
                        segments.append(self._convert_dict_to_segment(seg_dict))

                    request_data = SendMessageRequest(
                        channel_id=request_data.get("channel_id", ""),
                        segments=segments,
                    )
                elif event_type == RequestType.GET_USER_INFO.value and isinstance(request_data, dict):
                    request_data = GetUserInfoRequest(**request_data)
                elif event_type == RequestType.GET_CHANNEL_INFO.value and isinstance(request_data, dict):
                    request_data = GetChannelInfoRequest(**request_data)
                elif event_type == RequestType.GET_SELF_INFO.value and isinstance(request_data, dict):
                    request_data = GetSelfInfoRequest()
                elif event_type == RequestType.SET_MESSAGE_REACTION.value and isinstance(request_data, dict):
                    request_data = SetMessageReactionRequest(**request_data)

                # 调用处理器
                handler = self.event_handlers[event_type]
                result = await handler(event_type, request_data)

                # 如果有请求ID，需要响应
                if request_id:
                    self.logger.debug(f"发送响应: 请求ID {request_id}, 结果: {result}")
                    # 将BaseModel结果转换为字典
                    if result is not None and hasattr(result, "model_dump"):
                        result_dict = result.model_dump()
                    else:
                        result_dict = result or {}
                    await self._send_response(request_id, True, result_dict)
            except Exception as e:
                self.logger.exception(f"处理事件异常: {event_type}")
                # 如果有请求ID，发送错误响应
                if request_id:
                    await self._send_response(request_id, False, {"error": str(e)})

        else:
            self.logger.warning(f"未知事件类型: {event_type}, 数据: {data}")

    @retry_decorator(retry_count=3, initial_delay=1.0)
    async def subscribe_channel(self, channel_id: str) -> bool:
        """订阅频道

        Args:
            channel_id: 频道ID (如群组ID或用户ID)

        Returns:
            bool: 是否成功订阅
        """
        if not self.client_id or not self.session:
            self.logger.error("客户端尚未注册或启动")
            return False

        # 修改为正确的URL
        url = f"{self.server_url}/api/adapters/sse/connect"
        command_data = {
            "cmd": "subscribe",
            "channel_id": channel_id,
        }

        headers = {"X-Client-ID": self.client_id}

        # 修改：打印订阅信息
        self.logger.info(f"订阅频道: {channel_id}, URL: {url}")
        self.logger.debug(f"订阅数据: {command_data}")

        async with self.session.post(
            url,
            json=command_data,
            headers=headers,
        ) as response:
            if response.status == 200:
                self.subscribed_channels.add(channel_id)
                self.logger.success(f"订阅频道成功: {channel_id}")
                return True

            text = await response.text()
            self.logger.error(f"订阅频道失败 ({response.status}): {text}")
            return False

    @retry_decorator(retry_count=3, initial_delay=1.0)
    async def unsubscribe_channel(self, channel_id: str) -> bool:
        """取消订阅频道

        Args:
            channel_id: 频道ID

        Returns:
            bool: 是否成功取消订阅
        """
        if not self.client_id or not self.session:
            self.logger.error("客户端尚未注册或启动")
            return False

        # 修改为正确的URL
        url = f"{self.server_url}/api/adapters/sse/connect"
        command_data = {
            "cmd": "unsubscribe",
            "channel_id": channel_id,
        }

        headers = {"X-Client-ID": self.client_id}

        async with self.session.post(
            url,
            json=command_data,
            headers=headers,
        ) as response:
            if response.status == 200:
                self.subscribed_channels.discard(channel_id)
                self.logger.success(f"取消订阅频道成功: {channel_id}")
                return True

            text = await response.text()
            self.logger.error(f"取消订阅频道失败: {text}")
            return False

    @retry_decorator(retry_count=3, initial_delay=1.0)
    async def send_message(
        self,
        channel_id: str,
        message: Union[ReceiveMessage, Dict[str, Any]],
    ) -> bool:
        """发送消息到服务器

        Args:
            channel_id: 频道ID
            message: 消息对象或字典

        Returns:
            bool: 是否成功发送
        """
        if not self.client_id or not self.session:
            self.logger.error("客户端尚未注册或启动")
            return False

        # 修改为正确的URL
        url = f"{self.server_url}/api/adapters/sse/connect"

        # 如果是字典，转换为ReceiveMessage对象
        if isinstance(message, dict):
            try:
                message = ReceiveMessage(**message)
            except Exception:
                self.logger.exception("消息格式转换失败")
                return False

        command_data = {
            "cmd": "message",
            "channel_id": channel_id,
            "message": message.model_dump(),
        }

        headers = {"X-Client-ID": self.client_id}

        # 添加日志，打印消息发送信息
        self.logger.info(f"发送消息到频道: {channel_id}, URL: {url}")
        self.logger.debug(f"消息内容: {message.model_dump()}")

        async with self.session.post(
            url,
            json=command_data,
            headers=headers,
        ) as response:
            if response.status == 200:
                self.logger.success(f"消息发送成功: {channel_id}")
                return True

            text = await response.text()
            self.logger.error(f"消息发送失败 ({response.status}): {text}")
            return False

    @retry_decorator(retry_count=3, initial_delay=1.0)
    async def _send_response(
        self,
        request_id: str,
        success: bool,
        data: Dict[str, Any],
    ) -> bool:
        """向服务器发送响应

        Args:
            request_id: 请求ID
            success: 是否成功
            data: 响应数据

        Returns:
            bool: 是否成功发送响应
        """
        if not self.client_id or not self.session:
            self.logger.error("客户端尚未注册或启动")
            return False

        # 修改为正确的URL
        url = f"{self.server_url}/api/adapters/sse/connect"
        response_data = {
            "cmd": "response",
            "request_id": request_id,
            "success": success,
            "data": data,
        }

        headers = {"X-Client-ID": self.client_id}

        async with self.session.post(
            url,
            json=response_data,
            headers=headers,
        ) as response:
            return response.status == 200

    # 以下方法为默认事件处理器，需要被子类重写

    async def _handle_send_message(
        self,
        _event_type: str,
        data: SendMessageRequest,
    ) -> SendMessageResponse:
        """处理发送消息请求

        服务端发送消息请求，客户端需要实现实际的消息发送逻辑

        Args:
            _event_type: 事件类型
            data: 发送消息请求数据

        Returns:
            SendMessageResponse: 发送结果响应
        """
        self.logger.info(f"收到发送消息请求: {data}")
        # 需要被子类重写以实现实际的消息发送逻辑

        # 提取消息内容
        text_content = ""
        image_urls = []
        at_users = []

        for segment in data.segments:
            if isinstance(segment, TextSegment):
                text_content += segment.content
            elif isinstance(segment, ImageSegment):
                if segment.url:
                    image_urls.append(segment.url)
            elif isinstance(segment, AtSegment):
                at_users.append(
                    {
                        "user_id": segment.user_id,
                        "nickname": segment.nickname or segment.user_id,
                    },
                )

        self.logger.info(f"需要发送消息到频道 {data.channel_id}")
        self.logger.debug(f"文本内容: {text_content}")
        self.logger.debug(f"图片URL: {image_urls}")
        self.logger.debug(f"@用户: {at_users}")

        # 这里应实现实际的消息发送逻辑
        # 例如调用具体平台的API发送消息

        # 模拟消息发送成功
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        return SendMessageResponse(message_id=message_id, success=True)

    async def _handle_get_user_info(
        self,
        _event_type: str,
        data: GetUserInfoRequest,
    ) -> UserInfo:
        """处理获取用户信息请求

        Args:
            _event_type: 事件类型
            data: 获取用户信息请求数据

        Returns:
            UserInfo: 用户信息
        """
        self.logger.info(f"收到获取用户信息请求: {data}")
        # 需要被子类重写

        return UserInfo(
            user_id=data.user_id,
            user_name=f"用户_{data.user_id}",
            user_avatar=None,
            user_nickname=None,
            platform_name="sse",
        )

    async def _handle_get_channel_info(
        self,
        _event_type: str,
        data: GetChannelInfoRequest,
    ) -> ChannelInfo:
        """处理获取频道信息请求

        Args:
            _event_type: 事件类型
            data: 获取频道信息请求数据

        Returns:
            ChannelInfo: 频道信息
        """
        self.logger.info(f"收到获取频道信息请求: {data}")
        # 需要被子类重写

        return ChannelInfo(
            channel_id=data.channel_id,
            channel_name=f"频道_{data.channel_id}",
            channel_avatar=None,
            member_count=100,
            owner_id=None,
            is_admin=False,
        )

    async def _handle_get_self_info(
        self,
        _event_type: str,
        data: GetSelfInfoRequest,
    ) -> UserInfo:
        """处理获取自身信息请求

        Args:
            _event_type: 事件类型
            data: 获取自身信息请求数据

        Returns:
            UserInfo: 自身信息
        """
        self.logger.info(f"收到获取自身信息请求: {data}")
        # 需要被子类重写

        return UserInfo(
            user_id="self_id",
            user_name="我自己",
            user_avatar=None,
            user_nickname=None,
            platform_name="sse",
        )

    async def _handle_set_message_reaction(
        self,
        _event_type: str,
        data: SetMessageReactionRequest,
    ) -> SetMessageReactionResponse:
        """处理设置消息反应请求

        Args:
            _event_type: 事件类型
            data: 设置消息反应请求数据

        Returns:
            SetMessageReactionResponse: 设置结果
        """
        self.logger.info(f"收到设置消息反应请求: {data}")
        # 需要被子类重写

        # 默认实现：简单返回成功
        return SetMessageReactionResponse(
            success=True,
            message=f"消息反应设置{'成功' if data.status else '取消成功'}",
        )

    async def _handle_file_chunk(
        self,
        _event_type: str,
        data: Union[ChunkData, Dict[str, Any]],
    ) -> Optional[FileChunkResponse]:
        """处理服务端推送的文件分块数据

        Args:
            _event_type: 事件类型
            data: 分块数据

        Returns:
            Optional[FileChunkResponse]: 响应数据，如果是中间分块则返回None
        """
        try:
            # 如果是字典，先转换为ChunkData模型
            chunk_data = ChunkData(**data) if isinstance(data, dict) else data

            if not all(
                [
                    chunk_data.chunk_id,
                    chunk_data.chunk_index is not None,
                    chunk_data.total_chunks,
                    chunk_data.chunk_data,
                ],
            ):
                self.logger.error(f"分块数据不完整: {chunk_data}")
                return FileChunkResponse(success=False, error="分块数据不完整", message=None)

            # 类型检查和转换
            if (
                not isinstance(chunk_data.chunk_id, str)
                or not isinstance(chunk_data.chunk_index, int)
                or not isinstance(chunk_data.total_chunks, int)
            ):
                self.logger.error("分块数据类型错误")
                return FileChunkResponse(success=False, error="分块数据类型错误", message=None)

            self.logger.debug(f"接收分块: {chunk_data.filename} [{chunk_data.chunk_index + 1}/{chunk_data.total_chunks}]")

            # 初始化或更新chunk buffer
            if chunk_data.chunk_id not in self.chunk_buffers:
                self.chunk_buffers[chunk_data.chunk_id] = {
                    "chunks": [None] * chunk_data.total_chunks,
                    "total_chunks": chunk_data.total_chunks,
                    "received_chunks": 0,
                    "total_size": chunk_data.total_size,
                    "mime_type": chunk_data.mime_type,
                    "filename": chunk_data.filename,
                    "file_type": chunk_data.file_type,
                }
                self.chunk_timeouts[chunk_data.chunk_id] = time.time() + self.chunk_timeout_duration

            buffer_info = self.chunk_buffers[chunk_data.chunk_id]

            # 检查分块是否已接收
            if buffer_info["chunks"][chunk_data.chunk_index] is not None:
                self.logger.warning(
                    f"重复接收分块: {chunk_data.filename} [{chunk_data.chunk_index + 1}/{chunk_data.total_chunks}]",
                )
                return None

            # 存储分块数据
            buffer_info["chunks"][chunk_data.chunk_index] = chunk_data.chunk_data
            buffer_info["received_chunks"] += 1

            self.logger.debug(f"分块进度: {chunk_data.filename} [{buffer_info['received_chunks']}/{chunk_data.total_chunks}]")

            # 检查是否接收完所有分块
            if buffer_info["received_chunks"] == chunk_data.total_chunks:
                # 合并所有分块
                complete_data = "".join([chunk for chunk in buffer_info["chunks"] if chunk is not None])

                # 解码base64数据
                try:
                    file_bytes = base64.b64decode(complete_data)

                    # 调用用户自定义的文件处理回调
                    await self._on_file_received(
                        chunk_data.filename or f"file_{chunk_data.chunk_id[:8]}",
                        file_bytes,
                        chunk_data.mime_type or "application/octet-stream",
                        chunk_data.file_type or "file",
                    )

                    # 清理缓冲区
                    del self.chunk_buffers[chunk_data.chunk_id]
                    del self.chunk_timeouts[chunk_data.chunk_id]

                except Exception as e:
                    self.logger.exception(f"文件解码失败: {chunk_data.filename}")
                    # 清理缓冲区
                    del self.chunk_buffers[chunk_data.chunk_id]
                    del self.chunk_timeouts[chunk_data.chunk_id]
                    return FileChunkResponse(success=False, error=f"文件解码失败: {e!s}", message=None)
                else:
                    self.logger.success(f"文件接收完成: {chunk_data.filename} ({len(file_bytes)} bytes)")
                    return FileChunkResponse(success=True, error=None, message=f"文件 {chunk_data.filename} 接收完成")

        except Exception as e:
            self.logger.exception("处理文件分块异常")
            return FileChunkResponse(success=False, error=str(e), message=None)
        else:
            return None  # 中间分块不需要响应

    async def _handle_file_chunk_complete(
        self,
        _event_type: str,
        data: Union[ChunkComplete, Dict[str, Any]],
    ) -> Optional[None]:
        """处理服务端文件分块传输完成事件

        Args:
            _event_type: 事件类型
            data: 完成事件数据

        Returns:
            Optional[None]: 无响应数据
        """
        # 如果是字典，先转换为ChunkComplete模型
        chunk_complete = ChunkComplete(**data) if isinstance(data, dict) else data

        if chunk_complete.success:
            self.logger.info(f"服务端确认传输完成: {chunk_complete.message}")
        else:
            self.logger.error(f"服务端传输失败: {chunk_complete.message}")
            # 清理可能存在的缓冲区
            if chunk_complete.chunk_id and chunk_complete.chunk_id in self.chunk_buffers:
                del self.chunk_buffers[chunk_complete.chunk_id]
                del self.chunk_timeouts[chunk_complete.chunk_id]

        return None  # 不需要响应

    async def _on_file_received(self, filename: str, file_bytes: bytes, mime_type: str, file_type: str) -> None:
        """服务端推送文件接收完成回调

        用户可以重写此方法来自定义文件处理逻辑

        Args:
            filename: 文件名
            file_bytes: 文件字节数据
            mime_type: MIME类型
            file_type: 文件类型 (image/file)
        """
        self.logger.info(f"收到文件: {filename} ({len(file_bytes)} bytes, {mime_type})")

        # 默认实现：保存文件到当前目录
        try:
            file_path = Path(filename)
            # 确保文件名安全
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            if not safe_filename:
                safe_filename = f"file_{hashlib.md5(file_bytes).hexdigest()[:8]}"

            # 添加扩展名
            if not safe_filename.count("."):
                if mime_type.startswith("image/"):
                    ext = mime_type.split("/")[1]
                    safe_filename += f".{ext}"
                elif file_type == "file":
                    safe_filename += ".bin"

            file_path = Path(safe_filename)
            file_path.write_bytes(file_bytes)

        except Exception:
            self.logger.exception("保存文件失败")
        else:
            self.logger.success(f"文件已保存: {file_path}")

    async def _chunk_cleanup_loop(self) -> None:
        """分块清理循环任务"""
        while self.running:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._cleanup_expired_chunks()
            except asyncio.CancelledError:
                break
            except Exception:
                self.logger.exception("分块清理任务异常")

    async def _cleanup_expired_chunks(self) -> None:
        """清理过期的分块缓冲区"""
        current_time = time.time()
        expired_chunk_ids = []

        for chunk_id, timeout_time in self.chunk_timeouts.items():
            if current_time > timeout_time:
                expired_chunk_ids.append(chunk_id)

        for chunk_id in expired_chunk_ids:
            buffer_info = self.chunk_buffers.get(chunk_id, {})
            filename = buffer_info.get("filename", "unknown")
            self.logger.warning(f"清理过期分块缓冲区: {filename} (chunk_id: {chunk_id})")

            del self.chunk_buffers[chunk_id]
            del self.chunk_timeouts[chunk_id]


# 使用示例
async def example_usage():
    """使用示例"""

    class MyClient(SSEClient):
        async def _handle_send_message(
            self,
            _event_type: str,
            data: SendMessageRequest,
        ) -> SendMessageResponse:
            self.logger.info(f"收到发送消息请求: {data}")
            return await super()._handle_send_message(_event_type, data)

        async def _on_file_received(self, filename: str, file_bytes: bytes, mime_type: str, file_type: str) -> None:
            """自定义文件接收处理"""
            self.logger.info(f"接收到文件: {filename} ({len(file_bytes)} bytes, {mime_type}, {file_type})")

            # 这里可以实现自定义的文件处理逻辑
            # 比如保存到特定目录、上传到云存储等
            save_dir = Path("received_files")
            save_dir.mkdir(exist_ok=True)

            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-") or f"file_{int(time.time())}"
            file_path = save_dir / safe_filename

            try:
                file_path.write_bytes(file_bytes)
            except Exception:
                self.logger.exception("文件保存失败")
            else:
                self.logger.success(f"文件已保存到: {file_path}")

        async def _handle_get_self_info(self, _event_type: str, data: GetSelfInfoRequest) -> UserInfo:  # noqa: ARG002
            """自定义获取自身信息处理"""
            return UserInfo(
                user_id="my_bot_id",
                user_name="我的机器人",
                user_avatar="https://example.com/avatar.jpg",
                user_nickname=None,
                platform_name="sse",
            )

    # 创建客户端
    client = MyClient(
        server_url="http://localhost:8080",
        platform="wechat",
        client_name="ExampleClient",
        client_version="1.0.0",
    )

    # 启动客户端
    await client.start()

    # 订阅频道
    await client.subscribe_channel("group_123456")

    # 发送普通消息
    large_image_path = "large_image.jpg"  # 大图片文件

    # 创建消息段
    segments = [
        text("这是一张图片："),
        image(file_path=large_image_path),
    ]

    # 发送消息
    msg = ReceiveMessage(
        platform_name="wechat",
        from_id="user123",
        from_name="张三",
        from_nickname="小张",
        is_to_me=False,
        is_self=False,
        raw_content=None,
        segments=segments,
        channel_id="group_123456",
        channel_name="测试频道",
    )
    await client.send_message("group_123456", msg)

    # 运行一段时间
    await asyncio.sleep(60)

    # 停止客户端
    await client.stop()


if __name__ == "__main__":
    asyncio.run(example_usage())
