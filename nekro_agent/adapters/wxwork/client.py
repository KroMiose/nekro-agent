import asyncio
import json
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from websockets import connect
from websockets.asyncio.client import ClientConnection

from nekro_agent.core.logger import get_sub_logger


if TYPE_CHECKING:
    from .adapter import WxWorkAdapter


logger = get_sub_logger("adapter.wxwork")

CMD_SUBSCRIBE = "aibot_subscribe"
CMD_HEARTBEAT = "ping"
CMD_CALLBACK = "aibot_msg_callback"
CMD_EVENT_CALLBACK = "aibot_event_callback"
CMD_SEND_MSG = "aibot_send_msg"


class WxWorkLongConnectionClient:
    def __init__(self, bot_id: str, secret: str, adapter: "WxWorkAdapter"):
        self._bot_id = bot_id
        self._secret = secret
        self._adapter = adapter
        self._ws: Optional[ClientConnection] = None
        self._runner_task: Optional[asyncio.Task[None]] = None
        self._receiver_task: Optional[asyncio.Task[None]] = None
        self._heartbeat_task: Optional[asyncio.Task[None]] = None
        self._send_lock = asyncio.Lock()
        self._pending: Dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._stop_event = asyncio.Event()
        self._authenticated = asyncio.Event()

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and self._authenticated.is_set()

    async def start(self) -> None:
        if self._runner_task and not self._runner_task.done():
            return
        self._stop_event.clear()
        self._runner_task = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        self._stop_event.set()
        self._authenticated.clear()

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            await asyncio.gather(self._heartbeat_task, return_exceptions=True)
            self._heartbeat_task = None

        if self._runner_task:
            self._runner_task.cancel()
            await asyncio.gather(self._runner_task, return_exceptions=True)
            self._runner_task = None

        if self._receiver_task:
            self._receiver_task.cancel()
            await asyncio.gather(self._receiver_task, return_exceptions=True)
            self._receiver_task = None

        if self._ws is not None:
            await self._ws.close()
            self._ws = None

        self._fail_pending(RuntimeError("企业微信长连接已停止"))

    async def send_text_message(
        self,
        chatid: str,
        content: str,
        mentioned_list: list[str] | None = None,
    ) -> dict[str, Any]:
        text_body: dict[str, Any] = {"content": content}
        if mentioned_list:
            text_body["mentioned_list"] = mentioned_list

        body = {
            "chatid": chatid,
            "msgtype": "text",
            "text": text_body,
        }
        return await self._send_request(
            cmd=CMD_SEND_MSG,
            body=body,
            req_id=self._generate_req_id("send"),
        )

    async def _run_forever(self) -> None:
        attempt = 0

        while not self._stop_event.is_set():
            try:
                connect_kwargs: dict[str, Any] = {
                    "ping_interval": None,
                    "ping_timeout": None,
                    "close_timeout": self._adapter.config.REQUEST_TIMEOUT_SECONDS,
                    "max_size": 10 * 1024 * 1024,
                }
                if self._adapter.config.WS_URL.startswith("wss://"):
                    connect_kwargs["ssl"] = True

                async with connect(self._adapter.config.WS_URL, **connect_kwargs) as ws:
                    self._ws = ws
                    attempt = 0
                    logger.info(f"企业微信长连接已建立，开始认证: {self._adapter.config.WS_URL}")

                    self._receiver_task = asyncio.create_task(self._receive_loop())
                    await self._authenticate()
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    if self._receiver_task is not None:
                        await self._receiver_task
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._authenticated.clear()
                self._fail_pending(e)
                if self._stop_event.is_set():
                    break

                attempt += 1
                if self._adapter.config.MAX_RECONNECT_ATTEMPTS >= 0 and attempt > self._adapter.config.MAX_RECONNECT_ATTEMPTS:
                    logger.error("企业微信长连接达到最大重连次数，停止重连")
                    break

                delay = min(self._adapter.config.RECONNECT_INTERVAL_SECONDS * (2 ** (attempt - 1)), 30)
                error_type = type(e).__name__
                error_message = str(e).strip() or repr(e)
                logger.warning(
                    f"企业微信长连接断开，{delay}s 后尝试第 {attempt} 次重连: [{error_type}] {error_message}"
                )
                await asyncio.sleep(delay)
            finally:
                self._authenticated.clear()
                if self._heartbeat_task:
                    self._heartbeat_task.cancel()
                    await asyncio.gather(self._heartbeat_task, return_exceptions=True)
                    self._heartbeat_task = None
                if self._receiver_task:
                    self._receiver_task.cancel()
                    await asyncio.gather(self._receiver_task, return_exceptions=True)
                    self._receiver_task = None
                if self._ws is not None:
                    try:
                        await self._ws.close()
                    except Exception:
                        pass
                    self._ws = None

    async def _receive_loop(self) -> None:
        if self._ws is None:
            raise RuntimeError("企业微信长连接未建立，无法启动接收循环")
        async for raw_message in self._ws:
            await self._handle_raw_message(raw_message)

    async def _authenticate(self) -> None:
        subscribe_req_id = self._generate_req_id("subscribe")
        body = {"bot_id": self._bot_id, "secret": self._secret}

        logger.info(
            "发送企业微信订阅帧: "
            f"{json.dumps({'cmd': CMD_SUBSCRIBE, 'headers': {'req_id': subscribe_req_id}, 'body': self._mask_secret(body)}, ensure_ascii=False)}"
        )

        response = await self._send_request(
            cmd=CMD_SUBSCRIBE,
            body=body,
            req_id=subscribe_req_id,
            ensure_authenticated=False,
        )
        if response.get("errcode", 0) != 0:
            raise RuntimeError(f"企业微信长连接认证失败: {response.get('errmsg', 'unknown error')}")

        self._authenticated.set()
        logger.info("企业微信长连接认证成功")

    async def _heartbeat_loop(self) -> None:
        missed_acks = 0
        while not self._stop_event.is_set():
            await asyncio.sleep(self._adapter.config.HEARTBEAT_INTERVAL_SECONDS)
            try:
                await self._send_request(
                    cmd=CMD_HEARTBEAT,
                    body=None,
                    req_id=self._generate_req_id("ping"),
                )
                missed_acks = 0
            except Exception as e:
                missed_acks += 1
                logger.warning(f"企业微信心跳失败 {missed_acks} 次: {e}")
                if missed_acks >= 2:
                    if self._ws is not None:
                        await self._ws.close()
                    raise RuntimeError("企业微信长连接连续心跳失败，已主动断开")

    async def _handle_raw_message(self, raw_message: str) -> None:
        try:
            frame = json.loads(raw_message)
        except json.JSONDecodeError as e:
            logger.warning(f"企业微信长连接收到无法解析的消息: {e}")
            return

        if self._adapter.config.LOG_RAW_WS_FRAMES:
            self._adapter.log_raw_frame(frame)

        headers = frame.get("headers") or {}
        req_id = headers.get("req_id")
        cmd = frame.get("cmd")

        if isinstance(req_id, str) and req_id in self._pending and cmd not in {CMD_CALLBACK, CMD_EVENT_CALLBACK}:
            future = self._pending.pop(req_id)
            if not future.done():
                future.set_result(frame)
            return

        if cmd == CMD_CALLBACK:
            await self._adapter.handle_message_callback(frame)
            return

        if cmd == CMD_EVENT_CALLBACK:
            await self._adapter.handle_event_callback(frame)
            return

        logger.debug(f"收到未处理的企业微信长连接帧: {frame}")

    async def _send_request(
        self,
        *,
        cmd: str,
        body: dict[str, Any] | None,
        req_id: str,
        ensure_authenticated: bool = True,
    ) -> dict[str, Any]:
        if ensure_authenticated:
            await asyncio.wait_for(self._authenticated.wait(), timeout=self._adapter.config.REQUEST_TIMEOUT_SECONDS)
        if self._ws is None:
            raise RuntimeError("企业微信长连接未建立")

        future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future

        frame = {"cmd": cmd, "headers": {"req_id": req_id}}
        if body is not None:
            frame["body"] = body

        async with self._send_lock:
            await self._ws.send(json.dumps(frame, ensure_ascii=False))

        try:
            response = await asyncio.wait_for(future, timeout=self._adapter.config.REQUEST_TIMEOUT_SECONDS)
        except TimeoutError as e:
            self._pending.pop(req_id, None)
            raise RuntimeError(f"{cmd} 请求超时，{self._adapter.config.REQUEST_TIMEOUT_SECONDS}s 内未收到回执") from e
        except Exception:
            self._pending.pop(req_id, None)
            raise

        if response.get("errcode", 0) != 0:
            raise RuntimeError(f"{cmd} 失败: {response.get('errmsg', 'unknown error')}")
        return response

    def _fail_pending(self, exc: Exception) -> None:
        for req_id, future in list(self._pending.items()):
            if not future.done():
                future.set_exception(exc)
            self._pending.pop(req_id, None)

    def _generate_req_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"

    def _mask_secret(self, body: dict[str, Any]) -> dict[str, Any]:
        masked = dict(body)
        secret = str(masked.get("secret", ""))
        if secret:
            masked["secret"] = f"{secret[:3]}***{secret[-2:]}" if len(secret) > 5 else "***"
        return masked
