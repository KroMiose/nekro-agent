from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from nekro_agent.schemas.errors import AppError

from .service import WebChatMcpService, app_error_result

mcp = FastMCP(
    "nekro-web-chat",
    instructions=(
        "Control Nekro Agent Web Chat for plugin and conversation testing. "
        "This MCP app is mounted by Nekro Agent and uses Nekro Agent authentication."
    ),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
            "172.17.0.1:*",
            "host.docker.internal:*",
        ],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
            "http://172.17.0.1:*",
            "http://host.docker.internal:*",
        ],
    ),
)


def _client() -> WebChatMcpService:
    return WebChatMcpService()


@mcp.tool(description="Check Nekro Agent API authentication and Web Adapter availability.")
async def check_web_chat_status() -> dict[str, Any]:
    try:
        return await _client().check_status()
    except AppError as exc:
        return app_error_result(exc)


@mcp.tool(description="List Web Chat test sessions.")
async def list_web_chat_sessions(page: int = 1, page_size: int = 20, search: str = "") -> dict[str, Any]:
    try:
        return await _client().list_sessions(page=page, page_size=page_size, search=search)
    except AppError as exc:
        return app_error_result(exc)


@mcp.tool(description="Create a Web Chat test session and return its chat_key.")
async def create_web_chat_session(name: str = "") -> dict[str, Any]:
    try:
        return await _client().create_session(name=name)
    except AppError as exc:
        return app_error_result(exc)


@mcp.tool(description="Rename a Web Chat test session.")
async def rename_web_chat_session(chat_key: str, name: str) -> dict[str, Any]:
    try:
        return await _client().rename_session(chat_key, name=name)
    except AppError as exc:
        return app_error_result(exc)


@mcp.tool(description="Delete a Web Chat test session. Requires confirm=true because this clears related data.")
async def delete_web_chat_session(chat_key: str, confirm: bool = False) -> dict[str, Any]:
    try:
        return await _client().delete_session(chat_key, confirm=confirm)
    except AppError as exc:
        return app_error_result(exc)


@mcp.tool(description="Send a text message into a Web Chat session as the web user.")
async def send_web_chat_message(chat_key: str, content: str) -> dict[str, Any]:
    try:
        return await _client().send_message(chat_key, content=content)
    except AppError as exc:
        return app_error_result(exc)


@mcp.tool(description="Upload one file or image into a Web Chat session as the web user.")
async def send_web_chat_file(chat_key: str, file_path: str, content: str = "") -> dict[str, Any]:
    try:
        return await _client().send_file(chat_key, file_path=file_path, content=content)
    except AppError as exc:
        return app_error_result(exc)


@mcp.tool(description="Read Web Chat message history in chronological order.")
async def get_web_chat_messages(
    chat_key: str,
    before_id: int | None = None,
    page_size: int = 32,
    include_segments: bool = True,
) -> dict[str, Any]:
    try:
        return await _client().get_messages(
            chat_key,
            before_id=before_id,
            page_size=page_size,
            include_segments=include_segments,
        )
    except AppError as exc:
        return app_error_result(exc)


@mcp.tool(description="Read Web Chat channel detail, including status and send capability fields.")
async def get_web_chat_channel_detail(chat_key: str) -> dict[str, Any]:
    try:
        return await _client().get_channel_detail(chat_key)
    except AppError as exc:
        return app_error_result(exc)


@mcp.tool(description="Wait until an Agent reply appears after a message id or database id.")
async def wait_for_web_chat_reply(
    chat_key: str,
    after_id: int | None = None,
    after_message_id: str = "",
    timeout_seconds: float | None = None,
    poll_interval_seconds: float | None = None,
) -> dict[str, Any]:
    try:
        return await _client().wait_for_reply(
            chat_key,
            after_id=after_id,
            after_message_id=after_message_id,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
    except AppError as exc:
        return app_error_result(exc)


@mcp.tool(description="Send text into Web Chat, then wait for the next Agent reply.")
async def send_and_wait_web_chat_reply(
    chat_key: str,
    content: str,
    timeout_seconds: float | None = None,
    poll_interval_seconds: float | None = None,
) -> dict[str, Any]:
    try:
        return await _client().send_and_wait(
            chat_key,
            content=content,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
    except AppError as exc:
        return app_error_result(exc)


def main() -> None:
    raise RuntimeError("Web Chat MCP is mounted by Nekro Agent; do not start it as a standalone stdio server.")


if __name__ == "__main__":
    main()
