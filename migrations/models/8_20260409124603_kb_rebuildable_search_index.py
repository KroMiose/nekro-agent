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
        DROP TABLE IF EXISTS "kb_document";
        DROP TABLE IF EXISTS "kb_chunk";"""


MODELS_STATE = (
    "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"
)
