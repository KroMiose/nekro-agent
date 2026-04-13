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
    memory_system_enabled: bool
    sandbox_image: str
    sandbox_version: str
    container_name: Optional[str]
    host_port: Optional[int]
    runtime_policy: str
    create_time: str
    update_time: str
    # 聚合信息（列表页使用，无需额外请求）
    channel_count: int = 0
    channel_names: List[str] = []          # chat_key 列表（内部标识）
    channel_display_names: List[str] = []  # 频道显示名（channel_name 或 fallback 到 chat_key）
    skill_count: int = 0
    mcp_count: int = 0
    cc_model_preset_name: Optional[str] = None


class WorkspaceDetail(WorkspaceSummary):
    container_id: Optional[str]
    last_heartbeat: Optional[str]
    last_error: Optional[str]
    metadata: Dict[str, Any]
    cc_model_preset_id: Optional[int] = None
    primary_channel_chat_key: Optional[str] = None


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
    cc_version: Optional[str] = None
    claude_code_version: Optional[str] = None


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


class AutoInjectSkillsUpdate(BaseModel):
    skills: List[str]


class AutoInjectSkillsResponse(BaseModel):
    skills: List[str]


class AutoInjectMcpUpdate(BaseModel):
    servers: List[Dict[str, Any]]


class AutoInjectMcpResponse(BaseModel):
    servers: List[Dict[str, Any]]


# ── 沙盒通讯日志 ────────────────────────────────────────────────────────────


CommDirection = Literal["NA_TO_CC", "CC_TO_NA", "USER_TO_CC", "SYSTEM", "TOOL_CALL", "TOOL_RESULT", "CC_STATUS"]


class CommStatusPayload(BaseModel):
    running: bool
    started_at: Optional[int] = None


class WorkspaceCommQueueTask(BaseModel):
    task_id: Optional[str] = None
    source_chat_key: Optional[str] = None
    started_at: Optional[int] = None
    enqueued_at: Optional[int] = None


class WorkspaceCommQueueResponse(BaseModel):
    current_task: Optional[WorkspaceCommQueueTask] = None
    queued_tasks: List[WorkspaceCommQueueTask] = Field(default_factory=list)
    queue_length: int = 0


class CommLogEntry(BaseModel):
    id: int
    workspace_id: int
    direction: CommDirection
    source_chat_key: str
    content: str
    extra_data: str = ""
    is_streaming: bool
    task_id: Optional[str]
    create_time: str

    @classmethod
    def from_orm(cls, log: Any) -> "CommLogEntry":
        """从 DBWorkspaceCommLog ORM 实例构造 CommLogEntry。"""
        return cls(
            id=log.id,
            workspace_id=log.workspace_id,
            direction=log.direction,
            source_chat_key=log.source_chat_key,
            content=log.content,
            extra_data=log.extra_data or "",
            is_streaming=log.is_streaming,
            task_id=log.task_id,
            create_time=log.create_time.isoformat(),
        )


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


class ClaudeMdResponse(BaseModel):
    content: str
    extra: str


class ClaudeMdExtraUpdate(BaseModel):
    extra: str


class PromptLayerItem(BaseModel):
    key: str
    title: str
    target: Literal["cc", "na", "shared"]
    maintainer: Literal["manual", "cc", "na", "manual+cc", "manual+na"]
    content: str
    description: str = ""
    editable_by_cc: bool = False
    auto_inject: bool = True
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


class PromptComposerResponse(BaseModel):
    claude_md_content: str
    claude_md_extra: str
    na_context: PromptLayerItem
    shared_manual_rules: PromptLayerItem
    na_manual_rules: PromptLayerItem


class PromptLayerUpdate(BaseModel):
    content: str


# ── 频道注解 ─────────────────────────────────────────────────────────────────


class ChannelAnnotation(BaseModel):
    """单个频道在工作区中的注解（存储于 DBWorkspace.metadata.channel_annotations）。"""

    description: str = Field(default="", max_length=256, description="频道在本工作区中的用途说明")
    is_primary: bool = Field(default=False, description="是否为主频道")


class ChannelAnnotationUpdate(BaseModel):
    """更新单个频道注解的请求体。"""

    chat_key: str = Field(..., description="目标频道的全局唯一标识")
    description: str = Field(default="", max_length=256, description="频道在本工作区中的用途说明")
    is_primary: bool = Field(default=False, description="是否设为主频道（设置后自动清除其他频道的主频道标记）")


class BoundChannelInfo(BaseModel):
    """绑定频道的完整信息（含注解）。"""

    chat_key: str
    description: str = ""
    is_primary: bool = False


class BoundChannelsResponse(BaseModel):
    channels: List[BoundChannelInfo]
