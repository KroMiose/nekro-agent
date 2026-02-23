from tortoise import Tortoise
from tzlocal import get_localzone

from nekro_agent.core.logger import get_sub_logger

from .args import Args
from .core_utils import gen_sqlite_db_url
from .tortoise_config import TORTOISE_ORM, resolve_db_url

logger = get_sub_logger("database")
DB_INITED: bool = False

db_url: str = ""


async def init_db():
    global DB_INITED

    if not Args.LOAD_TEST:
        db_url = resolve_db_url()
    else:
        db_url = gen_sqlite_db_url(".temp/load_test.db")

    if DB_INITED:
        return

    tortoise_config = dict(TORTOISE_ORM)
    tortoise_config["connections"] = {"default": db_url}
    await Tortoise.init(
        config=tortoise_config,
        timezone=str(get_localzone()),
    )
    DB_INITED = True
    logger.success("Nekro Agent 数据库初始化成功 =^_^=")
