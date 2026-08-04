"""Manage the list of MCP servers to auto-inject when creating a new workspace."""

import json
from pathlib import Path
from typing import Any, Dict, List

from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv

_AUTO_INJECT_PATH = Path(OsEnv.DATA_DIR) / "configs" / "auto-inject-mcp.json"

# 默认为空列表 — 不预设任何 MCP 服务
_DEFAULT_MCP_SERVERS: List[Dict[str, Any]] = []


def _ensure_file() -> None:
    _AUTO_INJECT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _AUTO_INJECT_PATH.exists():
        from nekro_agent.services.mcp.web_chat_auth import build_web_chat_mcp_server_entry

        _AUTO_INJECT_PATH.write_text(
            json.dumps({"servers": [*_DEFAULT_MCP_SERVERS, build_web_chat_mcp_server_entry()]}, indent=2),
            encoding="utf-8",
        )


def get_auto_inject_mcp_servers() -> List[Dict[str, Any]]:
    """Return the list of MCP server configs marked for auto-injection."""
    _ensure_file()
    try:
        data = json.loads(_AUTO_INJECT_PATH.read_text(encoding="utf-8"))
        servers = list(data.get("servers", []))
        return _normalize_builtin_web_chat_mcp(servers)
    except Exception as e:
        logger.warning(f"读取 auto-inject-mcp.json 失败: {e}")
        return []


def set_auto_inject_mcp_servers(servers: List[Dict[str, Any]]) -> None:
    """Overwrite the auto-inject MCP server list."""
    _ensure_file()
    servers = _normalize_builtin_web_chat_mcp(servers, persist=False)
    _AUTO_INJECT_PATH.write_text(
        json.dumps({"servers": servers}, indent=2),
        encoding="utf-8",
    )


def update_auto_inject_validation(name: str, validation_state: Dict[str, Any]) -> bool:
    """更新自动注入清单中某个 server 的 validation 字段。

    返回 True 表示找到并更新成功，False 表示该 name 不在清单内。
    """
    servers = get_auto_inject_mcp_servers()
    found = False
    for entry in servers:
        if (entry or {}).get("name") == name:
            entry["validation"] = validation_state
            found = True
            break
    if found:
        set_auto_inject_mcp_servers(servers)
    return found


def _normalize_builtin_web_chat_mcp(servers: List[Dict[str, Any]], *, persist: bool = True) -> List[Dict[str, Any]]:
    """合并 Web Chat MCP 历史变体并注入专用 token。

    只在配置文件首次创建时种默认项；后续如果用户删除该条目，这里不会再强制补回。
    """
    from nekro_agent.services.mcp.web_chat_auth import (
        build_web_chat_mcp_server_entry,
        inject_web_chat_mcp_auth,
        is_web_chat_mcp_entry,
    )

    normalized: List[Dict[str, Any]] = []
    web_chat_entries: List[Dict[str, Any]] = []
    mutated = False
    for raw in servers:
        if not isinstance(raw, dict):
            continue
        if is_web_chat_mcp_entry(raw):
            web_chat_entries.append(raw)
            continue
        normalized.append(raw)

    if web_chat_entries:
        auto_inject = any(bool(entry.get("auto_inject", entry.get("enabled", False))) for entry in web_chat_entries)
        selected = (
            next((entry for entry in web_chat_entries if entry.get("id")), None)
            or next((entry for entry in web_chat_entries if isinstance(entry.get("validation"), dict)), None)
            or web_chat_entries[-1]
        )
        canonical = {
            **build_web_chat_mcp_server_entry(auto_inject=auto_inject),
            **selected,
            "auto_inject": auto_inject,
        }
        first_with_validation = next(
            (entry for entry in web_chat_entries if isinstance(entry.get("validation"), dict)),
            None,
        )
        if first_with_validation:
            canonical["validation"] = first_with_validation["validation"]
        canonical = inject_web_chat_mcp_auth(canonical)
        normalized.append(canonical)
        mutated = len(web_chat_entries) > 1 or any(inject_web_chat_mcp_auth(entry) != canonical for entry in web_chat_entries)

    if persist and mutated:
        _AUTO_INJECT_PATH.write_text(
            json.dumps({"servers": normalized}, indent=2),
            encoding="utf-8",
        )
    return normalized
