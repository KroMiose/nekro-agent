from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    """为 adapter_instance_session.instance_id 加唯一约束。

    该表语义上是"每个适配器实例一条会话"，但此前只有普通索引，配合
    get_or_none -> create 的读后写，并发绑定/续期会插出多条记录，
    之后取到哪条不确定，凭据与同步游标随之漂移。

    加约束前先归并历史重复行：每个 instance_id 只保留一条，优先级为
    有凭据 > 更新时间更新 > id 更大，确保留下的是最可能仍然可用的那条。
    """
    return """
        DELETE FROM "adapter_instance_session"
         WHERE "id" NOT IN (
               SELECT DISTINCT ON ("instance_id") "id"
                 FROM "adapter_instance_session"
                ORDER BY "instance_id",
                         ("credentials_json" <> '') DESC,
                         "update_time" DESC,
                         "id" DESC
         );
        DROP INDEX IF EXISTS "idx_adapter_ins_instanc_4cbd6e";
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_adapter_ins_instanc_4cbd6e" ON "adapter_instance_session" ("instance_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_adapter_ins_instanc_4cbd6e";
        CREATE INDEX IF NOT EXISTS "idx_adapter_ins_instanc_4cbd6e" ON "adapter_instance_session" ("instance_id");
    """
