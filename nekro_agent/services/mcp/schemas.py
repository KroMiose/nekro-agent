"""MCP 服务结构化配置模型"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class McpServerType(str, Enum):
    """MCP 服务器传输类型"""

    stdio = "stdio"  # command + args
    sse = "sse"  # url (SSE)
    http = "http"  # url (StreamableHTTP)


class McpEnvKeyDef(BaseModel):
    """注册表模板中需要用户填写的环境变量定义"""

    key: str
    description: str
    required: bool = True


class McpServerConfig(BaseModel):
    """单个 MCP 服务器的结构化配置"""

    name: str  # 服务器名称（唯一标识）
    type: McpServerType  # 传输类型
    enabled: bool = True  # 是否启用
    # stdio 类型
    command: Optional[str] = None  # 命令
    args: List[str] = []  # 参数
    env: Dict[str, str] = {}  # 环境变量
    # sse/http 类型
    url: Optional[str] = None  # 远程 URL
    headers: Dict[str, str] = {}  # HTTP 头


class McpRegistryItem(BaseModel):
    """注册表中的 MCP 服务模板"""

    id: str  # 模板 ID (e.g. "github", "fetch")
    name: str  # 显示名称
    description: str  # 描述
    icon: Optional[str] = None  # 图标标识
    type: McpServerType
    command: Optional[str] = None
    args: List[str] = []
    env_keys: List[McpEnvKeyDef] = []  # 需要用户填写的 env key 定义
    url: Optional[str] = None
    tags: List[str] = []  # 标签分类
