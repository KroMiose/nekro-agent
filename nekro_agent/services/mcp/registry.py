"""内置 MCP 服务注册表 — 仅提供基础传输类型模板"""

from .schemas import McpRegistryItem, McpServerType

BUILTIN_REGISTRY: list[McpRegistryItem] = [
    McpRegistryItem(
        id="stdio-template",
        name="Stdio 服务",
        description="基于命令行进程通信的 MCP 服务（最常见类型）",
        icon="terminal",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "your-mcp-server-package"],
        env_keys=[],
        tags=["stdio"],
    ),
    McpRegistryItem(
        id="sse-template",
        name="SSE 服务",
        description="基于 Server-Sent Events 的远程 MCP 服务",
        icon="cloud",
        type=McpServerType.sse,
        url="https://your-mcp-server.example.com/sse",
        env_keys=[],
        tags=["sse", "remote"],
    ),
    McpRegistryItem(
        id="http-template",
        name="HTTP 服务",
        description="基于 Streamable HTTP 的远程 MCP 服务",
        icon="cloud",
        type=McpServerType.http,
        url="https://your-mcp-server.example.com/mcp",
        env_keys=[],
        tags=["http", "remote"],
    ),
]


def get_registry() -> list[McpRegistryItem]:
    """返回内置 MCP 服务注册表"""
    return BUILTIN_REGISTRY
