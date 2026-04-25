from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ResourceFieldValueKind = Literal[
    "text",
    "password",
    "host",
    "port",
    "private_key",
    "username",
    "database",
    "json",
]
ResourceExportMode = Literal["env", "none"]


class ResourceField(BaseModel):
    field_key: str = ""
    label: str = Field(..., min_length=1, max_length=64)
    description: str = Field(default="", max_length=512)
    secret: bool = False
    value_kind: ResourceFieldValueKind = "text"
    order: int = 0
    export_mode: ResourceExportMode = "env"
    fixed_aliases: List[str] = Field(default_factory=list)
    value: str = ""


class ResourceTemplate(BaseModel):
    key: str
    name: str
    summary: str
    resource_note: str = ""
    resource_tags: List[str] = Field(default_factory=list)
    resource_prompt: str = ""
    fields: List[ResourceField] = Field(default_factory=list)


class WorkspaceResourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    template_key: Optional[str] = Field(default=None, max_length=64)
    resource_note: str = Field(default="", max_length=2000)
    resource_tags: List[str] = Field(default_factory=list)
    resource_prompt: str = Field(default="", max_length=4000)
    fields: List[ResourceField] = Field(default_factory=list)
    enabled: bool = True


class WorkspaceResourceCreate(WorkspaceResourceBase):
    pass


class WorkspaceResourceUpdate(WorkspaceResourceBase):
    pass


class BoundWorkspaceInfo(BaseModel):
    id: int
    name: str


class WorkspaceResourceSummary(BaseModel):
    id: int
    resource_key: str
    name: str
    template_key: Optional[str] = None
    resource_note: str = ""
    resource_tags: List[str] = Field(default_factory=list)
    resource_prompt: str = ""
    field_count: int = 0
    fixed_aliases: List[str] = Field(default_factory=list)
    enabled: bool = True
    bound_workspace_count: int = 0
    bound_workspaces: List[BoundWorkspaceInfo] = Field(default_factory=list)
    create_time: str
    update_time: str


class WorkspaceResourceDetail(WorkspaceResourceSummary):
    fields: List[ResourceField] = Field(default_factory=list)


class WorkspaceResourceListResponse(BaseModel):
    items: List[WorkspaceResourceSummary]


class WorkspaceResourceDetailResponse(BaseModel):
    item: WorkspaceResourceDetail


class WorkspaceResourceTemplatesResponse(BaseModel):
    items: List[ResourceTemplate]


class WorkspaceResourceBinding(BaseModel):
    binding_id: int
    resource_id: int
    enabled: bool = True
    sort_order: int = 0
    note: str = ""
    resource: WorkspaceResourceSummary


class WorkspaceResourceBindingsResponse(BaseModel):
    items: List[WorkspaceResourceBinding]


class WorkspaceResourceBindBody(BaseModel):
    note: str = Field(default="", max_length=256)


class WorkspaceResourceReorderItem(BaseModel):
    binding_id: int
    sort_order: int


class WorkspaceResourceReorderBody(BaseModel):
    items: List[WorkspaceResourceReorderItem]


class WorkspaceResourceCheckBindBody(BaseModel):
    resource_id: int


class WorkspaceResourceConflict(BaseModel):
    env_name: str
    existing_resource_id: int
    existing_resource_name: str
    target_resource_id: int
    target_resource_name: str


class WorkspaceResourceCheckBindResponse(BaseModel):
    ok: bool
    conflicts: List[WorkspaceResourceConflict] = Field(default_factory=list)


class ActionOkResponse(BaseModel):
    ok: bool = True
