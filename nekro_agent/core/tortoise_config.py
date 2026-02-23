from __future__ import annotations

from tzlocal import get_localzone

from nekro_agent.core.config import config
from nekro_agent.core.os_env import OsEnv

from .core_utils import gen_postgres_conn_str


def resolve_db_url() -> str:
    if OsEnv.RUN_IN_DOCKER or (OsEnv.USE_ENV_DATABASE.lower() == "true"):
        return gen_postgres_conn_str(
            host=OsEnv.POSTGRES_HOST,
            port=OsEnv.POSTGRES_PORT,
            user=OsEnv.POSTGRES_USER,
            password=OsEnv.POSTGRES_PASSWORD,
            db=OsEnv.POSTGRES_DATABASE,
        )
    return gen_postgres_conn_str(
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        user=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
        db=config.POSTGRES_DATABASE,
    )


TORTOISE_ORM = {
    "connections": {"default": resolve_db_url()},
    "apps": {
        "models": {
            "models": ["nekro_agent.models", "aerich.models"],
            "default_connection": "default",
        },
    },
    "timezone": str(get_localzone()),
}
