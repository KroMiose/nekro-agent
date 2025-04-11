import contextlib
import os
import secrets
import subprocess
from pathlib import Path

from .core_utils import OsEnvTypes


class OsEnv:
    """系统变量"""

    """实例名称"""
    INSTANCE_NAME: str = OsEnvTypes.Str("INSTANCE_NAME", default="")

    """数据目录"""
    DATA_DIR: str = OsEnvTypes.Str("DATA_DIR", default="./data")  # `~/srv/nekro_agent` In Docker

    """Postgres 数据库配置"""
    POSTGRES_HOST: str = OsEnvTypes.Str("POSTGRES_HOST", default="localhost")
    POSTGRES_PORT: int = OsEnvTypes.Int("POSTGRES_PORT", default=5432)
    POSTGRES_USER: str = OsEnvTypes.Str("POSTGRES_USER", default="nekro_agent")
    POSTGRES_PASSWORD: str = OsEnvTypes.Str("POSTGRES_PASSWORD", default="nekro_agent")
    POSTGRES_DATABASE: str = OsEnvTypes.Str("POSTGRES_DATABASE", default="nekro_agent")

    """Qdrant 数据库配置"""
    QDRANT_URL: str = OsEnvTypes.Str("QDRANT_URL", default="http://localhost:6333")
    QDRANT_API_KEY: str = OsEnvTypes.Str("QDRANT_API_KEY", default="")
    """JWT 配置"""
    JWT_SECRET_KEY: str = OsEnvTypes.Str("JWT_SECRET_KEY", default=f"secret:{secrets.token_urlsafe(32)}")
    JWT_REFRESH_SECRET_KEY: str = OsEnvTypes.Str("JWT_REFRESH_SECRET_KEY", default=f"refresh:{secrets.token_urlsafe(32)}")
    SUPER_ACCESS_KEY: str = OsEnvTypes.Str("SUPER_ACCESS_KEY", default=lambda: os.urandom(32).hex())
    ACCESS_TOKEN_EXPIRE_DAYS: int = OsEnvTypes.Int("ACCESS_TOKEN_EXPIRE_DAYS", default=7)
    ENCRYPT_ALGORITHM: str = OsEnvTypes.Str("ENCRYPT_ALGORITHM", default="HS256")

    """RPC 配置"""
    RPC_SECRET_KEY: str = OsEnvTypes.Str("RPC_SECRET_KEY", default=f"rpc:{secrets.token_urlsafe(32)}")

    """Webhook 配置"""
    WEBHOOK_SECRET_KEY: str = OsEnvTypes.Str("WEBHOOK_SECRET_KEY", default=f"webhook:{secrets.token_urlsafe(32)}")

    """其他配置"""
    RUN_IN_DOCKER: bool = OsEnvTypes.Bool("RUN_IN_DOCKER")

    """暴露端口"""
    EXPOSE_PORT: int = OsEnvTypes.Int("EXPOSE_PORT", default=8021)

    """前端资源目录"""
    STATIC_DIR: str = OsEnvTypes.Str("STATIC_DIR", default="./static")

    """WebUI 管理员密码"""
    ADMIN_PASSWORD: str = OsEnvTypes.Str("ADMIN_PASSWORD", default="")

    """Nekro Cloud API"""
    NEKRO_CLOUD_API_BASE_URL: str = OsEnvTypes.Str("NEKRO_CLOUD_API_BASE_URL", default="https://community.nekro.ai")
    # NEKRO_CLOUD_API_BASE_URL: str = OsEnvTypes.Str("NEKRO_CLOUD_API_BASE_URL", default="http://localhost:8787")


USER_UPLOAD_DIR: str = OsEnv.DATA_DIR + "/uploads"
SANDBOX_SHARED_HOST_DIR: str = OsEnv.DATA_DIR + "/sandboxes"
PROMPT_LOG_DIR: str = OsEnv.DATA_DIR + "/logs/prompts"
APP_LOG_DIR: str = OsEnv.DATA_DIR + "/logs/app"
BUILTIN_PLUGIN_DIR: str = "plugins/builtin"
WORKDIR_PLUGIN_DIR: str = OsEnv.DATA_DIR + "/plugins/workdir"
PACKAGES_DIR: str = OsEnv.DATA_DIR + "/plugins/packages"
NAPCAT_TEMPFILE_DIR: str = OsEnv.DATA_DIR + "/napcat_data/QQ/NapCat/temp"
NAPCAT_ONEBOT_ADAPTER_DIR: str = OsEnv.DATA_DIR + "/napcat_data/napcat"
EXT_WORKDIR: str = OsEnv.DATA_DIR + "/ext_workdir"
ONEBOT_ACCESS_TOKEN: str = os.getenv("ONEBOT_ACCESS_TOKEN", "")


# 设置上传目录及其子目录权限
with contextlib.suppress(Exception):
    Path(USER_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    subprocess.run(["chmod", "-R", "755", USER_UPLOAD_DIR], check=True)
    print(f"Set permission of {USER_UPLOAD_DIR} to 755")
