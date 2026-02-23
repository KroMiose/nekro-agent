from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "chat_channel" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "is_active" BOOL NOT NULL DEFAULT True,
    "preset_id" INT,
    "data" TEXT NOT NULL,
    "adapter_key" VARCHAR(64) NOT NULL,
    "channel_id" VARCHAR(64) NOT NULL,
    "channel_name" VARCHAR(64),
    "channel_type" VARCHAR(32),
    "chat_key" VARCHAR(64) NOT NULL,
    "conversation_start_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_chat_channe_adapter_7b45b1" ON "chat_channel" ("adapter_key");
CREATE INDEX IF NOT EXISTS "idx_chat_channe_channel_36ed4e" ON "chat_channel" ("channel_id");
CREATE INDEX IF NOT EXISTS "idx_chat_channe_chat_ke_a871f2" ON "chat_channel" ("chat_key");
COMMENT ON COLUMN "chat_channel"."id" IS 'ID';
COMMENT ON COLUMN "chat_channel"."is_active" IS '是否激活';
COMMENT ON COLUMN "chat_channel"."preset_id" IS '人设 ID';
COMMENT ON COLUMN "chat_channel"."data" IS '频道数据';
COMMENT ON COLUMN "chat_channel"."adapter_key" IS '适配器标识';
COMMENT ON COLUMN "chat_channel"."channel_id" IS '频道 ID';
COMMENT ON COLUMN "chat_channel"."channel_name" IS '频道名称';
COMMENT ON COLUMN "chat_channel"."channel_type" IS '频道类型';
COMMENT ON COLUMN "chat_channel"."chat_key" IS '全局聊天频道唯一标识';
COMMENT ON COLUMN "chat_channel"."conversation_start_time" IS '对话起始时间';
COMMENT ON COLUMN "chat_channel"."create_time" IS '创建时间';
COMMENT ON COLUMN "chat_channel"."update_time" IS '更新时间';
COMMENT ON TABLE "chat_channel" IS '数据库聊天频道模型';
CREATE TABLE IF NOT EXISTS "chat_message" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "sender_id" VARCHAR(128) NOT NULL,
    "sender_name" VARCHAR(128) NOT NULL,
    "sender_nickname" VARCHAR(128) NOT NULL,
    "is_tome" INT NOT NULL,
    "is_recalled" BOOL NOT NULL,
    "adapter_key" VARCHAR(64) NOT NULL,
    "message_id" VARCHAR(64) NOT NULL,
    "chat_key" VARCHAR(64) NOT NULL,
    "chat_type" VARCHAR(32) NOT NULL,
    "platform_userid" VARCHAR(256) NOT NULL,
    "content_text" TEXT NOT NULL,
    "content_data" TEXT NOT NULL,
    "raw_cq_code" TEXT NOT NULL,
    "ext_data" TEXT NOT NULL,
    "send_timestamp" INT NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_chat_messag_sender__c1ef2f" ON "chat_message" ("sender_id");
CREATE INDEX IF NOT EXISTS "idx_chat_messag_sender__4b32ff" ON "chat_message" ("sender_name");
CREATE INDEX IF NOT EXISTS "idx_chat_messag_sender__bfbf90" ON "chat_message" ("sender_nickname");
CREATE INDEX IF NOT EXISTS "idx_chat_messag_adapter_1cb67a" ON "chat_message" ("adapter_key");
CREATE INDEX IF NOT EXISTS "idx_chat_messag_message_3b609b" ON "chat_message" ("message_id");
CREATE INDEX IF NOT EXISTS "idx_chat_messag_chat_ke_e722b2" ON "chat_message" ("chat_key");
CREATE INDEX IF NOT EXISTS "idx_chat_messag_chat_ty_1ff9f5" ON "chat_message" ("chat_type");
CREATE INDEX IF NOT EXISTS "idx_chat_messag_platfor_aaa4f0" ON "chat_message" ("platform_userid");
CREATE INDEX IF NOT EXISTS "idx_chat_messag_send_ti_35f8ca" ON "chat_message" ("send_timestamp");
COMMENT ON COLUMN "chat_message"."id" IS 'ID';
COMMENT ON COLUMN "chat_message"."sender_id" IS '发送者 ID';
COMMENT ON COLUMN "chat_message"."sender_name" IS '发送者真实昵称';
COMMENT ON COLUMN "chat_message"."sender_nickname" IS '发送者显示昵称';
COMMENT ON COLUMN "chat_message"."is_tome" IS '是否与 Bot 相关';
COMMENT ON COLUMN "chat_message"."is_recalled" IS '是否为撤回消息';
COMMENT ON COLUMN "chat_message"."adapter_key" IS '适配器标识';
COMMENT ON COLUMN "chat_message"."message_id" IS '消息平台 ID';
COMMENT ON COLUMN "chat_message"."chat_key" IS '聊天频道唯一标识';
COMMENT ON COLUMN "chat_message"."chat_type" IS '聊天频道类型';
COMMENT ON COLUMN "chat_message"."platform_userid" IS '平台用户 ID';
COMMENT ON COLUMN "chat_message"."content_text" IS '消息内容文本';
COMMENT ON COLUMN "chat_message"."content_data" IS '消息内容数据 JSON';
COMMENT ON COLUMN "chat_message"."raw_cq_code" IS '原始 CQ 码';
COMMENT ON COLUMN "chat_message"."ext_data" IS '扩展数据';
COMMENT ON COLUMN "chat_message"."send_timestamp" IS '发送时间戳';
COMMENT ON COLUMN "chat_message"."create_time" IS '创建时间';
COMMENT ON COLUMN "chat_message"."update_time" IS '更新时间';
COMMENT ON TABLE "chat_message" IS '数据库聊天消息模型';
CREATE TABLE IF NOT EXISTS "exec_code" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "chat_key" VARCHAR(64) NOT NULL,
    "trigger_user_id" VARCHAR(256) NOT NULL DEFAULT '0',
    "trigger_user_name" VARCHAR(128) NOT NULL DEFAULT 'System',
    "success" BOOL NOT NULL DEFAULT False,
    "code_text" TEXT NOT NULL,
    "outputs" TEXT NOT NULL,
    "use_model" VARCHAR(128) DEFAULT '',
    "thought_chain" TEXT,
    "stop_type" SMALLINT NOT NULL DEFAULT 0,
    "exec_time_ms" INT NOT NULL DEFAULT 0,
    "generation_time_ms" INT NOT NULL DEFAULT 0,
    "total_time_ms" INT NOT NULL DEFAULT 0,
    "extra_data" TEXT NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_exec_code_chat_ke_397ea8" ON "exec_code" ("chat_key");
CREATE INDEX IF NOT EXISTS "idx_exec_code_trigger_143dcf" ON "exec_code" ("trigger_user_id");
COMMENT ON COLUMN "exec_code"."id" IS 'ID';
COMMENT ON COLUMN "exec_code"."chat_key" IS '聊天频道唯一标识';
COMMENT ON COLUMN "exec_code"."trigger_user_id" IS '触发用户ID';
COMMENT ON COLUMN "exec_code"."trigger_user_name" IS '触发用户名';
COMMENT ON COLUMN "exec_code"."success" IS '是否成功';
COMMENT ON COLUMN "exec_code"."code_text" IS '执行代码文本';
COMMENT ON COLUMN "exec_code"."outputs" IS '输出结果';
COMMENT ON COLUMN "exec_code"."use_model" IS '使用模型';
COMMENT ON COLUMN "exec_code"."thought_chain" IS '思维链信息';
COMMENT ON COLUMN "exec_code"."stop_type" IS '停止类型';
COMMENT ON COLUMN "exec_code"."exec_time_ms" IS '执行时间(毫秒)';
COMMENT ON COLUMN "exec_code"."generation_time_ms" IS '生成时间(毫秒)';
COMMENT ON COLUMN "exec_code"."total_time_ms" IS '响应总耗时(毫秒)';
COMMENT ON COLUMN "exec_code"."extra_data" IS '额外数据';
COMMENT ON COLUMN "exec_code"."create_time" IS '创建时间';
COMMENT ON COLUMN "exec_code"."update_time" IS '更新时间';
COMMENT ON TABLE "exec_code" IS '数据库执行代码模型';
CREATE TABLE IF NOT EXISTS "plugin_data" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "plugin_key" VARCHAR(128) NOT NULL,
    "data_key" VARCHAR(128) NOT NULL,
    "data_value" TEXT NOT NULL,
    "target_chat_key" VARCHAR(64) NOT NULL,
    "target_user_id" VARCHAR(256) NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_plugin_data_plugin__265997" ON "plugin_data" ("plugin_key");
CREATE INDEX IF NOT EXISTS "idx_plugin_data_data_ke_262fac" ON "plugin_data" ("data_key");
CREATE INDEX IF NOT EXISTS "idx_plugin_data_target__b00aa5" ON "plugin_data" ("target_chat_key");
CREATE INDEX IF NOT EXISTS "idx_plugin_data_target__62cb3b" ON "plugin_data" ("target_user_id");
COMMENT ON COLUMN "plugin_data"."id" IS 'ID';
COMMENT ON COLUMN "plugin_data"."plugin_key" IS '插件唯一标识';
COMMENT ON COLUMN "plugin_data"."data_key" IS '插件数据键';
COMMENT ON COLUMN "plugin_data"."data_value" IS '插件数据值';
COMMENT ON COLUMN "plugin_data"."target_chat_key" IS '目标聊天频道唯一标识';
COMMENT ON COLUMN "plugin_data"."target_user_id" IS '目标用户ID';
COMMENT ON COLUMN "plugin_data"."create_time" IS '创建时间';
COMMENT ON COLUMN "plugin_data"."update_time" IS '更新时间';
COMMENT ON TABLE "plugin_data" IS '数据库插件数据模型';
CREATE TABLE IF NOT EXISTS "presets" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "remote_id" VARCHAR(54),
    "on_shared" BOOL NOT NULL DEFAULT False,
    "name" VARCHAR(256) NOT NULL,
    "title" VARCHAR(128) NOT NULL,
    "avatar" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "tags" VARCHAR(512) NOT NULL,
    "ext_data" JSONB,
    "author" VARCHAR(128) NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_presets_remote__b514e3" ON "presets" ("remote_id");
CREATE INDEX IF NOT EXISTS "idx_presets_name_5a25e4" ON "presets" ("name");
CREATE INDEX IF NOT EXISTS "idx_presets_title_75e71c" ON "presets" ("title");
COMMENT ON COLUMN "presets"."id" IS 'ID';
COMMENT ON COLUMN "presets"."remote_id" IS '远程预设ID';
COMMENT ON COLUMN "presets"."on_shared" IS '是否在共享预设中';
COMMENT ON COLUMN "presets"."name" IS '预设名称';
COMMENT ON COLUMN "presets"."title" IS '标题';
COMMENT ON COLUMN "presets"."avatar" IS '预设头像(base64)';
COMMENT ON COLUMN "presets"."content" IS '预设内容';
COMMENT ON COLUMN "presets"."description" IS '预设描述';
COMMENT ON COLUMN "presets"."tags" IS '预设标签(逗号分隔)';
COMMENT ON COLUMN "presets"."ext_data" IS '扩展数据';
COMMENT ON COLUMN "presets"."author" IS '作者';
COMMENT ON COLUMN "presets"."create_time" IS '创建时间';
COMMENT ON COLUMN "presets"."update_time" IS '更新时间';
COMMENT ON TABLE "presets" IS '数据库预设模型';
CREATE TABLE IF NOT EXISTS "recurring_timer_job" (
    "id" UUID NOT NULL PRIMARY KEY,
    "job_id" VARCHAR(12) NOT NULL UNIQUE,
    "chat_key" VARCHAR(64) NOT NULL,
    "title" VARCHAR(128),
    "event_desc" TEXT NOT NULL,
    "cron_expr" VARCHAR(128) NOT NULL,
    "timezone" VARCHAR(64) NOT NULL,
    "workday_mode" VARCHAR(16) NOT NULL DEFAULT 'none',
    "status" VARCHAR(16) NOT NULL DEFAULT 'active',
    "next_run_at" TIMESTAMPTZ,
    "last_run_at" TIMESTAMPTZ,
    "misfire_policy" VARCHAR(16) NOT NULL DEFAULT 'fire_once',
    "misfire_grace_seconds" INT NOT NULL DEFAULT 300,
    "consecutive_failures" INT NOT NULL DEFAULT 0,
    "last_error" TEXT,
    "paused_notice_sent_at" TIMESTAMPTZ,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_recurring_t_job_id_5b6a36" ON "recurring_timer_job" ("job_id");
CREATE INDEX IF NOT EXISTS "idx_recurring_t_chat_ke_9ba710" ON "recurring_timer_job" ("chat_key");
CREATE INDEX IF NOT EXISTS "idx_recurring_t_status_8bf4cc" ON "recurring_timer_job" ("status");
CREATE INDEX IF NOT EXISTS "idx_recurring_t_next_ru_a71a4d" ON "recurring_timer_job" ("next_run_at");
CREATE INDEX IF NOT EXISTS "idx_recurring_t_last_ru_9f270f" ON "recurring_timer_job" ("last_run_at");
COMMENT ON COLUMN "recurring_timer_job"."id" IS '任务ID（UUID）';
COMMENT ON COLUMN "recurring_timer_job"."job_id" IS '对外任务ID（短ID，全局唯一）';
COMMENT ON COLUMN "recurring_timer_job"."chat_key" IS '目标聊天频道唯一标识';
COMMENT ON COLUMN "recurring_timer_job"."title" IS '任务标题（可选）';
COMMENT ON COLUMN "recurring_timer_job"."event_desc" IS '触发时提供给 Agent 的事件描述（上下文）';
COMMENT ON COLUMN "recurring_timer_job"."cron_expr" IS 'Cron 表达式（默认 5 段：min hour day month dow）';
COMMENT ON COLUMN "recurring_timer_job"."timezone" IS '时区（IANA TZ，例如 Asia/Shanghai）';
COMMENT ON COLUMN "recurring_timer_job"."workday_mode" IS '触发日模式：none/mon_fri/weekend/cn_workday/cn_restday';
COMMENT ON COLUMN "recurring_timer_job"."status" IS '状态：active/paused';
COMMENT ON COLUMN "recurring_timer_job"."next_run_at" IS '下次触发时间（本地时区）';
COMMENT ON COLUMN "recurring_timer_job"."last_run_at" IS '上次触发时间（本地时区）';
COMMENT ON COLUMN "recurring_timer_job"."misfire_policy" IS '错过触发策略：fire_once/skip';
COMMENT ON COLUMN "recurring_timer_job"."misfire_grace_seconds" IS '错过触发宽限秒数（在宽限内可补发）';
COMMENT ON COLUMN "recurring_timer_job"."consecutive_failures" IS '连续失败次数';
COMMENT ON COLUMN "recurring_timer_job"."last_error" IS '最近一次失败原因（可选）';
COMMENT ON COLUMN "recurring_timer_job"."paused_notice_sent_at" IS '自动暂停后已提示时间（用于去重提示）';
COMMENT ON COLUMN "recurring_timer_job"."create_time" IS '创建时间';
COMMENT ON COLUMN "recurring_timer_job"."update_time" IS '更新时间';
COMMENT ON TABLE "recurring_timer_job" IS '持久化周期定时任务（cron）';
CREATE TABLE IF NOT EXISTS "user" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "username" VARCHAR(128) NOT NULL,
    "password" VARCHAR(128) NOT NULL,
    "adapter_key" VARCHAR(64) NOT NULL,
    "platform_userid" VARCHAR(256) NOT NULL,
    "perm_level" INT NOT NULL,
    "login_time" TIMESTAMPTZ NOT NULL,
    "ban_until" TIMESTAMPTZ,
    "prevent_trigger_until" TIMESTAMPTZ,
    "ext_data" JSONB NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "user"."id" IS '用户ID';
COMMENT ON COLUMN "user"."username" IS '用户名';
COMMENT ON COLUMN "user"."password" IS '密码';
COMMENT ON COLUMN "user"."adapter_key" IS '适配器ID';
COMMENT ON COLUMN "user"."platform_userid" IS '平台用户ID';
COMMENT ON COLUMN "user"."perm_level" IS '权限等级';
COMMENT ON COLUMN "user"."login_time" IS '上次登录时间';
COMMENT ON COLUMN "user"."ban_until" IS '封禁截止时间';
COMMENT ON COLUMN "user"."prevent_trigger_until" IS '禁止触发截止时间';
COMMENT ON COLUMN "user"."ext_data" IS '扩展数据';
COMMENT ON COLUMN "user"."create_time" IS '创建时间';
COMMENT ON COLUMN "user"."update_time" IS '更新时间';
COMMENT ON TABLE "user" IS '数据库用户模型';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
