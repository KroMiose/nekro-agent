"""MCP 服务结构化配置模型"""

from __future__ import annotations

import re
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator, model_validator


class McpServerType(str, Enum):
    """MCP 服务器传输类型"""

    stdio = "stdio"  # command + args
    sse = "sse"  # url (SSE)
    http = "http"  # url (StreamableHTTP)


STDIO_COMMAND_ALLOWLIST: frozenset[str] = frozenset({"npx", "uvx"})
"""允许出现在 stdio 类型 `command` 字段中的可执行白名单。

仅保留 CC 沙盒镜像 (`kromiose/nekro-cc-sandbox`) 内已预装的命令：
- `npx` — 随 Node.js 20.x 提供
- `uvx` — 随 astral-sh/uv 提供

bunx (无 bun) 与 pnpx (runtime 未启用 corepack) 在沙盒内不可用，因此排除。
前端守门与服务端校验共用此常量。
"""

_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class McpEnvKeyDef(BaseModel):
    """注册表模板中需要用户填写的环境变量定义"""

    key: str
    description: str
    required: bool = True


class McpServerConfig(BaseModel):
    """单个 MCP 服务器的结构化配置"""

    model_config = ConfigDict(use_enum_values=False)

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
    # 验证状态（只读，由后端写入；前端编辑提交时被忽略）
    validation: Optional["McpValidationState"] = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        if not _NAME_PATTERN.match(value or ""):
            raise ValueError("服务器名称须为 1-64 位字母/数字/下划线/短横线")
        return value

    @model_validator(mode="after")
    def _validate_transport_fields(self) -> "McpServerConfig":
        if self.type == McpServerType.stdio:
            command = (self.command or "").strip()
            if not command:
                raise ValueError("stdio 类型必须填写 command")
            if command not in STDIO_COMMAND_ALLOWLIST:
                raise ValueError(
                    f"stdio command 必须在白名单内 ({sorted(STDIO_COMMAND_ALLOWLIST)})",
                )
        else:
            if not (self.url or "").strip():
                raise ValueError(f"{self.type.value} 类型必须填写 url")
            try:
                HttpUrl(self.url)  # type: ignore[arg-type]
            except Exception as e:  # noqa: BLE001
                raise ValueError(f"url 格式无效: {e}") from e
        return self


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


class McpConstraints(BaseModel):
    """暴露给前端的 MCP 配置约束（避免规则两边硬编码）"""

    stdio_command_allowlist: List[str]
    name_pattern: str


class McpValidationState(BaseModel):
    """MCP 服务器的持久化验证状态

    每次成功握手会刷新 status='validated' + validated_at；失败会写 status='failed'
    + last_error。配置发生任何修改时由后端重置为 'unvalidated'，确保 .mcp.json 只
    写入"真实通过过校验的"服务器。
    """

    status: Literal["validated", "unvalidated", "failed"] = "unvalidated"
    validated_at: Optional[str] = None  # ISO 8601 UTC
    server_name: Optional[str] = None
    server_version: Optional[str] = None
    tools_count: Optional[int] = None
    latency_ms: Optional[float] = None
    last_error: Optional[str] = None
    last_error_kind: Optional[str] = None


McpServerConfig.model_rebuild()
