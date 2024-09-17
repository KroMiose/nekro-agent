import contextlib
import subprocess
from pathlib import Path

from .utils import OsEnvTypes


class OsEnv:
    """系统变量"""

    """数据目录"""
    DATA_DIR: str = OsEnvTypes.Str("DATA_DIR", default="./data")  # `~/srv/nekro_agent` In Docker

    """Postgres 数据库配置"""
    POSTGRES_HOST: str = OsEnvTypes.Str("POSTGRES_HOST", default="localhost")
    POSTGRES_PORT: int = OsEnvTypes.Int("POSTGRES_PORT", default=5432)
    POSTGRES_USER: str = OsEnvTypes.Str("POSTGRES_USER", default="nekro_agent")
    POSTGRES_PASSWORD: str = OsEnvTypes.Str("POSTGRES_PASSWORD", default="nekro_agent")
    POSTGRES_DATABASE: str = OsEnvTypes.Str("POSTGRES_DATABASE", default="nekro_agent")

    """JWT 配置"""
    JWT_SECRET_KEY: str = OsEnvTypes.Str("JWT_SECRET_KEY", default="secret:Nekro-agent-Secret")
    JWT_REFRESH_SECRET_KEY: str = OsEnvTypes.Str("JWT_REFRESH_SECRET_KEY", default="refresh:Nekro-agent-Secret")
    SUPER_ACCESS_KEY: str = OsEnvTypes.Str("SUPER_ACCESS_KEY", default="Nekro-agent-Secret")
    ACCESS_TOKEN_EXPIRE_DAYS: int = OsEnvTypes.Int("ACCESS_TOKEN_EXPIRE_DAYS", default=7)
    ENCRYPT_ALGORITHM: str = OsEnvTypes.Str("ENCRYPT_ALGORITHM", default="HS256")

    """其他配置"""
    RUN_IN_DOCKER: bool = OsEnvTypes.Bool("RUN_IN_DOCKER")


USER_UPLOAD_DIR: str = OsEnv.DATA_DIR + "/uploads"
SANDBOX_SHARED_HOST_DIR: str = OsEnv.DATA_DIR + "/sandboxes"
PROMPT_LOG_DIR: str = OsEnv.DATA_DIR + "/logs/prompts"
APP_LOG_DIR: str = OsEnv.DATA_DIR + "/logs/app"


# 设置上传目录及其子目录权限
with contextlib.suppress(Exception):
    Path(USER_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    subprocess.run(["chmod", "-R", "755", USER_UPLOAD_DIR], check=True)
    print(f"Set permission of {USER_UPLOAD_DIR} to 755")
