from miose_toolkit_db import MioOrm, gen_postgresql_db_url, gen_sqlite_db_url

from .args import Args
from .config import config
from .os_env import OsEnv

if not Args.LOAD_TEST:
    if OsEnv.RUN_IN_DOCKER:
        orm: MioOrm = MioOrm(
            gen_postgresql_db_url(
                host=OsEnv.POSTGRES_HOST,
                port=OsEnv.POSTGRES_PORT,
                user=OsEnv.POSTGRES_USER,
                password=OsEnv.POSTGRES_PASSWORD,
                database=OsEnv.POSTGRES_DATABASE,
            ),
        )
    else:
        orm: MioOrm = MioOrm(
            gen_postgresql_db_url(
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT,
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD,
                database=config.POSTGRES_DATABASE,
            ),
        )

else:
    orm: MioOrm = MioOrm(gen_sqlite_db_url(".temp/load_test.db"))
