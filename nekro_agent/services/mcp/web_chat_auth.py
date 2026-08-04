"""Web Chat MCP 专用鉴权与内置配置。"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from hmac import compare_digest
from pathlib import Path
from typing import Any, Dict

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv

logger = get_sub_logger("web_chat_mcp.auth")

WEB_CHAT_MCP_SERVER_ID = "nekro-web-chat"
WEB_CHAT_MCP_SERVER_NAME = "NekroWebChatTest"
WEB_CHAT_MCP_URL = os.getenv(
    "NEKRO_WEB_CHAT_MCP_URL",
    "http://host.docker.internal:8021/api/mcp/web-chat/mcp",
)

_TOKEN_PATH = Path(OsEnv.DATA_DIR) / "configs" / "web-chat-mcp-token.json"


def get_web_chat_mcp_token() -> str:
    """获取 Web Chat MCP 专用 token，不存在时自动生成并持久化。"""
    existing = _read_token()
    if existing:
        return existing

    token = secrets.token_urlsafe(48)
    _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN_PATH.write_text(
        json.dumps(
            {
                "token": token,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "purpose": "web-chat-mcp",
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    try:
        _TOKEN_PATH.chmod(0o600)
    except OSError as e:
        logger.debug(f"设置 Web Chat MCP token 文件权限失败: {e}")
    return token


def is_valid_web_chat_mcp_token(token: str) -> bool:
    expected = get_web_chat_mcp_token()
    return bool(token) and compare_digest(token, expected)


def get_web_chat_mcp_auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {get_web_chat_mcp_token()}"}


def is_web_chat_mcp_entry(raw: Dict[str, Any]) -> bool:
    name_key = _normalize_web_chat_mcp_key(str(raw.get("name") or raw.get("id") or ""))
    url = str(raw.get("url") or "").rstrip("/")
    return (
        raw.get("id") == WEB_CHAT_MCP_SERVER_ID
        or name_key == _normalize_web_chat_mcp_key(WEB_CHAT_MCP_SERVER_NAME)
        or url.endswith("/api/mcp/web-chat/mcp")
    )


def build_web_chat_mcp_server_entry(*, auto_inject: bool = False) -> Dict[str, Any]:
    return {
        "id": WEB_CHAT_MCP_SERVER_ID,
        "name": WEB_CHAT_MCP_SERVER_NAME,
        "type": "http",
        "auto_inject": auto_inject,
        "url": WEB_CHAT_MCP_URL,
        "headers": get_web_chat_mcp_auth_headers(),
        "validation": {
            "status": "validated",
            "server_name": "nekro-web-chat",
        },
    }


def inject_web_chat_mcp_auth(raw: Dict[str, Any]) -> Dict[str, Any]:
    entry = dict(raw)
    if is_web_chat_mcp_entry(entry):
        entry["id"] = WEB_CHAT_MCP_SERVER_ID
        entry["type"] = "http"
        entry.setdefault("url", WEB_CHAT_MCP_URL)
        entry["headers"] = get_web_chat_mcp_auth_headers()
    return entry


def _read_token() -> str | None:
    if not _TOKEN_PATH.exists():
        return None
    try:
        data = json.loads(_TOKEN_PATH.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"读取 Web Chat MCP token 失败，将重新生成: {e}")
        return None
    token = data.get("token") if isinstance(data, dict) else None
    return token if isinstance(token, str) and token else None


def _normalize_web_chat_mcp_key(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())
