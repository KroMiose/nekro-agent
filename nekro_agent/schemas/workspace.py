from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., max_length=64)
    description: str = Field(default="", max_length=512)
    runtime_policy: Literal["agent", "relaxed", "strict"] = "agent"


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = Field(default=None, max_length=512)
    sandbox_image: Optional[str] = None
    sandbox_version: Optional[str] = None
    runtime_policy: Optional[Literal["agent", "relaxed", "strict"]] = None


class WorkspaceSummary(BaseModel):
    id: int
    name: str
    description: str
    status: str
    sandbox_image: str
    sandbox_version: str
    container_name: Optional[str]
    host_port: Optional[int]
    runtime_policy: str
    create_time: str
    update_time: str


class WorkspaceDetail(WorkspaceSummary):
    container_id: Optional[str]
    last_heartbeat: Optional[str]
    last_error: Optional[str]
    metadata: Dict[str, Any]
    cc_model_preset_id: Optional[int] = None


class WorkspaceListResponse(BaseModel):
    total: int
    items: List[WorkspaceSummary]


class SandboxStatus(BaseModel):
    workspace_id: int
    status: str
    container_name: Optional[str]
    container_id: Optional[str]
    host_port: Optional[int]
    session_id: Optional[str] = None
    tools: Optional[List[str]] = None


class ToolsResponse(BaseModel):
    tools: List[str]


class ChannelBindRequest(BaseModel):
    chat_key: str


class SkillItem(BaseModel):
    name: str
    description: str
    docs: List[str] = []  # 附属文档文件名列表，如 ["install.md"]


class WorkspaceSkillsUpdate(BaseModel):
    skills: List[str]


# ── 沙盒通讯日志 ────────────────────────────────────────────────────────────


class CommLogEntry(BaseModel):
    id: int
    workspace_id: int
    direction: str  # NA_TO_CC | CC_TO_NA | USER_TO_CC | SYSTEM
    source_chat_key: str
    content: str
    is_streaming: bool
    task_id: Optional[str]
    create_time: str


class CommHistoryResponse(BaseModel):
    total: int
    items: List[CommLogEntry]


class CommSendBody(BaseModel):
    content: str = Field(..., min_length=1, description="发送给 CC 的指令内容")


# ── 环境变量 ────────────────────────────────────────────────────────────────


class WorkspaceEnvVar(BaseModel):
    key: str = Field(..., min_length=1, max_length=256, description="环境变量名称（大写字母+下划线）")
    value: str = Field(default="", description="环境变量值")
    description: str = Field(default="", max_length=512, description="用途说明（注入 CLAUDE.md）")


class WorkspaceEnvVarsResponse(BaseModel):
    env_vars: List[WorkspaceEnvVar]


class WorkspaceEnvVarsUpdate(BaseModel):
    env_vars: List[WorkspaceEnvVar]
