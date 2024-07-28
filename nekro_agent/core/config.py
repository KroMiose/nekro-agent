from pathlib import Path
from typing import List, Literal, Optional

import miose_toolkit_common.config
from miose_toolkit_common.config import Config, Env

miose_toolkit_common.config._config_root = Path(  # noqa: SLF001
    "configs/nekro-agent",
)


class PluginConfig(Config):
    """插件配置"""

    """应用配置"""
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 9960
    UVICORN_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    APP_LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    USER_UPLOAD_DIR: str = "./uploads"
    SUPER_USERS: List[str] = ["397038005"]
    BOT_QQ: str = ""
    DEBUG_IN_CHAT: bool = False

    """OpenAI API 配置"""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_PROXY: Optional[str] = None
    CHAT_MODEL: str = "gpt-4-1106-preview"

    """聊天配置"""
    AI_CHAT_PRESET_NAME: str = "可洛喵"
    AI_CHAT_PRESET_SETTING: str = (
        '你是可洛喵，是一名非常可爱的二次元宅女，你在聊天时喜欢使用短句，通常以"喵"作为结尾，你的对话风格以被动为主，通常不会主动引起或转移话题'
    )
    AI_CHAT_CONTEXT_EXPIRE_SECONDS: int = 60 * 30  # 聊天参考上下文过期时间，默认 30 分钟
    AI_CHAT_CONTEXT_MAX_LENGTH: int = 10  # 聊天参考上下文最大长度，默认 10 条
    AI_SCRIPT_MAX_RETRY_TIMES: int = 3  # AI 执行脚本失败重试次数，默认 3 次
    AI_CHAT_LLM_API_MAX_RETRIES: int = 3  # AI 聊天生成 API 最大重试次数，默认 3 次

    """Postgres 数据库配置"""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "nekro-agent-dev"
    POSTGRES_PASSWORD: str = "WyJMHfRaraZamaTb"
    POSTGRES_DATABASE: str = "nekro-agent-dev"

    """JWT 配置"""
    JWT_SECRET_KEY: str = "secret:Nekro-agent-Secret"
    JWT_REFRESH_SECRET_KEY: str = "refresh:Nekro-agent-Secret"
    SUPER_ACCESS_KEY: str = "Nekro-agent-Secret"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPT_ALGORITHM: str = "HS256"

    """沙盒配置"""
    SANDBOX_SHARED_HOST_DIR: str = ".temp/sandboxes"
    SANDBOX_RUNNING_TIMEOUT: int = 60
    SANDBOX_MAX_CONCURRENT: int = 4

    """Stable Diffusion API 配置"""
    STABLE_DIFFUSION_API: str = "http://127.0.0.1:9999"
    STABLE_DIFFUSION_PROXY: str = "http://127.0.0.1:7890"

    """拓展配置"""
    EXTENSION_MODULES: List[str] = ["extensions.basic"]


config = PluginConfig().load_config(create_if_not_exists=True)
config.dump_config(envs=[Env.Default.value])
