from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "mem_entity" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "entity_type" VARCHAR(16) NOT NULL,
    "name" VARCHAR(256) NOT NULL,
    "canonical_name" VARCHAR(256) NOT NULL,
    "aliases" JSONB NOT NULL,
    "appearance_count" INT NOT NULL DEFAULT 1,
    "source_hint" VARCHAR(8) NOT NULL DEFAULT 'na',
    "is_inactive" BOOL NOT NULL DEFAULT False,
    "platform_identities" JSONB NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_mem_entity_workspa_bea105" ON "mem_entity" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_mem_entity_entity__99a3cc" ON "mem_entity" ("entity_type");
CREATE INDEX IF NOT EXISTS "idx_mem_entity_name_0a4292" ON "mem_entity" ("name");
CREATE INDEX IF NOT EXISTS "idx_mem_entity_canonic_382030" ON "mem_entity" ("canonical_name");
CREATE INDEX IF NOT EXISTS "idx_mem_entity_is_inac_2a8a86" ON "mem_entity" ("is_inactive");
CREATE INDEX IF NOT EXISTS "idx_mem_entity_workspa_e5c99e" ON "mem_entity" ("workspace_id", "canonical_name");
CREATE INDEX IF NOT EXISTS "idx_mem_entity_workspa_ab7dce" ON "mem_entity" ("workspace_id", "entity_type");
COMMENT ON COLUMN "mem_entity"."id" IS '主键 ID';
COMMENT ON COLUMN "mem_entity"."workspace_id" IS '工作区 ID（隔离边界）';
COMMENT ON COLUMN "mem_entity"."entity_type" IS '实体类型';
COMMENT ON COLUMN "mem_entity"."name" IS '实体名称（原始）';
COMMENT ON COLUMN "mem_entity"."canonical_name" IS '规范化名称（用于去重和归一化）';
COMMENT ON COLUMN "mem_entity"."aliases" IS '别名列表（JSON 数组）';
COMMENT ON COLUMN "mem_entity"."appearance_count" IS '出现次数';
COMMENT ON COLUMN "mem_entity"."source_hint" IS '主要来源提示（na/cc）';
COMMENT ON COLUMN "mem_entity"."is_inactive" IS '是否已失活';
COMMENT ON COLUMN "mem_entity"."platform_identities" IS '跨平台身份映射（预留字段）';
COMMENT ON COLUMN "mem_entity"."create_time" IS '创建时间';
COMMENT ON COLUMN "mem_entity"."update_time" IS '更新时间';
COMMENT ON TABLE "mem_entity" IS '记忆实体模型';
        CREATE TABLE IF NOT EXISTS "mem_media_resource" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "content_hash" VARCHAR(64) NOT NULL UNIQUE,
    "media_type" VARCHAR(16) NOT NULL,
    "description" TEXT,
    "tags" JSONB NOT NULL,
    "embedding_ref" VARCHAR(64),
    "original_filename" VARCHAR(256),
    "file_size" INT,
    "dimensions" JSONB,
    "duration" DOUBLE PRECISION,
    "mime_type" VARCHAR(64),
    "reference_count" INT NOT NULL DEFAULT 1,
    "first_seen_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_seen_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "reference_log" JSONB NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_mem_media_r_workspa_640893" ON "mem_media_resource" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_mem_media_r_content_a60f34" ON "mem_media_resource" ("content_hash");
CREATE INDEX IF NOT EXISTS "idx_mem_media_r_embeddi_584af1" ON "mem_media_resource" ("embedding_ref");
CREATE INDEX IF NOT EXISTS "idx_mem_media_r_workspa_aaec67" ON "mem_media_resource" ("workspace_id", "media_type");
CREATE INDEX IF NOT EXISTS "idx_mem_media_r_workspa_9f9962" ON "mem_media_resource" ("workspace_id", "reference_count");
COMMENT ON COLUMN "mem_media_resource"."id" IS '主键 ID';
COMMENT ON COLUMN "mem_media_resource"."workspace_id" IS '工作区 ID';
COMMENT ON COLUMN "mem_media_resource"."content_hash" IS '资源内容的 MD5/SHA256 哈希（全局唯一）';
COMMENT ON COLUMN "mem_media_resource"."media_type" IS '媒体类型';
COMMENT ON COLUMN "mem_media_resource"."description" IS 'AI 生成的文本描述';
COMMENT ON COLUMN "mem_media_resource"."tags" IS '标签列表（JSON 数组）';
COMMENT ON COLUMN "mem_media_resource"."embedding_ref" IS '可选的向量索引引用';
COMMENT ON COLUMN "mem_media_resource"."original_filename" IS '原始文件名';
COMMENT ON COLUMN "mem_media_resource"."file_size" IS '文件大小（字节）';
COMMENT ON COLUMN "mem_media_resource"."dimensions" IS '图片/视频尺寸（如 {width: 800, height: 600}）';
COMMENT ON COLUMN "mem_media_resource"."duration" IS '音视频时长（秒）';
COMMENT ON COLUMN "mem_media_resource"."mime_type" IS 'MIME 类型';
COMMENT ON COLUMN "mem_media_resource"."reference_count" IS '被引用次数';
COMMENT ON COLUMN "mem_media_resource"."first_seen_at" IS '首次出现时间';
COMMENT ON COLUMN "mem_media_resource"."last_seen_at" IS '最后出现时间';
COMMENT ON COLUMN "mem_media_resource"."reference_log" IS '引用记录（JSON 数组，限制最近 N 条）';
COMMENT ON COLUMN "mem_media_resource"."create_time" IS '创建时间';
COMMENT ON COLUMN "mem_media_resource"."update_time" IS '更新时间';
COMMENT ON TABLE "mem_media_resource" IS '记忆媒体资源模型';
        CREATE TABLE IF NOT EXISTS "mem_paragraph" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "memory_source" VARCHAR(8) NOT NULL,
    "cognitive_type" VARCHAR(16) NOT NULL,
    "knowledge_type" VARCHAR(16) NOT NULL,
    "content" TEXT NOT NULL,
    "summary" VARCHAR(512),
    "event_time" TIMESTAMPTZ,
    "base_weight" DOUBLE PRECISION NOT NULL DEFAULT 1,
    "last_reinforced_at" TIMESTAMPTZ,
    "half_life_seconds" INT NOT NULL DEFAULT 7200,
    "is_inactive" BOOL NOT NULL DEFAULT False,
    "embedding_ref" VARCHAR(64),
    "origin_kind" VARCHAR(16) NOT NULL,
    "origin_ref" VARCHAR(256),
    "origin_chat_key" VARCHAR(128),
    "anchor_msg_id" VARCHAR(64),
    "anchor_msg_id_start" VARCHAR(64),
    "anchor_msg_id_end" VARCHAR(64),
    "anchor_timestamp_start" INT,
    "anchor_timestamp_end" INT,
    "is_protected" BOOL NOT NULL DEFAULT False,
    "is_frozen" BOOL NOT NULL DEFAULT False,
    "manual_weight_delta" DOUBLE PRECISION NOT NULL DEFAULT 0,
    "last_manual_action" VARCHAR(32),
    "last_manual_action_at" TIMESTAMPTZ,
    "media_refs" JSONB NOT NULL,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_workspa_c473cf" ON "mem_paragraph" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_memory__eebb15" ON "mem_paragraph" ("memory_source");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_cogniti_7fb18b" ON "mem_paragraph" ("cognitive_type");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_knowled_c61e9b" ON "mem_paragraph" ("knowledge_type");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_event_t_6d82ff" ON "mem_paragraph" ("event_time");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_is_inac_a825c3" ON "mem_paragraph" ("is_inactive");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_embeddi_199e2f" ON "mem_paragraph" ("embedding_ref");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_origin__e69a3d" ON "mem_paragraph" ("origin_chat_key");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_anchor__511881" ON "mem_paragraph" ("anchor_msg_id");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_workspa_882570" ON "mem_paragraph" ("workspace_id", "cognitive_type");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_workspa_18bad1" ON "mem_paragraph" ("workspace_id", "memory_source");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_workspa_e0a429" ON "mem_paragraph" ("workspace_id", "is_inactive");
CREATE INDEX IF NOT EXISTS "idx_mem_paragra_workspa_af646b" ON "mem_paragraph" ("workspace_id", "event_time");
COMMENT ON COLUMN "mem_paragraph"."id" IS '主键 ID';
COMMENT ON COLUMN "mem_paragraph"."workspace_id" IS '工作区 ID（隔离边界）';
COMMENT ON COLUMN "mem_paragraph"."memory_source" IS '记忆来源（na/cc）';
COMMENT ON COLUMN "mem_paragraph"."cognitive_type" IS '认知类型（episodic/semantic）';
COMMENT ON COLUMN "mem_paragraph"."knowledge_type" IS '知识类型';
COMMENT ON COLUMN "mem_paragraph"."content" IS '记忆主体内容（第三人称叙述）';
COMMENT ON COLUMN "mem_paragraph"."summary" IS '简短摘要（用于快速展示）';
COMMENT ON COLUMN "mem_paragraph"."event_time" IS '事件发生时间（对 episodic 特别重要）';
COMMENT ON COLUMN "mem_paragraph"."base_weight" IS '基础权重';
COMMENT ON COLUMN "mem_paragraph"."last_reinforced_at" IS '最后一次强化时间';
COMMENT ON COLUMN "mem_paragraph"."half_life_seconds" IS '半衰期（秒）';
COMMENT ON COLUMN "mem_paragraph"."is_inactive" IS '是否已失活';
COMMENT ON COLUMN "mem_paragraph"."embedding_ref" IS 'Qdrant 向量 ID 引用';
COMMENT ON COLUMN "mem_paragraph"."origin_kind" IS '来源类型';
COMMENT ON COLUMN "mem_paragraph"."origin_ref" IS '来源引用（消息ID/任务ID等）';
COMMENT ON COLUMN "mem_paragraph"."origin_chat_key" IS '记忆产生的聊天频道标识';
COMMENT ON COLUMN "mem_paragraph"."anchor_msg_id" IS '锚定的单条原始消息 ID';
COMMENT ON COLUMN "mem_paragraph"."anchor_msg_id_start" IS '对话片段起始消息 ID';
COMMENT ON COLUMN "mem_paragraph"."anchor_msg_id_end" IS '对话片段结束消息 ID';
COMMENT ON COLUMN "mem_paragraph"."anchor_timestamp_start" IS '对话片段起始时间戳';
COMMENT ON COLUMN "mem_paragraph"."anchor_timestamp_end" IS '对话片段结束时间戳';
COMMENT ON COLUMN "mem_paragraph"."is_protected" IS '受保护，永不自动清理';
COMMENT ON COLUMN "mem_paragraph"."is_frozen" IS '冻结状态，暂停衰减';
COMMENT ON COLUMN "mem_paragraph"."manual_weight_delta" IS '手动调整的权重增量';
COMMENT ON COLUMN "mem_paragraph"."last_manual_action" IS '最后一次手动操作类型';
COMMENT ON COLUMN "mem_paragraph"."last_manual_action_at" IS '最后一次手动操作时间';
COMMENT ON COLUMN "mem_paragraph"."media_refs" IS '关联的媒体资源 ID 列表';
COMMENT ON COLUMN "mem_paragraph"."create_time" IS '创建时间';
COMMENT ON COLUMN "mem_paragraph"."update_time" IS '更新时间';
COMMENT ON TABLE "mem_paragraph" IS '记忆段落模型';
        CREATE TABLE IF NOT EXISTS "mem_reinforcement_log" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "target_type" VARCHAR(16) NOT NULL,
    "target_id" INT NOT NULL,
    "trigger_source" VARCHAR(16) NOT NULL,
    "trigger_ref" VARCHAR(256),
    "weight_before" DOUBLE PRECISION,
    "weight_after" DOUBLE PRECISION,
    "boost_amount" DOUBLE PRECISION NOT NULL DEFAULT 0.3,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_mem_reinfor_workspa_9dfb92" ON "mem_reinforcement_log" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_mem_reinfor_target__8f750a" ON "mem_reinforcement_log" ("target_id");
CREATE INDEX IF NOT EXISTS "idx_mem_reinfor_workspa_6e00f8" ON "mem_reinforcement_log" ("workspace_id", "target_type", "target_id");
CREATE INDEX IF NOT EXISTS "idx_mem_reinfor_workspa_8c4bad" ON "mem_reinforcement_log" ("workspace_id", "trigger_source");
CREATE INDEX IF NOT EXISTS "idx_mem_reinfor_workspa_746e2c" ON "mem_reinforcement_log" ("workspace_id", "create_time");
COMMENT ON COLUMN "mem_reinforcement_log"."id" IS '主键 ID';
COMMENT ON COLUMN "mem_reinforcement_log"."workspace_id" IS '工作区 ID';
COMMENT ON COLUMN "mem_reinforcement_log"."target_type" IS '目标类型';
COMMENT ON COLUMN "mem_reinforcement_log"."target_id" IS '目标 ID';
COMMENT ON COLUMN "mem_reinforcement_log"."trigger_source" IS '触发来源';
COMMENT ON COLUMN "mem_reinforcement_log"."trigger_ref" IS '触发引用（查询文本/任务ID等）';
COMMENT ON COLUMN "mem_reinforcement_log"."weight_before" IS '强化前权重';
COMMENT ON COLUMN "mem_reinforcement_log"."weight_after" IS '强化后权重';
COMMENT ON COLUMN "mem_reinforcement_log"."boost_amount" IS '强化增量';
COMMENT ON COLUMN "mem_reinforcement_log"."create_time" IS '创建时间';
COMMENT ON TABLE "mem_reinforcement_log" IS '记忆强化日志模型';
        CREATE TABLE IF NOT EXISTS "mem_relation" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "workspace_id" INT NOT NULL,
    "subject_entity_id" INT NOT NULL,
    "predicate" VARCHAR(64) NOT NULL,
    "object_entity_id" INT NOT NULL,
    "paragraph_id" INT,
    "memory_source" VARCHAR(8) NOT NULL,
    "cognitive_type" VARCHAR(16) NOT NULL,
    "base_weight" DOUBLE PRECISION NOT NULL DEFAULT 1,
    "last_reinforced_at" TIMESTAMPTZ,
    "half_life_seconds" INT NOT NULL DEFAULT 86400,
    "is_inactive" BOOL NOT NULL DEFAULT False,
    "create_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "update_time" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_mem_relatio_workspa_d4605a" ON "mem_relation" ("workspace_id");
CREATE INDEX IF NOT EXISTS "idx_mem_relatio_subject_39e52f" ON "mem_relation" ("subject_entity_id");
CREATE INDEX IF NOT EXISTS "idx_mem_relatio_predica_14b9fe" ON "mem_relation" ("predicate");
CREATE INDEX IF NOT EXISTS "idx_mem_relatio_object__5a9883" ON "mem_relation" ("object_entity_id");
CREATE INDEX IF NOT EXISTS "idx_mem_relatio_paragra_766d5c" ON "mem_relation" ("paragraph_id");
CREATE INDEX IF NOT EXISTS "idx_mem_relatio_is_inac_52db8c" ON "mem_relation" ("is_inactive");
CREATE INDEX IF NOT EXISTS "idx_mem_relatio_workspa_ca7d43" ON "mem_relation" ("workspace_id", "subject_entity_id");
CREATE INDEX IF NOT EXISTS "idx_mem_relatio_workspa_3125a6" ON "mem_relation" ("workspace_id", "object_entity_id");
CREATE INDEX IF NOT EXISTS "idx_mem_relatio_workspa_d389e6" ON "mem_relation" ("workspace_id", "predicate");
CREATE INDEX IF NOT EXISTS "idx_mem_relatio_subject_23ff3e" ON "mem_relation" ("subject_entity_id", "predicate", "object_entity_id");
COMMENT ON COLUMN "mem_relation"."id" IS '主键 ID';
COMMENT ON COLUMN "mem_relation"."workspace_id" IS '工作区 ID（隔离边界）';
COMMENT ON COLUMN "mem_relation"."subject_entity_id" IS '主体实体 ID';
COMMENT ON COLUMN "mem_relation"."predicate" IS '关系谓词';
COMMENT ON COLUMN "mem_relation"."object_entity_id" IS '客体实体 ID';
COMMENT ON COLUMN "mem_relation"."paragraph_id" IS '来源段落 ID（关系从哪段叙述提取）';
COMMENT ON COLUMN "mem_relation"."memory_source" IS '记忆来源（na/cc）';
COMMENT ON COLUMN "mem_relation"."cognitive_type" IS '认知类型（episodic/semantic）';
COMMENT ON COLUMN "mem_relation"."base_weight" IS '基础权重';
COMMENT ON COLUMN "mem_relation"."last_reinforced_at" IS '最后一次强化时间';
COMMENT ON COLUMN "mem_relation"."half_life_seconds" IS '半衰期（秒）';
COMMENT ON COLUMN "mem_relation"."is_inactive" IS '是否已失活';
COMMENT ON COLUMN "mem_relation"."create_time" IS '创建时间';
COMMENT ON COLUMN "mem_relation"."update_time" IS '更新时间';
COMMENT ON TABLE "mem_relation" IS '记忆关系模型';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "mem_reinforcement_log";
        DROP TABLE IF EXISTS "mem_relation";
        DROP TABLE IF EXISTS "mem_paragraph";
        DROP TABLE IF EXISTS "mem_entity";
        DROP TABLE IF EXISTS "mem_media_resource";"""


MODELS_STATE = (
    "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"
    "5gs4DNZzWPlHvV5+/y/l7RfH"
)
