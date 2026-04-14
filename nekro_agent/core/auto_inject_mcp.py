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
        _AUTO_INJECT_PATH.write_text(
            json.dumps({"servers": _DEFAULT_MCP_SERVERS}, indent=2),
            encoding="utf-8",
        )


def get_auto_inject_mcp_servers() -> List[Dict[str, Any]]:
    """Return the list of MCP server configs marked for auto-injection."""
    _ensure_file()
    try:
        data = json.loads(_AUTO_INJECT_PATH.read_text(encoding="utf-8"))
        return list(data.get("servers", []))
    except Exception as e:
        logger.warning(f"读取 auto-inject-mcp.json 失败: {e}")
        return []


def set_auto_inject_mcp_servers(servers: List[Dict[str, Any]]) -> None:
    """Overwrite the auto-inject MCP server list."""
    _ensure_file()
    _AUTO_INJECT_PATH.write_text(
        json.dumps({"servers": servers}, indent=2),
        encoding="utf-8",
    )
