"""内置 MCP 服务注册表"""

from .schemas import McpEnvKeyDef, McpRegistryItem, McpServerType

BUILTIN_REGISTRY: list[McpRegistryItem] = [
    McpRegistryItem(
        id="github",
        name="GitHub",
        description="GitHub API 集成 — 仓库管理、Issue、PR、搜索等",
        icon="github",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env_keys=[
            McpEnvKeyDef(
                key="GITHUB_PERSONAL_ACCESS_TOKEN",
                description="GitHub Personal Access Token",
                required=True,
            ),
        ],
        tags=["dev", "git"],
    ),
    McpRegistryItem(
        id="filesystem",
        name="Filesystem",
        description="本地文件系统读写 — 受限于指定目录",
        icon="folder",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
        env_keys=[],
        tags=["filesystem"],
    ),
    McpRegistryItem(
        id="fetch",
        name="Fetch",
        description="HTTP 请求与网页抓取 — 访问网页内容和 API",
        icon="cloud",
        type=McpServerType.stdio,
        command="uvx",
        args=["mcp-server-fetch"],
        env_keys=[],
        tags=["web", "http"],
    ),
    McpRegistryItem(
        id="brave-search",
        name="Brave Search",
        description="Brave 搜索引擎 — 网页搜索和本地搜索",
        icon="search",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
        env_keys=[
            McpEnvKeyDef(
                key="BRAVE_API_KEY",
                description="Brave Search API Key",
                required=True,
            ),
        ],
        tags=["search", "web"],
    ),
    McpRegistryItem(
        id="memory",
        name="Memory",
        description="持久化记忆系统 — 基于知识图谱的长期记忆存储",
        icon="memory",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
        env_keys=[],
        tags=["memory", "knowledge"],
    ),
    McpRegistryItem(
        id="postgres",
        name="PostgreSQL",
        description="PostgreSQL 数据库 — 只读 SQL 查询和表结构分析",
        icon="database",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-postgres", "postgresql://user:pass@localhost:5432/dbname"],
        env_keys=[],
        tags=["database", "sql"],
    ),
    McpRegistryItem(
        id="sequential-thinking",
        name="Sequential Thinking",
        description="顺序思考工具 — 帮助 AI 进行结构化的逐步推理",
        icon="brain",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "@modelcontextprotocol/server-sequential-thinking"],
        env_keys=[],
        tags=["reasoning", "thinking"],
    ),
    McpRegistryItem(
        id="open-websearch",
        name="Open WebSearch",
        description="开源网页搜索 — 基于搜索引擎的网页检索与提取",
        icon="search",
        type=McpServerType.stdio,
        command="npx",
        args=["-y", "open-websearch-mcp@latest"],
        env_keys=[],
        tags=["search", "web"],
    ),
]


def get_registry() -> list[McpRegistryItem]:
    """返回内置 MCP 服务注册表"""
    return BUILTIN_REGISTRY
