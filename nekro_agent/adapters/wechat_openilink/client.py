import asyncio
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from nekro_agent.core.logger import get_sub_logger

from .config import WeChatOpenILinkConfig

logger = get_sub_logger("adapter.wechat_openilink")

class WeChatOpenILinkClient:
    def __init__(self, config: WeChatOpenILinkConfig):
        self.config = config
        self._client: Any = None
        self._polling_task: Optional[asyncio.Task[Any]] = None
        self._login_task: Optional[asyncio.Task[Any]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._self_user_id = ""
        self._self_user_name = ""

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def self_user_id(self) -> str:
        return self._self_user_id

    @property
    def self_user_name(self) -> str:
        return self._self_user_name

    async def start(self, on_message: Callable[[Any], Awaitable[Any]]) -> None:
        if self._running:
            return

        self._loop = asyncio.get_running_loop()
        self._client = self._create_sdk_client()

        @self._client.on_message
        async def _handler(message: Any) -> None:
            await on_message(message)

        self._running = True
        self._login_task = asyncio.create_task(self._login_and_start_polling())

    async def stop(self) -> None:
        self._running = False

        if self._login_task and not self._login_task.done():
            self._login_task.cancel()
            try:
                await self._login_task
            except asyncio.CancelledError:
                pass
            finally:
                self._login_task = None

        if self._client is not None:
            stop = getattr(self._client, "stop", None)
            if callable(stop):
                stop()

        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            finally:
                self._polling_task = None

    async def send_text(self, to_user_id: str, text: str, ref_msg: Any | None = None) -> str:
        if self._client is None:
            raise RuntimeError("WeChatBot client not initialized")

        try:
            if ref_msg is not None:
                result = await self._client.reply(ref_msg, text)
            else:
                result = await self._client.send(to_user_id, text)
            return self._extract_message_id(result)
        except Exception as e:
            from wechatbot.errors import NoContextError

            if isinstance(e, NoContextError) and ref_msg is not None:
                result = await self._client.send(to_user_id, text)
                return self._extract_message_id(result)
            raise

    async def send_image(self, to_user_id: str, file_path: str, ref_msg: Any | None = None) -> str:
        data = await asyncio.to_thread(Path(file_path).read_bytes)
        return await self._send_media_bytes(
            to_user_id=to_user_id,
            payload={"image": data},
            ref_msg=ref_msg,
        )

    async def send_file(self, to_user_id: str, file_path: str, ref_msg: Any | None = None) -> str:
        data = await asyncio.to_thread(Path(file_path).read_bytes)
        file_name = Path(file_path).name or "file.bin"
        return await self._send_media_bytes(
            to_user_id=to_user_id,
            payload={"file": data, "file_name": file_name},
            ref_msg=ref_msg,
        )

    async def send_voice(self, to_user_id: str, file_path: str, ref_msg: Any | None = None) -> str:
        data = await asyncio.to_thread(Path(file_path).read_bytes)
        src_path = Path(file_path)
        suffix = src_path.suffix.lower() or ".amr"
        file_name = f"{src_path.stem or 'voice'}{suffix}"
        return await self._send_media_bytes(
            to_user_id=to_user_id,
            payload={"file": data, "file_name": file_name},
            ref_msg=ref_msg,
        )

    async def _send_media_bytes(
        self,
        *,
        to_user_id: str,
        payload: dict[str, Any],
        ref_msg: Any | None = None,
    ) -> str:
        if self._client is None:
            raise RuntimeError("WeChatBot client not initialized")

        try:
            if ref_msg is not None:
                result = await self._client.reply_media(ref_msg, payload)
            else:
                result = await self._client.send_media(to_user_id, payload)
            return self._extract_message_id(result)
        except Exception as e:
            from wechatbot.errors import NoContextError

            if isinstance(e, NoContextError) and ref_msg is not None:
                result = await self._client.send_media(to_user_id, payload)
                return self._extract_message_id(result)
            raise

    async def _login_and_start_polling(self) -> None:
        if self._client is None:
            self._running = False
            return

        try:
            heartbeat = max(min(self.config.LOGIN_TIMEOUT_SECONDS // 6, 30), 10)
            timeout = max(self.config.LOGIN_TIMEOUT_SECONDS, 1)
            login_task = asyncio.create_task(self._client.login())
            deadline = asyncio.get_running_loop().time() + timeout
            while not login_task.done():
                logger.info("WeChatBot 正在等待扫码登录...")
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    login_task.cancel()
                    try:
                        await login_task
                    except asyncio.CancelledError:
                        pass
                    raise asyncio.TimeoutError
                await asyncio.sleep(min(heartbeat, remaining))

            await login_task
            self._refresh_self_info_from_client()
            self._polling_task = asyncio.create_task(self._run_polling())
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            self._running = False
            logger.error("WeChatBot 登录超时")
        except Exception as e:
            self._running = False
            logger.error(f"WeChatBot 登录失败: {e}")
        finally:
            self._login_task = None

    async def _run_polling(self) -> None:
        if self._client is None:
            return

        while self._running:
            try:
                await self._client.start()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"WeChatBot 长轮询异常，2 秒后重试: {e}")
                await asyncio.sleep(2)

    def _create_sdk_client(self) -> Any:
        try:
            from wechatbot import WeChatBot
        except Exception as e:
            raise RuntimeError("未安装 wechatbot-sdk，请先同步依赖（poe sync / poe sync-dev）") from e

        self._hook_wechatbot_logger(WeChatBot)

        return WeChatBot(
            base_url=self.config.BASE_URL,
            cred_path=self.config.CRED_PATH,
            on_qr_url=lambda url: self._dispatch_login_event("qr", str(url)),
            on_scanned=lambda: self._dispatch_login_event("scanned", None),
            on_expired=lambda: self._dispatch_login_event("expired", None),
            on_error=lambda err: self._dispatch_login_event("error", str(err)),
        )

    def _hook_wechatbot_logger(self, bot_cls: Any) -> None:
        if getattr(bot_cls, "_nekro_log_hooked", False):
            return

        original_log = getattr(bot_cls, "_log", None)
        if not callable(original_log):
            return

        def _nekro_log(instance: Any, msg: str) -> None:  # noqa: ARG001
            logger.info(f"[wechatbot-sdk] {msg}")

        setattr(bot_cls, "_log", _nekro_log)
        setattr(bot_cls, "_nekro_log_hooked", True)

    def _dispatch_login_event(self, event: str, payload: str | None) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return

        def _schedule() -> None:
            asyncio.create_task(self._handle_login_event(event, payload))

        loop.call_soon_threadsafe(_schedule)

    async def _handle_login_event(self, event: str, payload: str | None) -> None:
        if event == "qr" and payload:
            logger.info(f"WeChatBot 登录二维码网址: {payload}")
            return
        if event == "scanned":
            logger.info("WeChatBot 已扫码，请在手机上确认...")
            return
        if event == "expired":
            logger.info("WeChatBot 二维码已过期，等待刷新...")
            return
        if event == "error" and payload:
            logger.warning(f"WeChatBot 登录异常: {payload}")

    def _refresh_self_info_from_client(self) -> None:
        if self._client is None:
            return
        user_id = str(getattr(self._client, "user_id", "") or "")
        self._self_user_id = user_id
        self._self_user_name = user_id

    def _extract_message_id(self, result: Any) -> str:
        if result is None:
            return ""
        for key in ("message_id", "msg_id", "id"):
            value = getattr(result, key, None)
            if value:
                return str(value)
        if isinstance(result, dict):
            for key in ("message_id", "msg_id", "id"):
                value = result.get(key)
                if value:
                    return str(value)
        return ""
