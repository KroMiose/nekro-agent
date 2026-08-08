from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import AppError
from nekro_agent.schemas.i18n import SupportedLang
from nekro_agent.services.mcp.web_chat_auth import is_valid_web_chat_mcp_token
from nekro_agent.services.user.deps import get_current_active_user, get_current_user
from nekro_agent.services.user.perm import Role

from .context import reset_current_user, set_current_user
from .server import mcp


class AuthenticatedMcpApp:
    """ASGI wrapper that lets NA own authentication before MCP handles requests."""

    def __init__(self, app: ASGIApp, session_manager: Any | None = None) -> None:
        self.app = app
        self.session_manager = session_manager
        self._startup_lock = asyncio.Lock()
        self._exit_stack: AsyncExitStack | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        try:
            user = await _resolve_mcp_user(request)
        except AppError as exc:
            await self._send_error(scope, receive, send, status_code=exc.http_status, message=exc.get_message(SupportedLang.ZH_CN))
            return
        except Exception:
            await self._send_error(scope, receive, send, status_code=401, message="未授权访问")
            return

        if user.perm_level < Role.Admin:
            await self._send_error(scope, receive, send, status_code=403, message="权限不足")
            return

        token = set_current_user(user)
        try:
            await self._ensure_started()
            await self.app(scope, receive, send)
        finally:
            reset_current_user(token)

    async def _ensure_started(self) -> None:
        if self.session_manager is None or self._exit_stack is not None:
            return
        async with self._startup_lock:
            if self._exit_stack is not None:
                return
            exit_stack = AsyncExitStack()
            await exit_stack.enter_async_context(self.session_manager.run())
            self._exit_stack = exit_stack

    @staticmethod
    async def _send_error(
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        status_code: int,
        message: str,
    ) -> None:
        await JSONResponse(
            {
                "error": "UnauthorizedError" if status_code == 401 else "PermissionDeniedError",
                "message": message,
            },
            status_code=status_code,
        )(scope, receive, send)


def create_web_chat_mcp_app() -> ASGIApp:
    app = mcp.streamable_http_app()
    return AuthenticatedMcpApp(app, mcp.session_manager)


async def _resolve_mcp_user(request: Request) -> DBUser:
    token = _extract_token(request)
    if token and is_valid_web_chat_mcp_token(token):
        from nekro_agent.schemas.errors import UnauthorizedError

        user = await DBUser.get_or_none(username="admin")
        if user is None:
            raise UnauthorizedError
        return await get_current_active_user(user)
    return await get_current_active_user(await get_current_user(request))


def _extract_token(request: Request) -> str:
    url_token = request.query_params.get("token")
    if url_token:
        return url_token.removeprefix("Bearer ").strip()
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return ""
