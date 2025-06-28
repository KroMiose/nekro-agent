import asyncio
import json
from typing import Any, Callable, Coroutine, Dict, List, Optional

import aiohttp
from pydantic import BaseModel, Field, ValidationError

from nekro_agent.core.logger import logger


class Danmaku(BaseModel):
    """弹幕消息"""

    from_live_room: str = Field(default="", description="消息来源(房间号)")
    uid: str = Field(default="0", description="消息用户ID")
    username: str = Field(default="unknown", description="用户名")
    text: str = Field(default="", description="弹幕内容")
    time: int = Field(default=0, description="弹幕发送时间")
    url: List[str] = Field(default_factory=list, description="弹幕中的表情图片url列表")
    is_trigger: bool = Field(default=False, description="是否触发LLM (由ws客户端接收并处理)")
    is_system: bool = Field(default=False, description="是否作为system身份发送 (由ws客户端接收并处理)")


class BilibiliWebSocketClient:
    """
    Bilibili WebSocket 客户端

    管理与 `/ws/danmaku` 和 `/ws/animate_control` 的连接。
    """

    def __init__(
        self,
        base_url: str,
        danmaku_handler: Callable[["BilibiliWebSocketClient", Danmaku], Coroutine[Any, Any, None]],
    ):
        self._base_url = base_url.rstrip("/")
        self._danmaku_handler = danmaku_handler
        self._danmaku_url = f"{self._base_url}/ws/danmaku"
        self._animate_url = f"{self._base_url}/ws/animate_control"

        self._session: Optional[aiohttp.ClientSession] = None
        self._danmaku_ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._animate_ws: Optional[aiohttp.ClientWebSocketResponse] = None

        self._main_tasks: List[asyncio.Task] = []
        self._is_closing = False

        # For animate_control request-response
        self._animate_lock = asyncio.Lock()
        self._pending_animate_future: Optional[asyncio.Future] = None

    async def start_with_auto_reconnect(self) -> None:
        """启动客户端并保持自动重连"""
        self._session = aiohttp.ClientSession()
        self._is_closing = False

        danmaku_task = asyncio.create_task(
            self._connection_loop(self._danmaku_url, self._on_danmaku_connect, "Danmaku"),
        )
        animate_task = asyncio.create_task(
            self._connection_loop(self._animate_url, self._on_animate_connect, "Animate"),
        )
        self._main_tasks = [danmaku_task, animate_task]

        await asyncio.gather(*self._main_tasks, return_exceptions=True)

    async def _connection_loop(
        self,
        url: str,
        on_connect: Callable[[aiohttp.ClientWebSocketResponse], Coroutine[Any, Any, None]],
        name: str,
    ) -> None:
        """通用连接循环，包含重连逻辑"""
        backoff_delay = 1
        while not self._is_closing:
            try:
                logger.info(f"正在连接到 {name} WebSocket: {url}")
                if not self._session or self._session.closed:
                    self._session = aiohttp.ClientSession()

                async with self._session.ws_connect(url, heartbeat=30) as ws:
                    logger.info(f"{name} WebSocket 连接成功: {url}")
                    backoff_delay = 1 
                    await on_connect(ws)
            except aiohttp.ClientConnectorError as e:
                logger.warning(f"{name} WebSocket 连接失败: {e}")
            except aiohttp.WSServerHandshakeError as e:
                logger.warning(f"{name} WebSocket握手失败: {e}")
            except Exception as e:
                logger.error(f"{name} WebSocket 循环遇到未知错误: {e}", exc_info=True)
            finally:
                # Fail any pending requests on this connection
                if name == "Animate" and self._pending_animate_future and not self._pending_animate_future.done():
                    self._pending_animate_future.set_exception(ConnectionError(f"{name} WebSocket disconnected"))

                if not self._is_closing:
                    logger.info(f"{name} WebSocket 将在 {backoff_delay} 秒后尝试重连...")
                    await asyncio.sleep(backoff_delay)
                    backoff_delay = min(backoff_delay * 2, 60)  

    async def _on_danmaku_connect(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        self._danmaku_ws = ws
        await self._danmaku_receiver(ws)

    async def _on_animate_connect(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        self._animate_ws = ws
        await self._animate_receiver(ws)

    async def _danmaku_receiver(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        """接收并处理弹幕消息"""
        async for msg in ws:
            if self._is_closing:
                break
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    # 心跳 pong 不需要处理, aiohttp 会自动处理
                    danmaku = Danmaku.model_validate_json(msg.data)
                    await self._danmaku_handler(self, danmaku)
                except ValidationError as e:
                    logger.warning(f"解析弹幕消息失败: {e}, 原始数据: {msg.data}")
                except Exception as e:
                    logger.error(f"处理弹幕消息时发生错误: {e}", exc_info=True)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"Danmaku WebSocket 出现错误: {ws.exception()}")
                break
        logger.info("Danmaku WebSocket 接收循环结束.")

    async def _animate_receiver(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        """接收并处理 animate control 的响应"""
        async for msg in ws:
            if self._is_closing:
                break
            if msg.type == aiohttp.WSMsgType.TEXT:
                logger.info(f"收到 Animate 消息: {msg.data}")
                if self._pending_animate_future and not self._pending_animate_future.done():
                    try:
                        data = json.loads(msg.data)
                        self._pending_animate_future.set_result(data)
                    except json.JSONDecodeError as e:
                        self._pending_animate_future.set_exception(e)
                else:
                    logger.warning(f"收到未请求的 Animate 消息: {msg.data}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"Animate WebSocket 出现错误: {ws.exception()}")
                if self._pending_animate_future and not self._pending_animate_future.done():
                    self._pending_animate_future.set_exception(ws.exception() or ConnectionError("Animate WebSocket disconnected"))
                break
        logger.info("Animate WebSocket 接收循环结束.")

    async def send_animate_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        向 /ws/animate_control 发送命令并等待响应。
        此方法不是线程安全的，也不支持并发请求。
        """
        async with self._animate_lock:
            if not self._animate_ws or self._animate_ws.closed:
                raise ConnectionError("Animate WebSocket 未连接。")

            loop = asyncio.get_running_loop()
            self._pending_animate_future = loop.create_future()

            try:
                logger.info(f"发送 Animate 命令: {command}")
                await self._animate_ws.send_json(command)
                return await asyncio.wait_for(self._pending_animate_future, timeout=30.0)
            except asyncio.TimeoutError:
                raise TimeoutError("Animate command timed out.") from None
            finally:
                self._pending_animate_future = None

    async def close(self) -> None:
        """关闭所有连接和任务"""
        if self._is_closing:
            return

        logger.info("正在关闭 Bilibili WebSocket 客户端...")
        self._is_closing = True

        for task in self._main_tasks:
            task.cancel()

        if self._danmaku_ws:
            await self._danmaku_ws.close()
        if self._animate_ws:
            await self._animate_ws.close()

        # Wait for session to close gracefully
        if self._session:
            await self._session.close()

        if self._main_tasks:
            await asyncio.gather(*self._main_tasks, return_exceptions=True)

        logger.info("Bilibili WebSocket 客户端已关闭。")