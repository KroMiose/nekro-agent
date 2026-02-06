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
    DATA_DIR: str = OsEnvTypes.Str("DATA_DIR", default="./data/nekro_agent")  # `~/srv/nekro_agent` In Docker

    """Postgres 数据库配置"""
    USE_ENV_DATABASE: str = OsEnvTypes.Str("USE_ENV_DATABASE", default="false")
    POSTGRES_HOST: str = OsEnvTypes.Str("POSTGRES_HOST", default="localhost")
    POSTGRES_PORT: int = OsEnvTypes.Int("POSTGRES_PORT", default=5432)
    POSTGRES_USER: str = OsEnvTypes.Str("POSTGRES_USER", default="nekro_agent")
    POSTGRES_PASSWORD: str = OsEnvTypes.Str("POSTGRES_PASSWORD", default="nekro_agent")
    POSTGRES_DATABASE: str = OsEnvTypes.Str("POSTGRES_DATABASE", default="nekro_agent")

    """Qdrant 数据库配置"""
    USE_ENV_QDRANT: str = OsEnvTypes.Str("USE_ENV_QDRANT", default="false")
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

    """OPENAPI 配置"""
    ENABLE_OPENAPI_DOCS: bool = OsEnvTypes.Bool("ENABLE_OPENAPI_DOCS")


APP_SYSTEM_DIR: str = OsEnv.DATA_DIR + "/system"  # 系统目录
USER_UPLOAD_DIR: str = OsEnv.DATA_DIR + "/uploads"  # 用户资源上传目录
SANDBOX_SHARED_HOST_DIR: str = OsEnv.DATA_DIR + "/sandboxes"  # 沙盒共享目录
SANDBOX_PIP_CACHE_DIR: str = OsEnv.DATA_DIR + "/sandboxes/.pip_cache"  # 沙盒动态 PIP 缓存目录
SANDBOX_PACKAGE_DIR: str = OsEnv.DATA_DIR + "/sandboxes/.packages"  # 沙盒动态包目录
PLUGIN_DYNAMIC_PACKAGE_DIR: str = OsEnv.DATA_DIR + "/plugins/.dynamic_packages"  # 插件动态包目录
PROMPT_LOG_DIR: str = OsEnv.DATA_DIR + "/logs/prompts"  # 提示词日志目录
PROMPT_ERROR_LOG_DIR: str = OsEnv.DATA_DIR + "/logs/prompts_error"  # 提示词错误日志目录
APP_LOG_DIR: str = OsEnv.DATA_DIR + "/logs/app"  # 应用日志目录
BUILTIN_PLUGIN_DIR: str = "plugins/builtin"  # 内置插件目录
WORKDIR_PLUGIN_DIR: str = OsEnv.DATA_DIR + "/plugins/workdir"  # 本地插件目录
PACKAGES_DIR: str = OsEnv.DATA_DIR + "/plugins/packages"  # 云端插件目录
NAPCAT_TEMPFILE_DIR: str = OsEnv.DATA_DIR + "/napcat_data/QQ/NapCat/temp"  # NapCat 临时文件目录
NAPCAT_ONEBOT_ADAPTER_DIR: str = OsEnv.DATA_DIR + "/napcat_data/napcat"  # NapCat OneBot 适配器目录
WALLPAPER_DIR: str = OsEnv.DATA_DIR + "/wallpapers"  # 壁纸目录
ONEBOT_ACCESS_TOKEN: str = os.getenv("ONEBOT_ACCESS_TOKEN", "")

# =============================================================================
# Timer / Calendar data paths (under DATA_DIR)
# =============================================================================
TIMER_SYSTEM_DIR: str = APP_SYSTEM_DIR + "/timer"
TIMER_ONE_SHOT_PERSIST_PATH: str = TIMER_SYSTEM_DIR + "/one_shot_timers.json"

CALENDAR_SYSTEM_DIR: str = APP_SYSTEM_DIR + "/calendar"
CALENDAR_CN_HOLIDAY_DIR: str = CALENDAR_SYSTEM_DIR + "/cn_holidays"


# 设置上传目录及其子目录权限
with contextlib.suppress(Exception):
    Path(USER_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    subprocess.run(["chmod", "-R", "755", USER_UPLOAD_DIR], check=True)
    print(f"Set permission of {USER_UPLOAD_DIR} to 755")
