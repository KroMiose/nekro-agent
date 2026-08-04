"""内置 MCP 服务注册表 — 提供推荐预置 + 空白模板"""

from .schemas import McpEnvKeyDef, McpRegistryItem, McpServerType
from .web_chat_auth import (
    WEB_CHAT_MCP_SERVER_ID,
    WEB_CHAT_MCP_SERVER_NAME,
    WEB_CHAT_MCP_URL,
    get_web_chat_mcp_auth_headers,
)

BUILTIN_REGISTRY: list[McpRegistryItem] = [
    # ── 推荐预置 MCP server ──
    McpRegistryItem(
        id="github",
        name="GitHub",
        description="访问 GitHub 仓库、Issue、PR 等",
        icon="github",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env_keys=[
            McpEnvKeyDef(
                key="GITHUB_PERSONAL_ACCESS_TOKEN",
                description="GitHub Personal Access Token (具备所需 scope)",
                required=True,
            ),
        ],
        tags=["preset", "stdio", "git"],
    ),
    McpRegistryItem(
        id="fetch",
        name="Fetch",
        description="通用网页抓取与转 Markdown",
        icon="cloud",
        type=McpServerType.stdio,
        command="uvx",
        args=["mcp-server-fetch"],
        env_keys=[],
        tags=["preset", "stdio", "web"],
    ),
    McpRegistryItem(
        id="playwright",
        name="Playwright",
        description="基于 Playwright 的浏览器自动化",
        icon="browser",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-playwright"],
        env_keys=[],
        tags=["preset", "stdio", "browser"],
    ),
    McpRegistryItem(
        id="slack",
        name="Slack",
        description="读写 Slack 频道与消息",
        icon="chat",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-slack"],
        env_keys=[
            McpEnvKeyDef(
                key="SLACK_BOT_TOKEN",
                description="Slack Bot OAuth Token (xoxb-...)",
                required=True,
            ),
            McpEnvKeyDef(
                key="SLACK_TEAM_ID",
                description="Slack workspace / team ID",
                required=True,
            ),
        ],
        tags=["preset", "stdio", "chat"],
    ),
    McpRegistryItem(
        id=WEB_CHAT_MCP_SERVER_ID,
        name=WEB_CHAT_MCP_SERVER_NAME,
        description="通过 Nekro Agent Web Chat 创建测试会话、发送消息、等待回复并读取历史",
        icon="chat",
        type=McpServerType.http,
        url=WEB_CHAT_MCP_URL,
        headers={},
        env_keys=[],
        tags=["preset", "http", "chat", "test", "nekro"],
    ),
    McpRegistryItem(
        id="postgres",
        name="PostgreSQL",
        description="只读访问 PostgreSQL 数据库（schema 探查 + SQL 查询）",
        icon="database",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-postgres"],
        env_keys=[
            McpEnvKeyDef(
                key="DATABASE_URL",
                description="PostgreSQL 连接串，如 postgres://user:pwd@host:5432/db",
                required=True,
            ),
        ],
        tags=["preset", "stdio", "db"],
    ),
    # ── 空白传输类型模板（从零开始） ──
    McpRegistryItem(
        id="blank-stdio",
        name="自定义 stdio 服务",
        description="基于命令行进程通信的 MCP 服务（最常见类型）",
        icon="terminal",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "your-mcp-server-package"],
        env_keys=[],
        tags=["blank", "stdio"],
    ),
    McpRegistryItem(
        id="blank-sse",
        name="自定义 SSE 服务",
        description="基于 Server-Sent Events 的远程 MCP 服务",
        icon="cloud",
        type=McpServerType.sse,
        url="https://your-mcp-server.example.com/sse",
        env_keys=[],
        tags=["blank", "sse", "remote"],
    ),
    McpRegistryItem(
        id="blank-http",
        name="自定义 HTTP 服务",
        description="基于 Streamable HTTP 的远程 MCP 服务",
        icon="cloud",
        type=McpServerType.http,
        url="https://your-mcp-server.example.com/mcp",
        env_keys=[],
        tags=["blank", "http", "remote"],
    ),
]


def get_registry() -> list[McpRegistryItem]:
    """返回内置 MCP 服务注册表"""
    registry: list[McpRegistryItem] = []
    for item in BUILTIN_REGISTRY:
        copied = item.model_copy(deep=True)
        if copied.id == WEB_CHAT_MCP_SERVER_ID:
            copied.headers = get_web_chat_mcp_auth_headers()
        registry.append(copied)
    return registry
