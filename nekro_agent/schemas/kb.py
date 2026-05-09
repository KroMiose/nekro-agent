from typing import Literal, Optional

from pydantic import BaseModel, Field

KBFormat = Literal["markdown", "text", "html", "json", "yaml", "csv", "xlsx", "pdf", "docx"]
KBStatus = Literal["pending", "extracting", "indexing", "ready", "failed"]
KBSearchSourceKind = Literal["document", "asset"]


class KBActionResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None


class KBTagUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list)


class KBCreateTextDocumentBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    source_path: str = Field(default="", description="可选目标相对路径；未提供时按分类自动生成")
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


class KBUpdateAssetBody(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[str] = Field(default=None, max_length=64)
    tags: Optional[list[str]] = None
    summary: Optional[str] = Field(default=None, max_length=1000)
    is_enabled: Optional[bool] = None


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
    source_workspace_path: Optional[str] = None
    normalized_text_path: Optional[str] = None
    normalized_workspace_path: Optional[str] = None
    content: str
    truncated: bool = False


class KBChunkContextResponse(BaseModel):
    document_id: int
    chunk_id: int
    title: str
    source_path: str
    source_workspace_path: Optional[str] = None
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
    source_kind: KBSearchSourceKind = "document"
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
    source_kind: KBSearchSourceKind = "document"
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
    referenced_sources: list["KBReferencedSource"] = Field(
        default_factory=list,
        description="该条目引用的其他文档/资产，可据此进一步获取补充内容",
    )


class KBSearchResponse(BaseModel):
    workspace_id: int
    query: str
    total: int
    items: list[KBSearchItem] = Field(default_factory=list)
    document_total: int = 0
    documents: list[KBSearchDocument] = Field(default_factory=list)
    suggested_document_ids: list[int] = Field(default_factory=list)
    next_action_hint: str = ""
    reference_expanded_items: list[KBSearchItem] = Field(
        default_factory=list,
        description="命中文档所引用的其他文档中抽取的补充 chunk，source_kind 与原文档一致",
    )


class KBReindexResponse(BaseModel):
    ok: bool = True
    total: int = 0
    success: int = 0
    failed: int = 0


class KBSourceFileResponse(BaseModel):
    document_id: int
    title: str
    source_path: str
    source_workspace_path: Optional[str] = None
    sandbox_file_path: Optional[str] = None


class KBReferencedSource(BaseModel):
    source_kind: KBSearchSourceKind
    document_id: int


KBSearchDocument.model_rebuild()


class KBAssetBoundWorkspace(BaseModel):
    workspace_id: int
    workspace_name: str
    workspace_status: str


class KBAssetListItem(BaseModel):
    id: int
    title: str
    category: str
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    file_name: str
    file_ext: str
    mime_type: str
    format: KBFormat
    source_path: str
    is_enabled: bool
    extract_status: KBStatus
    sync_status: KBStatus
    chunk_count: int
    file_size: int
    last_error: Optional[str] = None
    last_indexed_at: Optional[str] = None
    binding_count: int = 0
    bound_workspaces: list[KBAssetBoundWorkspace] = Field(default_factory=list)
    update_time: str
    create_time: str


class KBAssetListResponse(BaseModel):
    total: int
    items: list[KBAssetListItem] = Field(default_factory=list)


class KBAssetDetailResponse(BaseModel):
    asset: KBAssetListItem
    source_content: Optional[str] = None
    normalized_content: Optional[str] = None


class KBAssetUploadResponse(BaseModel):
    asset: KBAssetListItem
    reused_existing: bool = False


class KBAssetBindingsUpdateBody(BaseModel):
    workspace_ids: list[int] = Field(default_factory=list)


class KBAssetBindingsResponse(BaseModel):
    asset_id: int
    binding_count: int = 0
    items: list[KBAssetBoundWorkspace] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 文档/资产引用关系
# ---------------------------------------------------------------------------


class KBReferenceItem(BaseModel):
    """单条引用关系（用于展示列表）。"""

    ref_id: int
    document_id: int
    title: str
    category: str
    format: KBFormat
    summary: str = ""
    description: str = ""
    is_auto: bool = False


class KBDocumentReferences(BaseModel):
    """文档的双向引用列表。"""

    references_to: list[KBReferenceItem] = Field(default_factory=list, description="该文档引用了哪些文档")
    referenced_by: list[KBReferenceItem] = Field(default_factory=list, description="哪些文档引用了该文档")


class KBAssetReferences(BaseModel):
    """资产的双向引用列表。"""

    references_to: list[KBReferenceItem] = Field(default_factory=list, description="该资产引用了哪些资产")
    referenced_by: list[KBReferenceItem] = Field(default_factory=list, description="哪些资产引用了该资产")


class KBAddReferenceBody(BaseModel):
    target_id: int = Field(..., description="被引用的文档/资产 ID")
    description: str = Field(default="", max_length=500, description="引用说明")


class KBUpdateReferenceBody(BaseModel):
    description: str = Field(..., max_length=500, description="更新后的引用说明")
