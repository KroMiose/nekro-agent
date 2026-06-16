from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

import httpx
import websockets

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv

from .config import QQBOT_API_BASE_URL, QQBOT_MARKDOWN_ENABLED, QQBOT_TOKEN_BASE_URL, QQBotOpenClawConfig
from .media import MediaFile
from .schemas import (
    QQBotGatewayPayload,
    QQBotMediaUploadResponse,
    QQBotMessageResponse,
    QQBotUploadPrepareResponse,
)

logger = get_sub_logger("adapter.qqbot_openclaw.client")

GROUP_AND_C2C_INTENT = 1 << 25
DIRECT_MESSAGE_INTENT = 1 << 12
PUBLIC_GUILD_MESSAGES_INTENT = 1 << 30
INTERACTION_INTENT = 1 << 26
FULL_INTENTS = GROUP_AND_C2C_INTENT | DIRECT_MESSAGE_INTENT | PUBLIC_GUILD_MESSAGES_INTENT | INTERACTION_INTENT


class QQBotOpenClawClient:
    def __init__(
        self,
        config: QQBotOpenClawConfig,
        on_event: Callable[[str, dict[str, Any]], Awaitable[None]],
    ) -> None:
        self.config = config
        self.on_event = on_event
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0))
        self._token = ""
        self._token_expires_at = 0.0
        self._token_lock = asyncio.Lock()
        self._runner_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._heartbeat_ack = True
        self._stop_event = asyncio.Event()
        self.session_id: str | None = None
        self.last_seq: int | None = None
        self.self_user_id = ""
        self.last_connected_at: float | None = None
        self.last_error: str | None = None
        self._msg_seq_by_msg_id: dict[str, int] = {}
        self._session_path = Path(OsEnv.DATA_DIR) / "adapters" / "qqbot_openclaw" / "session.json"
        self._load_session()

    @property
    def running(self) -> bool:
        return self._runner_task is not None and not self._runner_task.done()

    async def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._runner_task = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._runner_task:
            self._runner_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._runner_task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
        await self._http.aclose()

    async def clear_session(self) -> None:
        self.session_id = None
        self.last_seq = None
        self._heartbeat_ack = True
        with contextlib.suppress(FileNotFoundError):
            self._session_path.unlink()

    async def test_token(self) -> bool:
        token = await self.get_access_token(force_refresh=True)
        return bool(token)

    async def get_access_token(self, force_refresh: bool = False) -> str:
        now = time.time()
        if not force_refresh and self._token and now < self._token_expires_at - 60:
            return self._token

        async with self._token_lock:
            now = time.time()
            if not force_refresh and self._token and now < self._token_expires_at - 60:
                return self._token

            url = f"{QQBOT_TOKEN_BASE_URL}/app/getAppAccessToken"
            response = await self._http.post(
                url,
                json={"appId": self.config.APP_ID, "clientSecret": self.config.CLIENT_SECRET},
            )
            response.raise_for_status()
            data = response.json()
            token = str(data.get("access_token") or data.get("accessToken") or "")
            if not token:
                raise RuntimeError(f"OpenClaw QQBot token 响应缺少 access_token: {data}")
            expires_in = int(data.get("expires_in") or data.get("expiresIn") or 7200)
            self._token = token
            self._token_expires_at = time.time() + expires_in
            return token

    async def get_gateway_url(self) -> str:
        data = await self._request("GET", "/gateway")
        gateway = str(data.get("url") or "")
        if not gateway:
            raise RuntimeError(f"OpenClaw QQBot gateway 响应缺少 url: {data}")
        return gateway

    async def send_text(
        self,
        *,
        target_type: Literal["c2c", "group"],
        target_id: str,
        content: str,
        msg_id: str | None,
    ) -> QQBotMessageResponse:
        body: dict[str, Any] = {}
        if QQBOT_MARKDOWN_ENABLED:
            body["msg_type"] = 2
            body["markdown"] = {"content": content}
        else:
            body["msg_type"] = 0
            body["content"] = content
        if msg_id:
            body["msg_id"] = msg_id
            body["msg_seq"] = self.next_msg_seq(msg_id)
        return QQBotMessageResponse.model_validate(
            await self._request("POST", self._message_path(target_type, target_id), json_body=body),
        )

    async def upload_media(
        self,
        *,
        target_type: Literal["c2c", "group"],
        target_id: str,
        media: MediaFile,
    ) -> QQBotMediaUploadResponse:
        prepared = QQBotUploadPrepareResponse.model_validate(
            await self._request(
                "POST",
                self._upload_prepare_path(target_type, target_id),
                json_body={
                    "file_type": media.file_type,
                    "file_name": media.file_name,
                    "file_size": media.size,
                    "md5": media.md5,
                    "sha1": media.sha1,
                    "md5_10m": media.md5_10m,
                },
            ),
        )

        block_size = int(prepared.block_size or 0)
        retry_timeout = int(prepared.retry_timeout or 0) if prepared.retry_timeout else None

        with media.path.open("rb") as f:
            for position, part in enumerate(prepared.parts, start=1):
                part_index = int(part.index or part.part_number or position)
                offset = int(part.offset if part.offset is not None else (part_index - 1) * block_size)
                size = int(part.size if part.size is not None else min(block_size, media.size - offset))
                upload_url = part.presigned_url or part.upload_url or part.url
                if not upload_url or size <= 0:
                    continue
                f.seek(offset)
                chunk = f.read(size)
                chunk_md5 = hashlib.md5(chunk).hexdigest()  # noqa: S324 - OpenClaw 上传协议要求 MD5。
                upload_response = await self._http.put(upload_url, content=chunk)
                upload_response.raise_for_status()
                await self._finish_upload_part_with_retry(
                    target_type=target_type,
                    target_id=target_id,
                    body={"upload_id": prepared.upload_id, "part_index": part_index, "block_size": size, "md5": chunk_md5},
                    retry_timeout=retry_timeout,
                )

        return QQBotMediaUploadResponse.model_validate(
            await self._complete_upload_with_retry(
                target_type=target_type,
                target_id=target_id,
                body={"upload_id": prepared.upload_id},
            ),
        )

    async def send_media_message(
        self,
        *,
        target_type: Literal["c2c", "group"],
        target_id: str,
        file_info: str | dict[str, Any],
        content: str,
        msg_id: str | None,
    ) -> QQBotMessageResponse:
        body: dict[str, Any] = {
            "msg_type": 7,
            "media": {"file_info": file_info},
        }
        if content:
            body["content"] = content
        if msg_id:
            body["msg_id"] = msg_id
            body["msg_seq"] = self.next_msg_seq(msg_id)
        return QQBotMessageResponse.model_validate(
            await self._request("POST", self._message_path(target_type, target_id), json_body=body),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        token = await self.get_access_token()
        url = f"{QQBOT_API_BASE_URL}{path}"
        response = await self._http.request(
            method,
            url,
            json=json_body,
            headers={"Authorization": f"QQBot {token}", "User-Agent": "NekroAgent-QQBotOpenClaw"},
        )
        if response.status_code == 401 and retry_auth:
            self._token = ""
            return await self._request(method, path, json_body=json_body, retry_auth=False)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            detail = response.text.strip()
            body_preview = self._redact_request_body(json_body)
            raise RuntimeError(
                "OpenClaw QQBot HTTP 请求失败: "
                f"{method} {path} status={response.status_code}, response={detail or '<empty>'}, body={body_preview}",
            ) from e
        if not response.content:
            return {}
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}

    async def _run_forever(self) -> None:
        backoff = 2.0
        while not self._stop_event.is_set():
            try:
                gateway_url = await self.get_gateway_url()
                await self._connect_once(gateway_url)
                backoff = 2.0
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.last_error = str(e)
                logger.warning(f"OpenClaw QQBot Gateway 连接异常，{backoff:.0f}s 后重试: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.8, 60.0)

    async def _connect_once(self, gateway_url: str) -> None:
        try:
            async with websockets.connect(gateway_url) as ws:
                async for raw in ws:
                    payload = QQBotGatewayPayload.model_validate(json.loads(raw))
                    if payload.s is not None:
                        self.last_seq = payload.s
                        self._save_session()
                    if payload.op == 10:
                        hello_data = payload.d if isinstance(payload.d, dict) else {}
                        heartbeat_interval = int(hello_data.get("heartbeat_interval") or 45000)
                        await self._send_identify_or_resume(ws)
                        if self._heartbeat_task and not self._heartbeat_task.done():
                            self._heartbeat_task.cancel()
                        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws, heartbeat_interval / 1000))
                    elif payload.op == 0:
                        await self._handle_dispatch(payload)
                    elif payload.op == 7:
                        logger.info("OpenClaw QQBot Gateway 要求重连")
                        return
                    elif payload.op == 9:
                        logger.warning("OpenClaw QQBot Gateway session 无效，清理后重新 identify")
                        await self.clear_session()
                        return
                    elif payload.op == 11:
                        self._heartbeat_ack = True
        finally:
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._heartbeat_task

    async def _send_identify_or_resume(self, ws: Any) -> None:
        token = await self.get_access_token()
        if self.session_id and self.last_seq is not None:
            await ws.send(
                json.dumps(
                    {
                        "op": 6,
                        "d": {
                            "token": f"QQBot {token}",
                            "session_id": self.session_id,
                            "seq": self.last_seq,
                        },
                    },
                ),
            )
            return

        await ws.send(
            json.dumps(
                {
                    "op": 2,
                    "d": {
                        "token": f"QQBot {token}",
                        "intents": FULL_INTENTS,
                        "shard": [0, 1],
                        "properties": {"$os": "linux", "$browser": "nekro-agent", "$device": "nekro-agent"},
                    },
                },
            ),
        )

    async def _heartbeat_loop(self, ws: Any, interval_seconds: float) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(max(interval_seconds, 1.0))
            if not self._heartbeat_ack:
                raise RuntimeError("OpenClaw QQBot Gateway heartbeat ack timeout")
            self._heartbeat_ack = False
            await ws.send(json.dumps({"op": 1, "d": self.last_seq}))

    async def _handle_dispatch(self, payload: QQBotGatewayPayload) -> None:
        event_type = payload.t or ""
        data = payload.d if isinstance(payload.d, dict) else {}
        if event_type == "READY":
            self.session_id = str(data.get("session_id") or "")
            user = data.get("user")
            if isinstance(user, dict):
                self.self_user_id = str(user.get("id") or user.get("openid") or "")
            self.last_connected_at = time.time()
            self.last_error = None
            self._save_session()
            logger.info(f"OpenClaw QQBot Gateway READY: session={self.session_id}")
            return
        if event_type == "RESUMED":
            self.last_connected_at = time.time()
            self.last_error = None
            self._save_session()
            logger.info("OpenClaw QQBot Gateway RESUMED")
            return
        if event_type in {"C2C_MESSAGE_CREATE", "GROUP_AT_MESSAGE_CREATE", "GROUP_MESSAGE_CREATE"}:
            event_id = str(data.get("id") or "")
            logger.debug(f"收到 OpenClaw QQBot 消息事件: type={event_type}, id={event_id}")
            await self.on_event(event_type, data)
            return
        if event_type:
            logger.debug(f"忽略 OpenClaw QQBot 事件: {event_type}")

    def next_msg_seq(self, msg_id: str | None = None) -> int:
        if not msg_id:
            return 1
        next_value = self._msg_seq_by_msg_id.get(msg_id, 0) + 1
        self._msg_seq_by_msg_id[msg_id] = next_value
        return next_value

    async def _finish_upload_part_with_retry(
        self,
        *,
        target_type: Literal["c2c", "group"],
        target_id: str,
        body: dict[str, Any],
        retry_timeout: int | None,
    ) -> None:
        path = self._upload_part_finish_path(target_type, target_id)
        deadline = time.monotonic() + min(max(retry_timeout or 120, 1), 600)
        attempt = 0
        last_error: Exception | None = None
        while True:
            try:
                await self._request("POST", path, json_body=body)
                return
            except Exception as e:
                last_error = e
                if attempt >= 2 and time.monotonic() >= deadline:
                    raise
                delay = 1.0 if "40093001" in str(e) and time.monotonic() < deadline else min(2**attempt, 4)
                logger.warning(
                    "OpenClaw QQBot 分片完成失败，准备重试: "
                    f"path={path}, part_index={body.get('part_index')}, attempt={attempt + 1}, error={e}",
                )
                await asyncio.sleep(delay)
                attempt += 1
                if attempt > 2 and "40093001" not in str(last_error):
                    raise last_error

    async def _complete_upload_with_retry(
        self,
        *,
        target_type: Literal["c2c", "group"],
        target_id: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        path = self._files_path(target_type, target_id)
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await self._request("POST", path, json_body=body)
            except Exception as e:
                last_error = e
                if attempt >= 2:
                    break
                delay = 2**attempt * 2
                logger.warning(f"OpenClaw QQBot 完成上传失败，{delay}s 后重试: path={path}, error={e}")
                await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    def _redact_request_body(self, body: dict[str, Any] | None) -> dict[str, Any] | None:
        if body is None:
            return None
        redacted = dict(body)
        if "content" in redacted and isinstance(redacted["content"], str):
            redacted["content"] = redacted["content"][:200]
        markdown = redacted.get("markdown")
        if isinstance(markdown, dict) and isinstance(markdown.get("content"), str):
            redacted["markdown"] = {**markdown, "content": markdown["content"][:200]}
        return redacted

    def _message_path(self, target_type: Literal["c2c", "group"], target_id: str) -> str:
        return f"/v2/users/{target_id}/messages" if target_type == "c2c" else f"/v2/groups/{target_id}/messages"

    def _files_path(self, target_type: Literal["c2c", "group"], target_id: str) -> str:
        return f"/v2/users/{target_id}/files" if target_type == "c2c" else f"/v2/groups/{target_id}/files"

    def _upload_prepare_path(self, target_type: Literal["c2c", "group"], target_id: str) -> str:
        return (
            f"/v2/users/{target_id}/upload_prepare"
            if target_type == "c2c"
            else f"/v2/groups/{target_id}/upload_prepare"
        )

    def _upload_part_finish_path(self, target_type: Literal["c2c", "group"], target_id: str) -> str:
        return (
            f"/v2/users/{target_id}/upload_part_finish"
            if target_type == "c2c"
            else f"/v2/groups/{target_id}/upload_part_finish"
        )

    def _load_session(self) -> None:
        try:
            if not self._session_path.exists():
                return
            data = json.loads(self._session_path.read_text(encoding="utf-8"))
            if data.get("app_id") != self.config.APP_ID:
                self._session_path.unlink(missing_ok=True)
                return
            saved_at = float(data.get("saved_at") or 0)
            if time.time() - saved_at > 5 * 60:
                self._session_path.unlink(missing_ok=True)
                return
            self.session_id = str(data.get("session_id") or "") or None
            last_seq = data.get("last_seq")
            self.last_seq = int(last_seq) if last_seq is not None else None
        except Exception as e:
            logger.warning(f"OpenClaw QQBot session 加载失败，忽略旧 session: {e}")

    def _save_session(self) -> None:
        if not self.session_id or self.last_seq is None:
            return
        try:
            self._session_path.parent.mkdir(parents=True, exist_ok=True)
            self._session_path.write_text(
                json.dumps(
                    {
                        "session_id": self.session_id,
                        "last_seq": self.last_seq,
                        "app_id": self.config.APP_ID,
                        "saved_at": time.time(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as e:
            logger.debug(f"OpenClaw QQBot session 保存失败: {e}")
