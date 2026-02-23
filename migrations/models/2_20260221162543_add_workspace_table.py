from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "workspace" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(64) NOT NULL UNIQUE,
    "description" TEXT NOT NULL,
    "status" VARCHAR(16) NOT NULL DEFAULT 'stopped',
    "sandbox_image" VARCHAR(128) NOT NULL DEFAULT '',
    "sandbox_version" VARCHAR(64) NOT NULL DEFAULT 'latest',
    "container_name" VARCHAR(64) UNIQUE,
    "container_id" VARCHAR(128),
    "host_port" INT,
    "runtime_policy" VARCHAR(16) NOT NULL DEFAULT 'agent',
    "last_heartbeat" TIMESTAMPTZ,
    "last_error" TEXT,
    "metadata" JSONB NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_workspace_name_1ea932" ON "workspace" ("name");
COMMENT ON COLUMN "workspace"."id" IS 'ID';
COMMENT ON COLUMN "workspace"."name" IS '工作区名称';
COMMENT ON COLUMN "workspace"."description" IS '工作区描述';
COMMENT ON COLUMN "workspace"."status" IS '状态: active|stopped|failed|deleting';
COMMENT ON COLUMN "workspace"."sandbox_image" IS 'cc-sandbox 镜像名';
COMMENT ON COLUMN "workspace"."sandbox_version" IS '镜像版本/Build Tag';
COMMENT ON COLUMN "workspace"."container_name" IS '容器名，格式: nekro-cc-{hex8}，同时用作 Docker 内网主机名';
COMMENT ON COLUMN "workspace"."container_id" IS '容器 ID（运行时填充）';
COMMENT ON COLUMN "workspace"."host_port" IS '宿主机映射端口';
COMMENT ON COLUMN "workspace"."runtime_policy" IS '运行策略: agent|relaxed|strict';
COMMENT ON COLUMN "workspace"."last_heartbeat" IS '最近心跳时间';
COMMENT ON COLUMN "workspace"."last_error" IS '最近错误信息';
COMMENT ON COLUMN "workspace"."metadata" IS '元数据';
COMMENT ON COLUMN "workspace"."create_time" IS '创建时间';
COMMENT ON COLUMN "workspace"."update_time" IS '更新时间';
COMMENT ON TABLE "workspace" IS '工作区数据模型';
        COMMENT ON COLUMN "chat_channel"."workspace_id" IS '关联工作区 ID';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "chat_channel"."workspace_id" IS '工作区 ID';
        DROP TABLE IF EXISTS "workspace";"""


MODELS_STATE = (
    "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"
    "6+/h8jP5YC"
)
