from miose_toolkit_db import MioOrm, gen_postgresql_db_url, gen_sqlite_db_url

from nekro_agent.core.args import Args
from nekro_agent.core.os_env import OsEnv

from .config import config

if not Args.LOAD_TEST:
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
    orm: MioOrm = MioOrm(gen_sqlite_db_url(".temp/load_test.db"))
