"""
SSE 客户端SDK
============

用于开发与SSE适配器通信的客户端的SDK。
提供消息模型、通信工具和事件处理框架。
"""

import asyncio
import base64
import contextlib
import json
import time
import uuid
from functools import wraps
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, Union, cast

import aiohttp
from loguru import logger
from pydantic import BaseModel, Field

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


class MessageSegment(BaseModel):
    """消息段基类"""

    type: str = Field(..., description="消息段类型")


class TextSegment(MessageSegment):
    """文本消息段"""

    content: str = Field(..., description="文本内容")


class ImageSegment(MessageSegment):
    """图片消息段"""

    url: str = Field(..., description="图片URL")
    name: Optional[str] = Field(None, description="图片文件名")
    size: Optional[int] = Field(None, description="图片大小(字节)")
    mime_type: Optional[str] = Field(None, description="图片MIME类型")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    is_origin: bool = Field(False, description="是否原图")


class FileSegment(MessageSegment):
    """文件消息段"""

    url: str = Field(..., description="文件URL")
    name: Optional[str] = Field(None, description="文件名")
    size: Optional[int] = Field(None, description="文件大小")
    mime_type: Optional[str] = Field(None, description="MIME类型")


class AtSegment(MessageSegment):
    """@消息段"""

    user_id: str = Field(..., description="用户ID")
    nickname: Optional[str] = Field(None, description="用户昵称")


class Message(BaseModel):
    """消息基类"""

    segments: List[Union[TextSegment, ImageSegment, FileSegment, AtSegment]] = Field(
        default_factory=list,
        description="消息段列表",
    )
    timestamp: int = Field(
        default_factory=lambda: int(time.time()),
        description="消息时间戳",
    )


class ReceiveMessage(Message):
    """接收到的消息"""

    msg_id: str = Field(default="", description="消息ID")
    from_id: str = Field(..., description="发送者ID")
    from_name: str = Field(..., description="发送者名称")
    from_nickname: Optional[str] = Field(None, description="发送者昵称")
    is_to_me: bool = Field(False, description="是否@我")
    is_self: bool = Field(False, description="是否自己发送的")
    raw_content: Optional[str] = Field(None, description="原始内容")
    channel_id: str = Field(..., description="频道ID")


class SendMessage(Message):
    """要发送的消息"""

    channel_id: str = Field(..., description="频道ID")


# 辅助函数
def text(content: str) -> TextSegment:
    """创建文本消息段"""
    return TextSegment(type="text", content=content)


def image(
    url: str,
    name: Optional[str] = None,
    size: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    is_origin: bool = False,
) -> ImageSegment:
    """创建图片消息段"""
    return ImageSegment(
        type="image",
        url=url,
        name=name,
        size=size,
        mime_type="image/jpeg",
        width=width,
        height=height,
        is_origin=is_origin,
    )


def file(
    url: str,
    name: Optional[str] = None,
    size: Optional[int] = None,
    mime_type: Optional[str] = None,
) -> FileSegment:
    """创建文件消息段"""
    return FileSegment(type="file", url=url, name=name, size=size, mime_type=mime_type)


def at(user_id: str, nickname: Optional[str] = None) -> AtSegment:
    """创建@消息段"""
    return AtSegment(type="at", user_id=user_id, nickname=nickname)


# 事件处理器类型
EventHandler = Callable[[str, Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]


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

        # 注册默认事件处理器
        self.register_handler("send_message", self._handle_send_message)
        self.register_handler("get_user_info", self._handle_get_user_info)
        self.register_handler("get_channel_info", self._handle_get_channel_info)
        self.register_handler("get_self_info", self._handle_get_self_info)

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

        self.session = aiohttp.ClientSession(conn_timeout=10, read_timeout=99999999)
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
            self.session = aiohttp.ClientSession()

        retry_count = 0
        max_retries = 10 if self.auto_reconnect else 1

        while self.running and retry_count < max_retries:
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
                                        f"处理事件发生异常，事件类型: {event_type}, 数据: {event_data}",
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
                # 调用处理器
                handler = self.event_handlers[event_type]
                result = await handler(event_type, request_data)

                # 如果有请求ID，需要响应
                if request_id:
                    await self._send_response(request_id, True, result or {})
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
            "message": message.dict(),
        }

        headers = {"X-Client-ID": self.client_id}

        # 添加日志，打印消息发送信息
        self.logger.info(f"发送消息到频道: {channel_id}, URL: {url}")
        self.logger.debug(f"消息内容: {message.dict()}")

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
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理发送消息请求

        服务端发送消息请求，客户端需要实现实际的消息发送逻辑

        Args:
            _event_type: 事件类型
            data: 请求数据
                {
                    "channel_id": "频道ID",
                    "segments": [
                        {"type": "text", "content": "文本内容"},
                        {"type": "image", "url": "图片URL"},
                        ...
                    ]
                }

        Returns:
            Dict[str, Any]: 响应数据
                {
                    "message_id": "发送成功的消息ID",
                    "success": true
                }
        """
        self.logger.info(f"收到发送消息请求: {data}")
        # 需要被子类重写以实现实际的消息发送逻辑

        channel_id = data.get("channel_id", "")
        segments = data.get("segments", [])

        # 提取消息内容
        text_content = ""
        image_urls = []
        at_users = []

        for segment in segments:
            seg_type = segment.get("type")
            if seg_type == "text":
                text_content += segment.get("content", "")
            elif seg_type == "image":
                image_urls.append(segment.get("url", ""))
            elif seg_type == "at":
                at_users.append(
                    {
                        "user_id": segment.get("user_id", ""),
                        "nickname": segment.get("nickname", ""),
                    },
                )

        self.logger.info(f"需要发送消息到频道 {channel_id}")
        self.logger.debug(f"文本内容: {text_content}")
        self.logger.debug(f"图片URL: {image_urls}")
        self.logger.debug(f"@用户: {at_users}")

        # 这里应实现实际的消息发送逻辑
        # 例如调用具体平台的API发送消息

        # 模拟消息发送成功
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        return {"message_id": message_id, "success": True}

    async def _handle_get_user_info(
        self,
        _event_type: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理获取用户信息请求

        Args:
            _event_type: 事件类型
            data: 请求数据，包含 user_id

        Returns:
            Dict[str, Any]: 用户信息
        """
        self.logger.info(f"收到获取用户信息请求: {data}")
        # 需要被子类重写

        user_id = data.get("user_id", "")
        return {
            "user_id": user_id,
            "user_name": f"用户_{user_id}",
            "user_avatar": None,
        }

    async def _handle_get_channel_info(
        self,
        _event_type: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理获取频道信息请求

        Args:
            _event_type: 事件类型
            data: 请求数据，包含 channel_id

        Returns:
            Dict[str, Any]: 频道信息
        """
        self.logger.info(f"收到获取频道信息请求: {data}")
        # 需要被子类重写

        channel_id = data.get("channel_id", "")
        return {
            "channel_id": channel_id,
            "channel_name": f"频道_{channel_id}",
            "channel_avatar": None,
            "member_count": 100,
        }

    async def _handle_get_self_info(
        self,
        _event_type: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理获取自身信息请求

        Args:
            _event_type: 事件类型
            data: 请求数据

        Returns:
            Dict[str, Any]: 自身信息
        """
        self.logger.info(f"收到获取自身信息请求: {data}")
        # 需要被子类重写

        return {
            "user_id": "self_id",
            "user_name": "我自己",
            "user_avatar": None,
        }


# 使用示例
async def example_usage():
    """使用示例"""

    class MyClient(SSEClient):
        async def _handle_send_message(
            self,
            _event_type: str,
            data: Dict[str, Any],
        ) -> Dict[str, Any]:
            self.logger.info(f"收到发送消息请求: {data}")
            return await super()._handle_send_message(_event_type, data)

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

    # 发送消息
    msg = ReceiveMessage(
        from_id="user123",
        from_name="张三",
        # 以下是可选参数，有默认值
        from_nickname="小张",
        is_to_me=False,
        is_self=False,
        raw_content=None,
        segments=[
            text("你好，世界！"),
            image("https://example.com/image.jpg"),
        ],
        channel_id="group_123456",
    )
    await client.send_message("group_123456", msg)

    # 运行一段时间
    await asyncio.sleep(60)

    # 停止客户端
    await client.stop()


if __name__ == "__main__":
    asyncio.run(example_usage())
