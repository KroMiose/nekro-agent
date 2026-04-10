from typing import Literal, Optional

from pydantic import BaseModel, Field

KBFormat = Literal["markdown", "text", "html", "json", "yaml", "csv", "xlsx", "pdf", "docx"]
KBStatus = Literal["pending", "extracting", "indexing", "ready", "failed"]


class KBActionResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None


class KBTagUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list)


class KBCreateTextDocumentBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    source_path: str = Field(default="", description="相对 kb/files 的目标路径，可为空")
    file_name: str = Field(default="", description="可选文件名，未提供时按 title 生成")
    format: Literal["markdown", "text"] = "markdown"
    category: str = Field(default="", max_length=64)
    tags: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=1000)
    is_enabled: bool = True


class KBUpdateDocumentBody(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, max_length=64)
    tags: Optional[list[str]] = None
    summary: Optional[str] = Field(default=None, max_length=1000)
    is_enabled: Optional[bool] = None
    source_path: Optional[str] = Field(default=None, description="更新目标相对路径")
    content: Optional[str] = Field(default=None, description="仅文本类文档可更新源内容")


class KBDocumentListItem(BaseModel):
    id: int
    workspace_id: int
    title: str
    category: str
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    file_name: str
    file_ext: str
    mime_type: str
    format: KBFormat
    source_path: str
    source_workspace_path: str
    normalized_text_path: Optional[str] = None
    normalized_workspace_path: Optional[str] = None
    is_enabled: bool
    extract_status: KBStatus
    sync_status: KBStatus
    chunk_count: int
    file_size: int
    last_error: Optional[str] = None
    last_indexed_at: Optional[str] = None
    update_time: str
    create_time: str


class KBDocumentListResponse(BaseModel):
    total: int
    items: list[KBDocumentListItem] = Field(default_factory=list)


class KBTreeNode(BaseModel):
    name: str
    path: str
    type: Literal["dir", "file"]
    document_id: Optional[int] = None
    children: Optional[list["KBTreeNode"]] = None


KBTreeNode.model_rebuild()


class KBTreeResponse(BaseModel):
    nodes: list[KBTreeNode] = Field(default_factory=list)


class KBDocumentDetailResponse(BaseModel):
    document: KBDocumentListItem
    source_content: Optional[str] = None
    normalized_content: Optional[str] = None


class KBFullTextResponse(BaseModel):
    document_id: int
    title: str
    source_path: str
    source_workspace_path: str
    normalized_text_path: Optional[str] = None
    normalized_workspace_path: Optional[str] = None
    content: str
    truncated: bool = False


class KBChunkContextResponse(BaseModel):
    document_id: int
    chunk_id: int
    title: str
    source_path: str
    source_workspace_path: str
    normalized_text_path: Optional[str] = None
    normalized_workspace_path: Optional[str] = None
    heading_path: str = ""
    chunk_char_start: int
    chunk_char_end: int
    window_start: int
    window_size: int
    excerpt_char_start: int
    excerpt_char_end: int
    before_truncated: bool = False
    after_truncated: bool = False
    includes_hit: bool = True
    prev_window_start: Optional[int] = None
    next_window_start: Optional[int] = None
    match_text: str
    annotated_excerpt: str


class KBSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    max_chunks_per_document: int = Field(default=2, ge=1, le=10)
    category: str = ""
    tags: list[str] = Field(default_factory=list)


class KBSearchItem(BaseModel):
    document_id: int
    chunk_id: int
    title: str
    file_name: str
    format: KBFormat
    source_path: str
    source_workspace_path: str
    normalized_text_path: Optional[str] = None
    normalized_workspace_path: Optional[str] = None
    heading_path: str = ""
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    content_preview: str
    score: float


class KBSearchSnippet(BaseModel):
    chunk_id: int
    heading_path: str = ""
    content_preview: str
    score: float


class KBSearchDocument(BaseModel):
    document_id: int
    title: str
    file_name: str
    format: KBFormat
    source_path: str
    source_workspace_path: str
    normalized_text_path: Optional[str] = None
    normalized_workspace_path: Optional[str] = None
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    document_score: float
    matched_chunk_count: int
    headings: list[str] = Field(default_factory=list)
    best_match_excerpt: str = ""
    snippets: list[KBSearchSnippet] = Field(default_factory=list)


class KBSearchResponse(BaseModel):
    workspace_id: int
    query: str
    total: int
    items: list[KBSearchItem] = Field(default_factory=list)
    document_total: int = 0
    documents: list[KBSearchDocument] = Field(default_factory=list)
    suggested_document_ids: list[int] = Field(default_factory=list)
    next_action_hint: str = ""


class KBReindexResponse(BaseModel):
    ok: bool = True
    total: int = 0
    success: int = 0
    failed: int = 0


class KBSourceFileResponse(BaseModel):
    document_id: int
    title: str
    source_path: str
    source_workspace_path: str
    sandbox_file_path: Optional[str] = None
