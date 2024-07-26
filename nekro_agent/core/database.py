from miose_toolkit_db import MioOrm, gen_postgresql_db_url, gen_sqlite_db_url

from nekro_agent.core.args import Args

from .config import config

if not Args.LOAD_TEST:
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
