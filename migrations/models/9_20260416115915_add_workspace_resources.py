from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "workspace_resource" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "resource_key" VARCHAR(128) NOT NULL UNIQUE,
    "name" VARCHAR(128) NOT NULL,
    "template_key" VARCHAR(64),
    "resource_note" TEXT NOT NULL,
    "resource_tags_json" JSONB NOT NULL,
    "resource_prompt" TEXT NOT NULL,
    "schema_json" JSONB NOT NULL,
    "public_payload" JSONB NOT NULL,
    "secret_payload_encrypted" TEXT NOT NULL,
    "enabled" BOOL NOT NULL DEFAULT True,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_workspace_r_resourc_477220" ON "workspace_resource" ("resource_key");
CREATE INDEX IF NOT EXISTS "idx_workspace_r_name_beb0a4" ON "workspace_resource" ("name");
COMMENT ON COLUMN "workspace_resource"."id" IS 'ID';
COMMENT ON COLUMN "workspace_resource"."resource_key" IS '稳定资源键';
COMMENT ON COLUMN "workspace_resource"."name" IS '资源名称';
COMMENT ON COLUMN "workspace_resource"."template_key" IS '模板键';
COMMENT ON COLUMN "workspace_resource"."resource_note" IS '资源备注';
COMMENT ON COLUMN "workspace_resource"."resource_tags_json" IS '资源标签列表';
COMMENT ON COLUMN "workspace_resource"."resource_prompt" IS '资源提示';
COMMENT ON COLUMN "workspace_resource"."schema_json" IS '字段结构定义';
COMMENT ON COLUMN "workspace_resource"."public_payload" IS '非敏感字段值';
COMMENT ON COLUMN "workspace_resource"."secret_payload_encrypted" IS '加密后的敏感字段值';
COMMENT ON COLUMN "workspace_resource"."enabled" IS '是否启用';
COMMENT ON COLUMN "workspace_resource"."create_time" IS '创建时间';
COMMENT ON COLUMN "workspace_resource"."update_time" IS '更新时间';
COMMENT ON TABLE "workspace_resource" IS '工作区资源定义模型。';
        CREATE TABLE IF NOT EXISTS "workspace_resource_binding" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "resource_id" INT NOT NULL,
    "enabled" BOOL NOT NULL DEFAULT True,
    "sort_order" INT NOT NULL DEFAULT 0,
    "note" VARCHAR(256) NOT NULL DEFAULT '',
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_workspace_r_workspa_9b7715" UNIQUE ("workspace_id", "resource_id")
);
CREATE INDEX IF NOT EXISTS "idx_workspace_r_workspa_752606" ON "workspace_resource_binding" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_workspace_r_resourc_58750c" ON "workspace_resource_binding" ("resource_id");
CREATE INDEX IF NOT EXISTS "idx_workspace_r_workspa_076b24" ON "workspace_resource_binding" ("workspace_id", "sort_order");
CREATE INDEX IF NOT EXISTS "idx_workspace_r_workspa_36b547" ON "workspace_resource_binding" ("workspace_id", "enabled");
COMMENT ON COLUMN "workspace_resource_binding"."id" IS 'ID';
COMMENT ON COLUMN "workspace_resource_binding"."workspace_id" IS '工作区 ID';
COMMENT ON COLUMN "workspace_resource_binding"."resource_id" IS '资源 ID';
COMMENT ON COLUMN "workspace_resource_binding"."enabled" IS '是否启用';
COMMENT ON COLUMN "workspace_resource_binding"."sort_order" IS '排序';
COMMENT ON COLUMN "workspace_resource_binding"."note" IS '备注';
COMMENT ON COLUMN "workspace_resource_binding"."create_time" IS '创建时间';
COMMENT ON COLUMN "workspace_resource_binding"."update_time" IS '更新时间';
COMMENT ON TABLE "workspace_resource_binding" IS '工作区与资源绑定关系。';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "workspace_resource_binding";
        DROP TABLE IF EXISTS "workspace_resource";"""


MODELS_STATE = (
    "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"
)
