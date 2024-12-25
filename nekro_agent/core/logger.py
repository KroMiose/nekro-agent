import sys
from pathlib import Path
from types import TracebackType

from loguru import logger

from .config import config
from .os_env import APP_LOG_DIR


# 捕获未处理的异常处理
def exception_handler(
    _type: BaseException,
    value: BaseException,
    traceback: TracebackType,  # noqa: ARG001
):
    try:
        raise value  # noqa: TRY301
    except Exception:
        logger.exception("Uncaught exception occurred")


sys.excepthook = exception_handler

logger.configure(
    handlers=[
        {
            "sink": sys.stdout,
            "format": (
                "<g>{time:MM-DD HH:mm:ss}</g> "
                "[<lvl>{level}</lvl>] "
                "<c><u>{name}</u></c> | "
                "<c>{function}:{line}</c>| "
                "{message}"
            ),
            "level": config.APP_LOG_LEVEL,
        },
        {
            "sink": Path(APP_LOG_DIR) / "app.log",
            "rotation": "100 MB",
            "retention": "10 days",
            "compression": "zip",
        },
    ],
)
