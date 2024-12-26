from tortoise import Tortoise

from .args import Args
from .config import config
from .core_utils import gen_postgres_conn_str, gen_sqlite_db_url
from .logger import logger
from .os_env import OsEnv

DB_INITED: bool = False

db_url: str = ""


async def init_db():
    global DB_INITED

    if not Args.LOAD_TEST:
        if OsEnv.RUN_IN_DOCKER:
            db_url = gen_postgres_conn_str(
                host=OsEnv.POSTGRES_HOST,
                port=OsEnv.POSTGRES_PORT,
                user=OsEnv.POSTGRES_USER,
                password=OsEnv.POSTGRES_PASSWORD,
                db=OsEnv.POSTGRES_DATABASE,
            )
        else:
            db_url = gen_postgres_conn_str(
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT,
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD,
                db=config.POSTGRES_DATABASE,
            )
    else:
        db_url = gen_sqlite_db_url(".temp/load_test.db")

    if DB_INITED:
        return

    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["nekro_agent.models"]},  # 加载模型
    )
    # 生成数据库表
    try:
        await Tortoise.generate_schemas()
    except Exception:
        logger.error("初始化数据表失败，如果应用行为异常，请使用 `/nekro_db_reset -y` 重建数据表")
    DB_INITED = True
    logger.success("Database initialized")


async def reset_db():
    """重置数据库"""
    await Tortoise.close_connections()
    conn = Tortoise.get_connection("default")
    # 获取所有表名
    tables = await conn.execute_query("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")

    # 依次删除所有表
    for table in tables[1]:
        await conn.execute_query(f'DROP TABLE IF EXISTS "{table[0]}" CASCADE')

    await Tortoise.generate_schemas()
    logger.success("Database reset")
