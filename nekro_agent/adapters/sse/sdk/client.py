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

import aiohttp
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
        self.session: Optional[aiohttp.ClientSession] = None
        self.sse_task: Optional[asyncio.Task] = None
        self.subscribed_channels: set[str] = set()
        self.running = False
        self.event_handlers: Dict[str, EventHandler] = {}

        # 分块接收相关（仅用于接收服务端推送的大文件）
        self.chunk_buffers: Dict[str, Any] = {}  # chunk_id -> {chunks: [], total_chunks: int, ...}
        self.chunk_timeouts: Dict[str, float] = {}  # chunk_id -> timeout_timestamp
        self.chunk_timeout_duration = 300  # 5分钟超时

        # 实例化分块接收器
        self._chunk_receiver = ChunkReceiver(self._on_file_received)

        # 注册默认事件处理器
        self.register_handler(RequestType.SEND_MESSAGE.value, self._handle_send_message)
        self.register_handler(RequestType.GET_USER_INFO.value, self._handle_get_user_info)
        self.register_handler(RequestType.GET_CHANNEL_INFO.value, self._handle_get_channel_info)
        self.register_handler(RequestType.GET_SELF_INFO.value, self._handle_get_self_info)
        self.register_handler(RequestType.SET_MESSAGE_REACTION.value, self._handle_set_message_reaction)
        self.register_handler(
            RequestType.FILE_CHUNK.value,
            lambda _, data: self._chunk_receiver.handle_file_chunk(data),
        )
        self.register_handler(
            RequestType.FILE_CHUNK_COMPLETE.value,
            lambda _, data: self._async_wrapper(self._chunk_receiver.handle_file_chunk_complete(data)),
        )

    def _create_session(self) -> aiohttp.ClientSession:
        """创建并配置aiohttp.ClientSession"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        timeout = aiohttp.ClientTimeout(
            total=None,
            connect=30,
            sock_read=300,
        )
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            read_bufsize=2 * 1024 * 1024,
            max_line_size=8 * 1024 * 1024,
            max_field_size=16 * 1024 * 1024,
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

        if self.session:
            await self.session.close()
            self.session = None
        self.logger.info("客户端已停止")

    @retry_decorator()
    async def _post_command(self, command: "ClientCommand", data: Optional[Dict[str, Any]] = None) -> aiohttp.ClientResponse:
        """向服务端发送POST命令的辅助方法"""
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

        self.logger.debug(f"发送命令: {command.value}, URL: {url}, Payload: {payload}")
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
            if response.status == 200:
                result = await response.json()
                self.client_id = result.get("client_id")
                self.logger.success(f"客户端注册成功: {self.client_id}")
                return True

            error_text = await response.text()
            self.logger.error(f"客户端注册失败 ({response.status}): {error_text}")
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
                async with self.session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"SSE连接失败 ({response.status}): {error_text}")
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

    async def _process_sse_stream(self, response: aiohttp.ClientResponse) -> None:
        """从响应中处理SSE事件流"""
        event_type, event_data = None, ""
        async for line in response.content:
            if not self.running:
                break
            line = line.decode("utf-8").strip()
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

    async def _handle_registered_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """处理已注册的事件"""
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

        try:
            pydantic_data = model(**request_data) if model else request_data
            result = await handler(event_type, pydantic_data)
            if request_id and result:
                await self._send_response(request_id, True, result.model_dump())
        except Exception as e:
            self.logger.exception(f"处理事件 '{event_type}' 时发生异常")
            if request_id:
                await self._send_response(request_id, False, {"error": str(e)})

    async def subscribe_channel(self, channel_ids: Union[str, List[str]]) -> bool:
        """订阅频道"""
        channels = [channel_ids] if isinstance(channel_ids, str) else channel_ids
        try:
            response = await self._post_command(ClientCommand.SUBSCRIBE, {"channel_ids": channels})
        except Exception:
            self.logger.exception(f"订阅频道 {channels} 异常")
            return False
        else:
            if response.status == 200:
                for channel_id in channels:
                    self.subscribed_channels.add(channel_id)
                self.logger.success(f"订阅频道成功: {channels}")
                return True
            self.logger.error(f"订阅频道失败 ({response.status}): {await response.text()}")
            return False

    async def unsubscribe_channel(self, channel_ids: Union[str, List[str]]) -> bool:
        """取消订阅频道"""
        channels = [channel_ids] if isinstance(channel_ids, str) else channel_ids
        try:
            response = await self._post_command(ClientCommand.UNSUBSCRIBE, {"channel_ids": channels})
        except Exception:
            self.logger.exception(f"取消订阅频道 {channels} 异常")
            return False
        else:
            if response.status == 200:
                for channel_id in channels:
                    self.subscribed_channels.discard(channel_id)
                self.logger.success(f"取消订阅频道成功: {channels}")
                return True
            self.logger.error(f"取消订阅失败 ({response.status}): {await response.text()}")
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
            if response.status == 200:
                self.logger.success(f"消息发送成功: {channel_id}")
                return True
            self.logger.error(f"消息发送失败 ({response.status}): {await response.text()}")
            return False

    async def _send_response(self, request_id: str, success: bool, data: Dict[str, Any]) -> bool:
        """向服务器发送响应"""
        response_data = {"request_id": request_id, "success": success, "data": data}
        try:
            response = await self._post_command(ClientCommand.RESPONSE, response_data)
        except Exception:
            self.logger.exception(f"发送响应 (req_id: {request_id}) 异常")
            return False
        else:
            return response.status == 200

    # 以下方法为默认事件处理器，需要被子类重写
    async def _handle_send_message(self, _event_type: str, data: SendMessageRequest) -> SendMessageResponse:
        """处理发送消息请求（可重写）"""
        self.logger.info(f"收到发送消息请求: {data.model_dump_json(indent=2)}")
        # 默认实现：打印日志并模拟成功
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        return SendMessageResponse(message_id=message_id, success=True)

    async def _handle_get_user_info(self, _event_type: str, data: GetUserInfoRequest) -> UserInfo:
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

    async def _handle_get_channel_info(self, _event_type: str, data: GetChannelInfoRequest) -> ChannelInfo:
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

    async def _handle_get_self_info(self, _event_type: str, _data: GetSelfInfoRequest) -> UserInfo:
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
        return SetMessageReactionResponse(success=True, message=f"消息反应设置{'成功' if data.status else '取消'}")

    async def _on_file_received(self, filename: str, file_bytes: bytes, mime_type: str, _file_type: str) -> None:
        """文件接收完成回调（可重写）"""
        self.logger.info(f"收到文件: {filename} ({len(file_bytes)} bytes, {mime_type})")
        # 默认实现：保存文件到当前目录
        try:
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-") or f"file_{int(time.time())}"
            file_path = Path(safe_filename)
            file_path.write_bytes(file_bytes)
            self.logger.success(f"文件已保存: {file_path}")
        except Exception:
            self.logger.exception("保存文件失败")

    async def _async_wrapper(self, result: Any) -> Any:
        """简单的异步包装器"""
        return result
