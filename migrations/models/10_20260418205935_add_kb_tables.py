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
COMMENT ON TABLE "kb_asset_chunk" IS '全局知识库资产索引切块。';
        CREATE TABLE IF NOT EXISTS "kb_asset_reference" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "source_asset_id" INT NOT NULL,
    "target_asset_id" INT NOT NULL,
    "description" VARCHAR(500) NOT NULL DEFAULT '',
    "is_auto" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_kb_asset_re_source__ecbf69" UNIQUE ("source_asset_id", "target_asset_id")
);
CREATE INDEX IF NOT EXISTS "idx_kb_asset_re_source__e9621a" ON "kb_asset_reference" ("source_asset_id");
CREATE INDEX IF NOT EXISTS "idx_kb_asset_re_target__16dd41" ON "kb_asset_reference" ("target_asset_id");
COMMENT ON COLUMN "kb_asset_reference"."id" IS '引用记录 ID';
COMMENT ON COLUMN "kb_asset_reference"."source_asset_id" IS '发起引用的资产 ID';
COMMENT ON COLUMN "kb_asset_reference"."target_asset_id" IS '被引用的资产 ID';
COMMENT ON COLUMN "kb_asset_reference"."description" IS '引用说明，描述被引用资产补充了哪些内容';
COMMENT ON COLUMN "kb_asset_reference"."is_auto" IS '是否由系统自动检测生成';
COMMENT ON COLUMN "kb_asset_reference"."create_time" IS '创建时间';
COMMENT ON COLUMN "kb_asset_reference"."update_time" IS '更新时间';
COMMENT ON TABLE "kb_asset_reference" IS '全局知识库资产间引用关系。';
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
COMMENT ON TABLE "kb_document" IS '知识库文档元数据。';
        CREATE TABLE IF NOT EXISTS "kb_document_reference" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "source_document_id" INT NOT NULL,
    "target_document_id" INT NOT NULL,
    "description" VARCHAR(500) NOT NULL DEFAULT '',
    "is_auto" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_kb_document_source__f8e48a" UNIQUE ("source_document_id", "target_document_id")
);
CREATE INDEX IF NOT EXISTS "idx_kb_document_workspa_2258dc" ON "kb_document_reference" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_kb_document_source__b51ea6" ON "kb_document_reference" ("source_document_id");
CREATE INDEX IF NOT EXISTS "idx_kb_document_target__4e9e43" ON "kb_document_reference" ("target_document_id");
CREATE INDEX IF NOT EXISTS "idx_kb_document_workspa_1c535f" ON "kb_document_reference" ("workspace_id", "source_document_id");
CREATE INDEX IF NOT EXISTS "idx_kb_document_workspa_c7af54" ON "kb_document_reference" ("workspace_id", "target_document_id");
COMMENT ON COLUMN "kb_document_reference"."id" IS '引用记录 ID';
COMMENT ON COLUMN "kb_document_reference"."workspace_id" IS '所属工作区 ID（source 和 target 必须同属此工作区）';
COMMENT ON COLUMN "kb_document_reference"."source_document_id" IS '发起引用的文档 ID';
COMMENT ON COLUMN "kb_document_reference"."target_document_id" IS '被引用的文档 ID';
COMMENT ON COLUMN "kb_document_reference"."description" IS '引用说明，描述被引用文档补充了哪些内容';
COMMENT ON COLUMN "kb_document_reference"."is_auto" IS '是否由系统自动检测生成';
COMMENT ON COLUMN "kb_document_reference"."create_time" IS '创建时间';
COMMENT ON COLUMN "kb_document_reference"."update_time" IS '更新时间';
COMMENT ON TABLE "kb_document_reference" IS '工作区知识库文档间引用关系。';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "kb_asset_binding";
        DROP TABLE IF EXISTS "kb_asset_reference";
        DROP TABLE IF EXISTS "kb_document_reference";
        DROP TABLE IF EXISTS "kb_asset";
        DROP TABLE IF EXISTS "kb_asset_chunk";
        DROP TABLE IF EXISTS "kb_document";
        DROP TABLE IF EXISTS "kb_chunk";"""


MODELS_STATE = (
    "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"
    "WCaKNeL3/8f80GQ14="
)
