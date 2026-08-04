from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest

from nekro_agent.core import auto_inject_mcp
from nekro_agent.services.mcp import web_chat_auth
from nekro_agent.services.mcp.registry import get_registry
from nekro_agent.services.user.role import Role
from nekro_agent.services.workspace.manager import _build_disk_mcp_config
from web_chat_mcp.na_app import AuthenticatedMcpApp
from web_chat_mcp.service import ChatMessageItem, WebChatMcpService


@pytest.mark.asyncio
async def test_authenticated_mcp_app_rejects_missing_auth() -> None:
    async def inner_app(_scope: dict[str, Any], _receive: Any, _send: Any) -> None:
        raise AssertionError("unauthenticated request should not reach MCP app")

    transport = httpx.ASGITransport(app=AuthenticatedMcpApp(inner_app))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/mcp")

    assert response.status_code == 401
    assert response.json()["error"] == "UnauthorizedError"


@pytest.mark.asyncio
async def test_authenticated_mcp_app_accepts_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    class FakeUser:
        is_active = True
        perm_level = Role.Admin

    async def fake_get_current_user(_request: Any) -> FakeUser:
        return FakeUser()

    async def inner_app(_scope: dict[str, Any], _receive: Any, send: Any) -> None:
        nonlocal called
        called = True
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    monkeypatch.setattr("web_chat_mcp.na_app.get_current_user", fake_get_current_user)
    transport = httpx.ASGITransport(app=AuthenticatedMcpApp(inner_app))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/mcp")

    assert response.status_code == 204
    assert called is True


@pytest.mark.asyncio
async def test_authenticated_mcp_app_starts_session_manager_before_inner_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeUser:
        is_active = True
        perm_level = Role.Admin

    class FakeSessionManager:
        started = False

        @asynccontextmanager
        async def run(self):
            self.started = True
            yield

    session_manager = FakeSessionManager()

    async def fake_get_current_user(_request: Any) -> FakeUser:
        return FakeUser()

    async def inner_app(_scope: dict[str, Any], _receive: Any, send: Any) -> None:
        assert session_manager.started is True
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    monkeypatch.setattr("web_chat_mcp.na_app.get_current_user", fake_get_current_user)
    transport = httpx.ASGITransport(app=AuthenticatedMcpApp(inner_app, session_manager))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/mcp")

    assert response.status_code == 204
    assert session_manager.started is True


@pytest.mark.asyncio
async def test_authenticated_mcp_app_accepts_generated_mcp_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called = False
    monkeypatch.setattr(web_chat_auth, "_TOKEN_PATH", tmp_path / "web-chat-mcp-token.json")
    token = web_chat_auth.get_web_chat_mcp_token()

    class FakeUser:
        is_active = True
        perm_level = Role.Admin

    async def fake_get_or_none(**_kwargs: Any) -> FakeUser:
        return FakeUser()

    async def inner_app(_scope: dict[str, Any], _receive: Any, send: Any) -> None:
        nonlocal called
        called = True
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    monkeypatch.setattr("web_chat_mcp.na_app.DBUser.get_or_none", fake_get_or_none)
    transport = httpx.ASGITransport(app=AuthenticatedMcpApp(inner_app))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/mcp", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 204
    assert called is True


@pytest.mark.asyncio
async def test_authenticated_mcp_app_rejects_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeUser:
        is_active = True
        perm_level = Role.User

    async def fake_get_current_user(_request: Any) -> FakeUser:
        return FakeUser()

    async def inner_app(_scope: dict[str, Any], _receive: Any, _send: Any) -> None:
        raise AssertionError("non-admin request should not reach MCP app")

    monkeypatch.setattr("web_chat_mcp.na_app.get_current_user", fake_get_current_user)
    transport = httpx.ASGITransport(app=AuthenticatedMcpApp(inner_app))
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/mcp")

    assert response.status_code == 403
    assert response.json()["error"] == "PermissionDeniedError"


@pytest.mark.asyncio
async def test_registered_tools_include_send_and_wait() -> None:
    from web_chat_mcp.server import mcp

    tools = await mcp.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "send_and_wait_web_chat_reply" in tool_names
    assert "send_web_chat_message" in tool_names


def test_web_chat_mcp_allows_docker_gateway_host_header() -> None:
    from web_chat_mcp.server import mcp

    security = mcp.settings.transport_security

    assert security is not None
    assert security.enable_dns_rebinding_protection is True
    assert "172.17.0.1:*" in security.allowed_hosts
    assert "host.docker.internal:*" in security.allowed_hosts


def test_registry_injects_generated_web_chat_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(web_chat_auth, "_TOKEN_PATH", tmp_path / "web-chat-mcp-token.json")

    item = next(entry for entry in get_registry() if entry.id == web_chat_auth.WEB_CHAT_MCP_SERVER_ID)
    authorization = item.headers["Authorization"]

    assert authorization.startswith("Bearer ")
    assert "<NA_ACCESS_TOKEN>" not in authorization
    assert authorization == f"Bearer {web_chat_auth.get_web_chat_mcp_token()}"


def test_auto_inject_library_contains_configured_web_chat_mcp(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(auto_inject_mcp, "_AUTO_INJECT_PATH", tmp_path / "auto-inject-mcp.json")
    monkeypatch.setattr(web_chat_auth, "_TOKEN_PATH", tmp_path / "web-chat-mcp-token.json")

    servers = auto_inject_mcp.get_auto_inject_mcp_servers()
    web_chat = next(server for server in servers if server["name"] == web_chat_auth.WEB_CHAT_MCP_SERVER_NAME)

    assert web_chat["type"] == "http"
    assert web_chat["id"] == web_chat_auth.WEB_CHAT_MCP_SERVER_ID
    assert web_chat["url"] == web_chat_auth.WEB_CHAT_MCP_URL
    assert web_chat["headers"]["Authorization"] == f"Bearer {web_chat_auth.get_web_chat_mcp_token()}"
    assert web_chat["validation"]["status"] == "validated"


def test_disk_mcp_config_uses_claude_code_schema_for_http() -> None:
    metadata = {"mcp_servers_enabled": [web_chat_auth.WEB_CHAT_MCP_SERVER_NAME]}
    library = {
        web_chat_auth.WEB_CHAT_MCP_SERVER_NAME: {
            "id": web_chat_auth.WEB_CHAT_MCP_SERVER_ID,
            "name": web_chat_auth.WEB_CHAT_MCP_SERVER_NAME,
            "type": "http",
            "url": web_chat_auth.WEB_CHAT_MCP_URL,
            "headers": {"Authorization": "Bearer test"},
            "validation": {"status": "validated"},
        },
    }

    disk_config = _build_disk_mcp_config(metadata, library=library)
    web_chat = disk_config["mcpServers"][web_chat_auth.WEB_CHAT_MCP_SERVER_NAME]

    assert web_chat["type"] == "http"
    assert "transport" not in web_chat
    assert web_chat["url"] == web_chat_auth.WEB_CHAT_MCP_URL
    assert web_chat["headers"]["Authorization"] == "Bearer test"


def test_auto_inject_library_keeps_web_chat_mcp_deleted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(auto_inject_mcp, "_AUTO_INJECT_PATH", tmp_path / "auto-inject-mcp.json")
    monkeypatch.setattr(web_chat_auth, "_TOKEN_PATH", tmp_path / "web-chat-mcp-token.json")

    auto_inject_mcp.set_auto_inject_mcp_servers([])

    assert auto_inject_mcp.get_auto_inject_mcp_servers() == []


def test_auto_inject_library_deduplicates_web_chat_mcp_variants(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(auto_inject_mcp, "_AUTO_INJECT_PATH", tmp_path / "auto-inject-mcp.json")
    monkeypatch.setattr(web_chat_auth, "_TOKEN_PATH", tmp_path / "web-chat-mcp-token.json")

    auto_inject_mcp.set_auto_inject_mcp_servers(
        [
            {
                "name": "NekroWebChatTest",
                "type": "http",
                "url": web_chat_auth.WEB_CHAT_MCP_URL,
                "headers": {},
            },
            {
                "name": "Nekro-Web-Chat-Test",
                "type": "http",
                "url": web_chat_auth.WEB_CHAT_MCP_URL,
                "headers": {"Authorization": "Bearer stale"},
            },
            {
                "name": web_chat_auth.WEB_CHAT_MCP_SERVER_NAME,
                "type": "http",
                "auto_inject": True,
                "url": web_chat_auth.WEB_CHAT_MCP_URL,
                "headers": {},
                "validation": {"status": "validated", "server_name": "nekro-web-chat"},
            },
        ],
    )

    servers = auto_inject_mcp.get_auto_inject_mcp_servers()

    assert [server["name"] for server in servers] == [web_chat_auth.WEB_CHAT_MCP_SERVER_NAME]
    assert servers[0]["auto_inject"] is True
    assert servers[0]["headers"]["Authorization"] == f"Bearer {web_chat_auth.get_web_chat_mcp_token()}"


def test_auto_inject_library_preserves_edited_web_chat_mcp_name_and_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(auto_inject_mcp, "_AUTO_INJECT_PATH", tmp_path / "auto-inject-mcp.json")
    monkeypatch.setattr(web_chat_auth, "_TOKEN_PATH", tmp_path / "web-chat-mcp-token.json")
    custom_url = "http://127.0.0.1:8021/api/mcp/web-chat/mcp"

    auto_inject_mcp.set_auto_inject_mcp_servers(
        [
            {
                "id": web_chat_auth.WEB_CHAT_MCP_SERVER_ID,
                "name": "Local Web Chat MCP",
                "type": "http",
                "auto_inject": False,
                "url": custom_url,
                "headers": {"Authorization": "Bearer stale"},
            },
        ],
    )

    servers = auto_inject_mcp.get_auto_inject_mcp_servers()

    assert servers[0]["id"] == web_chat_auth.WEB_CHAT_MCP_SERVER_ID
    assert servers[0]["name"] == "Local Web Chat MCP"
    assert servers[0]["url"] == custom_url
    assert servers[0]["headers"]["Authorization"] == f"Bearer {web_chat_auth.get_web_chat_mcp_token()}"


@pytest.mark.asyncio
async def test_delete_session_requires_confirmation() -> None:
    result = await WebChatMcpService().delete_session("web-session_test", confirm=False)

    assert result["ok"] is False
    assert result["status"] == "confirmation_required"


@pytest.mark.asyncio
async def test_file_upload_requires_allowlist(tmp_path: Path) -> None:
    upload_file = tmp_path / "input.txt"
    upload_file.write_text("hello", encoding="utf-8")

    result = await WebChatMcpService().send_file("web-session_test", file_path=str(upload_file))

    assert result["ok"] is False
    assert result["status"] == "file_not_allowed"


def test_chat_message_item_marks_system_message_before_agent() -> None:
    item = ChatMessageItem(
        id=1,
        sender_id="-1",
        sender_name="SYSTEM",
        sender_nickname="SYSTEM",
        platform_userid="0",
        content="system notice",
        chat_key="web-session_test",
        create_time="2026-08-05 00:00:00",
    )

    assert item.role == "system"
