from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "email" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "account_username" VARCHAR(256) NOT NULL,
    "email_uid" VARCHAR(128) NOT NULL,
    "message_id" VARCHAR(512) NOT NULL DEFAULT '',
    "subject" VARCHAR(1024) NOT NULL DEFAULT '',
    "sender" VARCHAR(512) NOT NULL DEFAULT '',
    "recipients" TEXT NOT NULL,
    "date" TIMESTAMPTZ,
    "body_text" TEXT NOT NULL,
    "has_attachments" BOOL NOT NULL DEFAULT False,
    "attachment_names" TEXT NOT NULL,
    "in_reply_to" VARCHAR(512) NOT NULL DEFAULT '',
    "references" TEXT NOT NULL,
    "fetched_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_email_account_f2d7e6" UNIQUE ("account_username", "email_uid")
);
CREATE INDEX IF NOT EXISTS "idx_email_account_e542ae" ON "email" ("account_username");
COMMENT ON COLUMN "email"."id" IS 'ID';
COMMENT ON COLUMN "email"."account_username" IS '所属邮箱账户';
COMMENT ON COLUMN "email"."email_uid" IS 'IMAP UID';
COMMENT ON COLUMN "email"."message_id" IS 'Message-ID 头';
COMMENT ON COLUMN "email"."subject" IS '邮件主题';
COMMENT ON COLUMN "email"."sender" IS '发件人';
COMMENT ON COLUMN "email"."recipients" IS '收件人(JSON)';
COMMENT ON COLUMN "email"."date" IS '邮件日期';
COMMENT ON COLUMN "email"."body_text" IS '纯文本正文(截断)';
COMMENT ON COLUMN "email"."has_attachments" IS '是否有附件';
COMMENT ON COLUMN "email"."attachment_names" IS '附件文件名列表(JSON)';
COMMENT ON COLUMN "email"."in_reply_to" IS 'In-Reply-To 头';
COMMENT ON COLUMN "email"."references" IS 'References 头';
COMMENT ON COLUMN "email"."fetched_at" IS '获取时间';
COMMENT ON COLUMN "email"."create_time" IS '创建时间';
COMMENT ON COLUMN "email"."update_time" IS '更新时间';
COMMENT ON TABLE "email" IS '邮件模型，用于存储已处理的邮件信息';
        ALTER TABLE "chat_channel" ADD "observe_mode" BOOL NOT NULL DEFAULT False;
        COMMENT ON COLUMN "chat_channel"."observe_mode" IS '旁观模式';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "chat_channel" DROP COLUMN "observe_mode";
        DROP TABLE IF EXISTS "email";"""


MODELS_STATE = (
    "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"
)
