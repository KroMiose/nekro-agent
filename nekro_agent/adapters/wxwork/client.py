import asyncio
import base64
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Coroutine, Dict, Optional

from websockets import connect
from websockets.asyncio.client import ClientConnection

from nekro_agent.core.logger import get_sub_logger


if TYPE_CHECKING:
    from .adapter import WxWorkAdapter


logger = get_sub_logger("adapter.wxwork")

WXWORK_OFFICIAL_WS_URL = "wss://openws.work.weixin.qq.com"

CMD_SUBSCRIBE = "aibot_subscribe"
CMD_HEARTBEAT = "ping"
CMD_CALLBACK = "aibot_msg_callback"
CMD_EVENT_CALLBACK = "aibot_event_callback"
CMD_SEND_MSG = "aibot_send_msg"
CMD_UPLOAD_MEDIA_INIT = "aibot_upload_media_init"
CMD_UPLOAD_MEDIA_CHUNK = "aibot_upload_media_chunk"
CMD_UPLOAD_MEDIA_FINISH = "aibot_upload_media_finish"
UPLOAD_MEDIA_CHUNK_SIZE = 512 * 1024
UPLOAD_MEDIA_MAX_CHUNKS = 100
WXWORK_DIRECT_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
MARKDOWN_LINK_DEF_LINE_RE = re.compile(r"(?m)^(?P<label>\[[^\]\n]{1,256}\]:)")


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
        self._callback_tasks: set[asyncio.Task[None]] = set()
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

        await self._cancel_callback_tasks()
        self._fail_pending(RuntimeError("企业微信长连接已停止"))

    async def send_text_message(
        self,
        chatid: str,
        content: str,
        mentioned_list: list[str] | None = None,
    ) -> dict[str, Any]:
        content = self._escape_markdown_link_definition_lines(content)
        body = {
            "chatid": chatid,
            # 官方 SDK 的 aibot_send_msg 主动发送仅支持 markdown / template_card / media，
            # 这里将普通文本统一走 markdown 通道，避免 text 类型触发 40008。
            "msgtype": "markdown",
            "markdown": {"content": content},
        }
        if mentioned_list:
            logger.info(
                "企业微信 AI Bot 主动发送当前走 markdown 通道，mentioned_list 参数将退化为正文中的普通文本 @ 展示"
            )
        return await self._send_request(
            cmd=CMD_SEND_MSG,
            body=body,
            req_id=self._generate_req_id("send"),
        )

    async def send_media_message(
        self,
        chatid: str,
        *,
        media_type: str,
        file_path: str,
    ) -> dict[str, Any]:
        if media_type not in {"image", "file"}:
            raise ValueError(f"企业微信 AI Bot 暂不支持的媒体类型: {media_type}")

        upload_result = await self.upload_media(file_path=file_path, media_type=media_type)
        media_id = str((upload_result.get("body") or {}).get("media_id") or upload_result.get("media_id") or "").strip()
        if not media_id:
            raise RuntimeError(f"企业微信 AI Bot 上传{media_type}成功但响应缺少 media_id")

        body = {
            "chatid": chatid,
            "msgtype": media_type,
            media_type: {"media_id": media_id},
        }
        return await self._send_request(
            cmd=CMD_SEND_MSG,
            body=body,
            req_id=self._generate_req_id(f"send_{media_type}"),
        )

    async def upload_media(
        self,
        *,
        file_path: str,
        media_type: str,
    ) -> dict[str, Any]:
        filename, file_buffer = self._prepare_media_upload(file_path=file_path, media_type=media_type)
        if not file_buffer:
            raise ValueError(f"企业微信 AI Bot 不支持上传空文件: {file_path}")

        total_size = len(file_buffer)
        total_chunks = (total_size + UPLOAD_MEDIA_CHUNK_SIZE - 1) // UPLOAD_MEDIA_CHUNK_SIZE
        if total_chunks > UPLOAD_MEDIA_MAX_CHUNKS:
            raise ValueError(
                f"企业微信 AI Bot 上传文件过大: {file_path} 需要 {total_chunks} 个分片，超过 {UPLOAD_MEDIA_MAX_CHUNKS} 个分片上限"
            )

        init_body = {
            "type": media_type,
            "filename": filename,
            "total_size": total_size,
            "total_chunks": total_chunks,
            "md5": hashlib.md5(file_buffer).hexdigest(),
        }
        logger.info(
            f"企业微信 AI Bot 开始上传媒体: type={media_type}, filename={filename}, size={total_size}, chunks={total_chunks}"
        )
        init_response = await self._send_request(
            cmd=CMD_UPLOAD_MEDIA_INIT,
            body=init_body,
            req_id=self._generate_req_id("upload_init"),
        )

        upload_id = str((init_response.get("body") or {}).get("upload_id") or "").strip()
        if not upload_id:
            raise RuntimeError(f"企业微信 AI Bot 初始化上传成功但响应缺少 upload_id: {init_response}")

        for chunk_index in range(total_chunks):
            start = chunk_index * UPLOAD_MEDIA_CHUNK_SIZE
            end = min(start + UPLOAD_MEDIA_CHUNK_SIZE, total_size)
            chunk = file_buffer[start:end]
            chunk_body = {
                "upload_id": upload_id,
                "chunk_index": chunk_index,
                "base64_data": base64.b64encode(chunk).decode("ascii"),
            }
            await self._send_request(
                cmd=CMD_UPLOAD_MEDIA_CHUNK,
                body=chunk_body,
                req_id=self._generate_req_id("upload_chunk"),
            )

        finish_response = await self._send_request(
            cmd=CMD_UPLOAD_MEDIA_FINISH,
            body={"upload_id": upload_id},
            req_id=self._generate_req_id("upload_finish"),
        )
        logger.info(f"企业微信 AI Bot 媒体上传完成: filename={filename}, type={media_type}")
        return finish_response

    def _prepare_media_upload(self, *, file_path: str, media_type: str) -> tuple[str, bytes]:
        file = Path(file_path)
        if not file.exists() or not file.is_file():
            raise FileNotFoundError(f"企业微信 AI Bot 上传文件不存在: {file_path}")

        if media_type != "image":
            return file.name, file.read_bytes()

        if file.suffix.lower() in WXWORK_DIRECT_IMAGE_SUFFIXES:
            return file.name, file.read_bytes()

        raise ValueError(
            f"企业微信 AI Bot 暂不支持发送 {file.suffix.lower() or '未知'} 格式图片，仅支持 jpg/jpeg/png: {file.name}"
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
                    "ssl": True,
                }

                async with connect(WXWORK_OFFICIAL_WS_URL, **connect_kwargs) as ws:
                    self._ws = ws
                    attempt = 0
                    logger.info(f"企业微信长连接已建立，开始认证: {WXWORK_OFFICIAL_WS_URL}")

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
                await self._cancel_callback_tasks()

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
            self._schedule_callback_task(self._adapter.handle_message_callback(frame))
            return

        if cmd == CMD_EVENT_CALLBACK:
            self._schedule_callback_task(self._adapter.handle_event_callback(frame))
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

    def _escape_markdown_link_definition_lines(self, content: str) -> str:
        """避免 `[label]: xxx` 在 Markdown 中被识别为引用定义而不可见。"""
        return MARKDOWN_LINK_DEF_LINE_RE.sub(r"\\\g<label>", content)

    def _schedule_callback_task(self, coro: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coro)
        self._callback_tasks.add(task)
        task.add_done_callback(self._on_callback_task_done)

    def _on_callback_task_done(self, task: asyncio.Task[None]) -> None:
        self._callback_tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.opt(exception=exc).error("企业微信回调后台任务执行失败")

    async def _cancel_callback_tasks(self) -> None:
        if not self._callback_tasks:
            return

        tasks = list(self._callback_tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._callback_tasks.clear()
