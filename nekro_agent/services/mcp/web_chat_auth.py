"""Web Chat MCP 专用鉴权与内置配置。"""

from __future__ import annotations

import hashlib
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

_EXTERNAL_TOKEN_PATH = Path(OsEnv.DATA_DIR) / "configs" / "web-chat-mcp-external-token.json"
_MIN_EXTERNAL_TOKEN_LENGTH = 16
_INTERNAL_TOKEN = secrets.token_urlsafe(48)


def get_internal_web_chat_mcp_token() -> str:
    """获取当前进程内置 Web Chat MCP token。"""
    return _INTERNAL_TOKEN


def rotate_internal_web_chat_mcp_token() -> str:
    """轮换当前进程内置 token，供启动流程刷新沙盒 MCP 配置。"""
    global _INTERNAL_TOKEN
    _INTERNAL_TOKEN = secrets.token_urlsafe(48)
    return _INTERNAL_TOKEN


def is_valid_web_chat_mcp_token(token: str) -> bool:
    """校验 Web Chat MCP token，内置 token 或已启用外接 token 任一匹配即可。"""
    if not token:
        return False
    if compare_digest(token, get_internal_web_chat_mcp_token()):
        return True
    return is_valid_external_web_chat_mcp_token(token)


def get_web_chat_mcp_auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {get_internal_web_chat_mcp_token()}"}


def generate_external_web_chat_mcp_token() -> tuple[str, Dict[str, Any]]:
    """生成并启用用户外接固定 token，仅调用方可拿到一次明文。"""
    token = secrets.token_urlsafe(48)
    status = save_external_web_chat_mcp_token(enabled=True, token=token)
    return token, status


def save_external_web_chat_mcp_token(*, enabled: bool, token: str | None = None) -> Dict[str, Any]:
    """保存用户外接 token 状态。token 为空时只切换启用状态，不覆盖既有密钥。"""
    state = _read_external_token_state()
    normalized_token = token.strip() if token is not None else ""
    if normalized_token:
        _validate_external_token(normalized_token)
        state["token_hash"] = _hash_token(normalized_token)
        state["token_preview"] = _preview_token(normalized_token)
        state["updated_at"] = _utc_now()

    if enabled and not state.get("token_hash"):
        raise ValueError("启用外接密钥前需要先设置密钥")

    state["enabled"] = enabled
    if not state.get("updated_at"):
        state["updated_at"] = _utc_now()
    _write_external_token_state(state)
    return get_external_web_chat_mcp_status()


def clear_external_web_chat_mcp_token() -> Dict[str, Any]:
    """关闭并清除用户外接 token。"""
    state: Dict[str, Any] = {
        "enabled": False,
        "token_hash": None,
        "token_preview": None,
        "updated_at": _utc_now(),
    }
    _write_external_token_state(state)
    return get_external_web_chat_mcp_status()


def get_external_web_chat_mcp_status() -> Dict[str, Any]:
    state = _read_external_token_state()
    return {
        "enabled": bool(state.get("enabled")) and bool(state.get("token_hash")),
        "configured": bool(state.get("token_hash")),
        "token_preview": state.get("token_preview") if state.get("token_hash") else None,
        "updated_at": state.get("updated_at") if state.get("token_hash") or state.get("updated_at") else None,
    }


def is_valid_external_web_chat_mcp_token(token: str) -> bool:
    state = _read_external_token_state()
    if not state.get("enabled") or not state.get("token_hash"):
        return False
    return compare_digest(_hash_token(token), str(state["token_hash"]))


def refresh_web_chat_mcp_runtime_auth() -> list[str]:
    """把全局 MCP 库里的内置 Web Chat 条目刷新为当前运行期 token，并返回需刷新 workspace 的条目名。"""
    from nekro_agent.core.auto_inject_mcp import get_auto_inject_mcp_servers, set_auto_inject_mcp_servers

    refreshed: list[Dict[str, Any]] = []
    referenced_names = [WEB_CHAT_MCP_SERVER_NAME]
    for raw in get_auto_inject_mcp_servers():
        if isinstance(raw, dict) and is_web_chat_mcp_entry(raw):
            name = raw.get("name")
            if isinstance(name, str) and name and name not in referenced_names:
                referenced_names.append(name)
            refreshed.append(inject_web_chat_mcp_auth(raw))
        elif isinstance(raw, dict):
            refreshed.append(raw)
    set_auto_inject_mcp_servers(refreshed)
    return referenced_names


async def init_web_chat_mcp_runtime_auth() -> None:
    """启动时轮换内置 token，并同步全局库和已引用 workspace 的 MCP 配置。"""
    try:
        from nekro_agent.services.workspace.manager import WorkspaceService

        rotate_internal_web_chat_mcp_token()
        referenced_names = refresh_web_chat_mcp_runtime_auth()
        for name in referenced_names:
            await WorkspaceService.refresh_global_mcp_server_references(name)
        logger.info("Web Chat MCP runtime token refreshed")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"刷新 Web Chat MCP 运行期密钥失败（非致命）: {e}")


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
    return get_internal_web_chat_mcp_token()


def _read_external_token_state() -> Dict[str, Any]:
    if not _EXTERNAL_TOKEN_PATH.exists():
        return _empty_external_token_state()
    try:
        data = json.loads(_EXTERNAL_TOKEN_PATH.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"读取 Web Chat MCP 外接密钥状态失败，将按未配置处理: {e}")
        return _empty_external_token_state()
    if not isinstance(data, dict):
        return _empty_external_token_state()
    return {
        "enabled": bool(data.get("enabled")),
        "token_hash": data.get("token_hash") if isinstance(data.get("token_hash"), str) else None,
        "token_preview": data.get("token_preview") if isinstance(data.get("token_preview"), str) else None,
        "updated_at": data.get("updated_at") if isinstance(data.get("updated_at"), str) else None,
    }


def _write_external_token_state(state: Dict[str, Any]) -> None:
    _EXTERNAL_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    _EXTERNAL_TOKEN_PATH.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    try:
        _EXTERNAL_TOKEN_PATH.chmod(0o600)
    except OSError as e:
        logger.debug(f"设置 Web Chat MCP 外接密钥文件权限失败: {e}")


def _empty_external_token_state() -> Dict[str, Any]:
    return {
        "enabled": False,
        "token_hash": None,
        "token_preview": None,
        "updated_at": None,
    }


def _validate_external_token(token: str) -> None:
    if len(token) < _MIN_EXTERNAL_TOKEN_LENGTH:
        raise ValueError(f"外接密钥长度不能少于 {_MIN_EXTERNAL_TOKEN_LENGTH} 个字符")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _preview_token(token: str) -> str:
    if len(token) <= 12:
        return f"{token[:2]}...{token[-2:]}"
    return f"{token[:6]}...{token[-6:]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_web_chat_mcp_key(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())
