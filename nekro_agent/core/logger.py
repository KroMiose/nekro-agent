import time

from miose_toolkit_logger import logger

from .config import config
from .os_env import APP_LOG_DIR

logger.set_log_level(config.APP_LOG_LEVEL)
logger.set_log_format(
    "<g>{time:MM-DD HH:mm:ss}</g> [<lvl>{level}</lvl>] <c><u>{name}</u></c> | <c>{function}:{line}</c>| {message}",
)

logger.set_log_output(f"{APP_LOG_DIR}/{time.strftime('%Y-%m-%d-%H-%M-%S')}.log", with_console=True)
logger.success("Logger initialized")
print("logger initialized")
