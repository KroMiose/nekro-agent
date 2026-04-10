from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "kb_asset" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "source_path" VARCHAR(512) NOT NULL UNIQUE,
    "normalized_text_path" VARCHAR(256),
    "file_name" VARCHAR(256) NOT NULL,
    "file_ext" VARCHAR(32) NOT NULL,
    "mime_type" VARCHAR(128) NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "category" VARCHAR(64) NOT NULL DEFAULT '',
    "tags" JSONB NOT NULL,
    "summary" TEXT NOT NULL,
    "source_type" VARCHAR(32) NOT NULL DEFAULT 'upload',
    "format" VARCHAR(32) NOT NULL,
    "is_enabled" BOOL NOT NULL DEFAULT True,
    "extract_status" VARCHAR(32) NOT NULL DEFAULT 'pending',
    "sync_status" VARCHAR(32) NOT NULL DEFAULT 'pending',
    "content_hash" VARCHAR(64) NOT NULL UNIQUE,
    "normalized_text_hash" VARCHAR(64) NOT NULL DEFAULT '',
    "chunk_count" INT NOT NULL DEFAULT 0,
    "file_size" BIGINT NOT NULL DEFAULT 0,
    "last_indexed_at" TIMESTAMPTZ,
    "last_error" TEXT,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_kb_asset_is_enab_56521e" ON "kb_asset" ("is_enabled");
CREATE INDEX IF NOT EXISTS "idx_kb_asset_is_enab_7e46bf" ON "kb_asset" ("is_enabled", "sync_status");
CREATE INDEX IF NOT EXISTS "idx_kb_asset_categor_d9cfed" ON "kb_asset" ("category", "format");
COMMENT ON COLUMN "kb_asset"."id" IS '资产 ID';
COMMENT ON COLUMN "kb_asset"."source_path" IS '相对 kb_library/files 根目录的源文件路径';
COMMENT ON COLUMN "kb_asset"."normalized_text_path" IS '相对 kb_library/.normalized 根目录的规范化全文路径';
COMMENT ON COLUMN "kb_asset"."file_name" IS '原始文件名';
COMMENT ON COLUMN "kb_asset"."file_ext" IS '文件扩展名';
COMMENT ON COLUMN "kb_asset"."mime_type" IS '文件 MIME 类型';
COMMENT ON COLUMN "kb_asset"."title" IS '资产标题';
COMMENT ON COLUMN "kb_asset"."category" IS '资产分类';
COMMENT ON COLUMN "kb_asset"."tags" IS '资产标签列表';
COMMENT ON COLUMN "kb_asset"."summary" IS '资产摘要';
COMMENT ON COLUMN "kb_asset"."source_type" IS '来源类型';
COMMENT ON COLUMN "kb_asset"."format" IS '文档格式';
COMMENT ON COLUMN "kb_asset"."is_enabled" IS '是否允许被绑定与检索';
COMMENT ON COLUMN "kb_asset"."extract_status" IS '抽取状态';
COMMENT ON COLUMN "kb_asset"."sync_status" IS '索引状态';
COMMENT ON COLUMN "kb_asset"."content_hash" IS '原始文件内容哈希';
COMMENT ON COLUMN "kb_asset"."normalized_text_hash" IS '规范化全文哈希';
COMMENT ON COLUMN "kb_asset"."chunk_count" IS 'chunk 数量';
COMMENT ON COLUMN "kb_asset"."file_size" IS '文件大小';
COMMENT ON COLUMN "kb_asset"."last_indexed_at" IS '最近索引时间';
COMMENT ON COLUMN "kb_asset"."last_error" IS '最近错误';
COMMENT ON COLUMN "kb_asset"."create_time" IS '创建时间';
COMMENT ON COLUMN "kb_asset"."update_time" IS '更新时间';
COMMENT ON TABLE "kb_asset" IS '全局知识库资产元数据。';
        CREATE TABLE IF NOT EXISTS "kb_asset_binding" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "asset_id" INT NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_kb_asset_bi_workspa_1488ff" UNIQUE ("workspace_id", "asset_id")
);
CREATE INDEX IF NOT EXISTS "idx_kb_asset_bi_workspa_5b471e" ON "kb_asset_binding" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_kb_asset_bi_asset_i_a37134" ON "kb_asset_binding" ("asset_id");
CREATE INDEX IF NOT EXISTS "idx_kb_asset_bi_workspa_1488ff" ON "kb_asset_binding" ("workspace_id", "asset_id");
COMMENT ON COLUMN "kb_asset_binding"."id" IS '绑定 ID';
COMMENT ON COLUMN "kb_asset_binding"."workspace_id" IS '工作区 ID';
COMMENT ON COLUMN "kb_asset_binding"."asset_id" IS '全局资产 ID';
COMMENT ON COLUMN "kb_asset_binding"."create_time" IS '创建时间';
COMMENT ON COLUMN "kb_asset_binding"."update_time" IS '更新时间';
COMMENT ON TABLE "kb_asset_binding" IS '工作区与全局知识库资产绑定关系。';
        CREATE TABLE IF NOT EXISTS "kb_asset_chunk" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "asset_id" INT NOT NULL,
    "chunk_index" INT NOT NULL,
    "heading_path" VARCHAR(512) NOT NULL DEFAULT '',
    "char_start" INT NOT NULL DEFAULT 0,
    "char_end" INT NOT NULL DEFAULT 0,
    "token_count" INT NOT NULL DEFAULT 0,
    "embedding_ref" VARCHAR(64),
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_kb_asset_ch_asset_i_e588ad" UNIQUE ("asset_id", "chunk_index")
);
CREATE INDEX IF NOT EXISTS "idx_kb_asset_ch_asset_i_6c685c" ON "kb_asset_chunk" ("asset_id");
CREATE INDEX IF NOT EXISTS "idx_kb_asset_ch_embeddi_8b5b88" ON "kb_asset_chunk" ("embedding_ref");
CREATE INDEX IF NOT EXISTS "idx_kb_asset_ch_asset_i_e588ad" ON "kb_asset_chunk" ("asset_id", "chunk_index");
COMMENT ON COLUMN "kb_asset_chunk"."id" IS '资产 Chunk ID';
COMMENT ON COLUMN "kb_asset_chunk"."asset_id" IS '所属资产 ID';
COMMENT ON COLUMN "kb_asset_chunk"."chunk_index" IS '资产内顺序';
COMMENT ON COLUMN "kb_asset_chunk"."heading_path" IS '标题层级路径';
COMMENT ON COLUMN "kb_asset_chunk"."char_start" IS '字符起始偏移';
COMMENT ON COLUMN "kb_asset_chunk"."char_end" IS '字符结束偏移';
COMMENT ON COLUMN "kb_asset_chunk"."token_count" IS '估算 token 数';
COMMENT ON COLUMN "kb_asset_chunk"."embedding_ref" IS 'Qdrant 向量 ID';
COMMENT ON COLUMN "kb_asset_chunk"."create_time" IS '创建时间';
COMMENT ON COLUMN "kb_asset_chunk"."update_time" IS '更新时间';
COMMENT ON TABLE "kb_asset_chunk" IS '全局知识库资产索引切块。';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "kb_asset_chunk";
        DROP TABLE IF EXISTS "kb_asset_binding";
        DROP TABLE IF EXISTS "kb_asset";"""


MODELS_STATE = (
    "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"
    "xod6PPlgs4TK3nQPlHPV5+/3//ZAKG"
)
