from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "kb_chunk" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "document_id" INT NOT NULL,
    "chunk_index" INT NOT NULL,
    "heading_path" VARCHAR(512) NOT NULL DEFAULT '',
    "content" TEXT NOT NULL,
    "content_preview" VARCHAR(512) NOT NULL DEFAULT '',
    "char_start" INT NOT NULL DEFAULT 0,
    "char_end" INT NOT NULL DEFAULT 0,
    "token_count" INT NOT NULL DEFAULT 0,
    "embedding_ref" VARCHAR(64),
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_kb_chunk_documen_07a833" UNIQUE ("document_id", "chunk_index")
);
CREATE INDEX IF NOT EXISTS "idx_kb_chunk_workspa_d9265f" ON "kb_chunk" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_kb_chunk_documen_cba701" ON "kb_chunk" ("document_id");
CREATE INDEX IF NOT EXISTS "idx_kb_chunk_embeddi_e19de2" ON "kb_chunk" ("embedding_ref");
CREATE INDEX IF NOT EXISTS "idx_kb_chunk_workspa_81db67" ON "kb_chunk" ("workspace_id", "document_id");
CREATE INDEX IF NOT EXISTS "idx_kb_chunk_workspa_c0e439" ON "kb_chunk" ("workspace_id", "chunk_index");
COMMENT ON COLUMN "kb_chunk"."id" IS 'Chunk ID';
COMMENT ON COLUMN "kb_chunk"."workspace_id" IS '工作区 ID';
COMMENT ON COLUMN "kb_chunk"."document_id" IS '所属文档 ID';
COMMENT ON COLUMN "kb_chunk"."chunk_index" IS '文档内顺序';
COMMENT ON COLUMN "kb_chunk"."heading_path" IS '标题层级路径';
COMMENT ON COLUMN "kb_chunk"."content" IS 'Chunk 内容';
COMMENT ON COLUMN "kb_chunk"."content_preview" IS 'Chunk 预览';
COMMENT ON COLUMN "kb_chunk"."char_start" IS '字符起始偏移';
COMMENT ON COLUMN "kb_chunk"."char_end" IS '字符结束偏移';
COMMENT ON COLUMN "kb_chunk"."token_count" IS '估算 token 数';
COMMENT ON COLUMN "kb_chunk"."embedding_ref" IS 'Qdrant 向量 ID';
COMMENT ON COLUMN "kb_chunk"."create_time" IS '创建时间';
COMMENT ON COLUMN "kb_chunk"."update_time" IS '更新时间';
COMMENT ON TABLE "kb_chunk" IS '知识库索引切块。';
        CREATE TABLE IF NOT EXISTS "kb_document" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "source_path" VARCHAR(512) NOT NULL,
    "normalized_text_path" VARCHAR(256),
    "file_name" VARCHAR(256) NOT NULL,
    "file_ext" VARCHAR(32) NOT NULL,
    "mime_type" VARCHAR(128) NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "category" VARCHAR(64) NOT NULL DEFAULT '',
    "tags" JSONB NOT NULL,
    "summary" TEXT NOT NULL,
    "source_type" VARCHAR(32) NOT NULL DEFAULT 'manual',
    "format" VARCHAR(32) NOT NULL,
    "is_enabled" BOOL NOT NULL DEFAULT True,
    "extract_status" VARCHAR(32) NOT NULL DEFAULT 'pending',
    "sync_status" VARCHAR(32) NOT NULL DEFAULT 'pending',
    "content_hash" VARCHAR(64) NOT NULL DEFAULT '',
    "normalized_text_hash" VARCHAR(64) NOT NULL DEFAULT '',
    "chunk_count" INT NOT NULL DEFAULT 0,
    "file_size" BIGINT NOT NULL DEFAULT 0,
    "last_indexed_at" TIMESTAMPTZ,
    "last_error" TEXT,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_kb_document_workspa_714c89" UNIQUE ("workspace_id", "source_path")
);
CREATE INDEX IF NOT EXISTS "idx_kb_document_workspa_1f20df" ON "kb_document" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_kb_document_is_enab_f54e07" ON "kb_document" ("is_enabled");
CREATE INDEX IF NOT EXISTS "idx_kb_document_workspa_4b5732" ON "kb_document" ("workspace_id", "is_enabled");
CREATE INDEX IF NOT EXISTS "idx_kb_document_workspa_2d9e02" ON "kb_document" ("workspace_id", "category");
CREATE INDEX IF NOT EXISTS "idx_kb_document_workspa_e10772" ON "kb_document" ("workspace_id", "format");
CREATE INDEX IF NOT EXISTS "idx_kb_document_workspa_c2101d" ON "kb_document" ("workspace_id", "sync_status");
COMMENT ON COLUMN "kb_document"."id" IS '文档 ID';
COMMENT ON COLUMN "kb_document"."workspace_id" IS '工作区 ID';
COMMENT ON COLUMN "kb_document"."source_path" IS '相对 kb/files 根目录的源文件路径';
COMMENT ON COLUMN "kb_document"."normalized_text_path" IS '相对 kb/.normalized 根目录的规范化全文路径';
COMMENT ON COLUMN "kb_document"."file_name" IS '原始文件名';
COMMENT ON COLUMN "kb_document"."file_ext" IS '文件扩展名';
COMMENT ON COLUMN "kb_document"."mime_type" IS '文件 MIME 类型';
COMMENT ON COLUMN "kb_document"."title" IS '文档标题';
COMMENT ON COLUMN "kb_document"."category" IS '文档分类';
COMMENT ON COLUMN "kb_document"."tags" IS '标签列表';
COMMENT ON COLUMN "kb_document"."summary" IS '摘要';
COMMENT ON COLUMN "kb_document"."source_type" IS '来源类型';
COMMENT ON COLUMN "kb_document"."format" IS '文档格式';
COMMENT ON COLUMN "kb_document"."is_enabled" IS '是否参与检索';
COMMENT ON COLUMN "kb_document"."extract_status" IS '抽取状态';
COMMENT ON COLUMN "kb_document"."sync_status" IS '索引状态';
COMMENT ON COLUMN "kb_document"."content_hash" IS '原始文件内容哈希';
COMMENT ON COLUMN "kb_document"."normalized_text_hash" IS '规范化全文哈希';
COMMENT ON COLUMN "kb_document"."chunk_count" IS 'chunk 数量';
COMMENT ON COLUMN "kb_document"."file_size" IS '文件大小';
COMMENT ON COLUMN "kb_document"."last_indexed_at" IS '最近索引时间';
COMMENT ON COLUMN "kb_document"."last_error" IS '最近错误';
COMMENT ON COLUMN "kb_document"."create_time" IS '创建时间';
COMMENT ON COLUMN "kb_document"."update_time" IS '更新时间';
COMMENT ON TABLE "kb_document" IS '知识库文档元数据。';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "kb_chunk";
        DROP TABLE IF EXISTS "kb_document";"""


MODELS_STATE = (
    "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"
)
