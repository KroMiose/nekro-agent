from __future__ import annotations

from pathlib import Path

from aerich import Command
from tortoise import Tortoise

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.core.tortoise_config import TORTOISE_ORM

logger = get_sub_logger("database")


async def _ensure_aerich_table(conn) -> None:
    dialect = conn.capabilities.dialect
    if dialect == "postgres":
        await conn.execute_script(
            """
            CREATE TABLE IF NOT EXISTS "aerich" (
                "id" SERIAL NOT NULL PRIMARY KEY,
                "version" VARCHAR(255) NOT NULL,
                "app" VARCHAR(100) NOT NULL,
                "content" JSONB NOT NULL
            );
            """
        )
    elif dialect == "sqlite":
        await conn.execute_script(
            """
            CREATE TABLE IF NOT EXISTS "aerich" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                "version" VARCHAR(255) NOT NULL,
                "app" VARCHAR(100) NOT NULL,
                "content" JSON NOT NULL
            );
            """
        )


async def run_db_migrations(auto: bool = True, initialized: bool = True) -> None:
    if auto and not OsEnv.AUTO_DB_MIGRATE:
        return

    if not initialized:
        await Tortoise.init(config=TORTOISE_ORM)

    conn = Tortoise.get_connection("default")
    migrations_dir = Path("migrations/models")
    migrations_dir.mkdir(parents=True, exist_ok=True)
    has_migration_files = any(migrations_dir.iterdir())

    if not has_migration_files:
        logger.warning("未检测到迁移文件，跳过自动迁移")
        if not initialized:
            await Tortoise.close_connections()
        return

    command = Command(TORTOISE_ORM, app="models", location="./migrations")

    # 自动修复旧格式迁移文件（aerich 0.6+ 要求 MODELS_STATE 字段）
    try:
        fixed = await command.fix_migrations()
        if fixed:
            logger.info(f"已修复旧格式迁移文件: {fixed}")
    except Exception as e:
        logger.debug(f"fix_migrations 跳过: {e}")

    await command.init()
    await _ensure_aerich_table(conn)
    await command.upgrade()

    if not initialized:
        await Tortoise.close_connections()
