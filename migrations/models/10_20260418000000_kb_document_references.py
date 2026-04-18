from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "kb_document_reference" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "source_document_id" INT NOT NULL,
    "target_document_id" INT NOT NULL,
    "description" VARCHAR(500) NOT NULL DEFAULT '',
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_kb_document_source_target" UNIQUE ("source_document_id", "target_document_id")
);
CREATE INDEX IF NOT EXISTS "idx_kb_doc_ref_workspace_id" ON "kb_document_reference" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_kb_doc_ref_source" ON "kb_document_reference" ("workspace_id", "source_document_id");
CREATE INDEX IF NOT EXISTS "idx_kb_doc_ref_target" ON "kb_document_reference" ("workspace_id", "target_document_id");
COMMENT ON COLUMN "kb_document_reference"."id" IS '引用记录 ID';
COMMENT ON COLUMN "kb_document_reference"."workspace_id" IS '所属工作区 ID';
COMMENT ON COLUMN "kb_document_reference"."source_document_id" IS '发起引用的文档 ID';
COMMENT ON COLUMN "kb_document_reference"."target_document_id" IS '被引用的文档 ID';
COMMENT ON COLUMN "kb_document_reference"."description" IS '引用说明，描述被引用文档补充了哪些内容';
COMMENT ON TABLE "kb_document_reference" IS '工作区知识库文档间引用关系';

        CREATE TABLE IF NOT EXISTS "kb_asset_reference" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "source_asset_id" INT NOT NULL,
    "target_asset_id" INT NOT NULL,
    "description" VARCHAR(500) NOT NULL DEFAULT '',
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_kb_asset_source_target" UNIQUE ("source_asset_id", "target_asset_id")
);
CREATE INDEX IF NOT EXISTS "idx_kb_asset_ref_source" ON "kb_asset_reference" ("source_asset_id");
CREATE INDEX IF NOT EXISTS "idx_kb_asset_ref_target" ON "kb_asset_reference" ("target_asset_id");
COMMENT ON COLUMN "kb_asset_reference"."id" IS '引用记录 ID';
COMMENT ON COLUMN "kb_asset_reference"."source_asset_id" IS '发起引用的资产 ID';
COMMENT ON COLUMN "kb_asset_reference"."target_asset_id" IS '被引用的资产 ID';
COMMENT ON COLUMN "kb_asset_reference"."description" IS '引用说明，描述被引用资产补充了哪些内容';
COMMENT ON TABLE "kb_asset_reference" IS '全局知识库资产间引用关系';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "kb_document_reference";
        DROP TABLE IF EXISTS "kb_asset_reference";
    """
