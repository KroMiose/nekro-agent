import json
import sys
from asyncio import Queue
from collections import deque
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from loguru import logger

from .config import config
from .os_env import APP_LOG_DIR

# 内存中保存最近的日志记录
log_records = deque(maxlen=1000)
# 订阅者队列
subscribers: List[Queue] = []
# 记录所有出现过的日志来源
log_sources: Set[str] = set()


def format_log_entry(record: Dict) -> Dict:
    """格式化日志条目"""
    # 记录日志来源
    log_sources.add(record["name"])

    extra = record.get("extra") or {}
    return {
        "timestamp": datetime.fromtimestamp(record["time"].timestamp()).strftime("%Y-%m-%d %H:%M:%S"),
        "level": record["level"].name,
        "message": record["message"],
        "source": record["name"],
        "subsystem": extra.get("subsystem"),
        "plugin_key": extra.get("plugin_key"),
        "function": record["function"],
        "line": record["line"],
    }


class LogInterceptHandler:
    """日志拦截处理器"""

    async def __call__(self, message):
        """处理日志消息"""
        record = message.record
        log_entry = format_log_entry(record)
        log_records.append(log_entry)
        log_json = json.dumps(log_entry)
        for queue in subscribers:
            await queue.put(f"{log_json}\n\n")


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

# 立即配置日志处理器
Path(APP_LOG_DIR).mkdir(parents=True, exist_ok=True)
log_handlers = [
    {
        "sink": LogInterceptHandler(),
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
        "format": (
            "<g>{time:MM-DD HH:mm:ss}</g> "
            "[<lvl>{level}</lvl>] "
            "<c><u>{name}</u></c> | "
            "<c>{function}:{line}</c>| "
            "{message}"
        ),
        "level": config.APP_LOG_LEVEL,
        "rotation": "100 MB",
        "retention": "10 days",
        "compression": "zip",
    },
]

logger.configure(handlers=log_handlers) # type: ignore


async def get_log_records(
    page: int = 1,
    page_size: int = 100,
    source: Optional[str] = None,
    count_only: bool = False,
    subsystem: Optional[str] = None,
    plugin_key: Optional[str] = None,
) -> List[Dict] | int:
    """获取历史日志记录，默认返回最新的100条日志

    Args:
        page: 页码，从1开始
        page_size: 每页记录数
        source: 日志来源过滤
        count_only: 是否只返回计数
        subsystem: 子系统过滤（来自 logger.bind(subsystem=...)）
        plugin_key: 插件过滤（来自 logger.bind(plugin_key=...)）

    Returns:
        返回指定页的日志记录，按时间从新到旧排序
    """
    # 1. 转换 deque 到列表并过滤（此时是从旧到新的顺序）
    filtered_logs = [
        log
        for log in log_records
        if (not source or log["source"] == source) and (not subsystem or log.get("subsystem") == subsystem)
        and (not plugin_key or log.get("plugin_key") == plugin_key)
    ]
    # 如果只需要计数
    if count_only:
        return len(filtered_logs)
    # 2. 反转列表使其变成从新到旧的顺序
    filtered_logs = filtered_logs[::-1]

    # 分页（此时分页基于从新到旧排序的列表）
    start = (page - 1) * page_size
    end = start + page_size if page_size > 0 else None
    return filtered_logs[start:end][::-1]


async def get_log_sources() -> List[str]:
    """获取所有日志来源"""
    return sorted(log_sources)


async def subscribe_logs() -> AsyncGenerator[str, None]:
    """订阅日志流"""
    queue: Queue = Queue()
    subscribers.append(queue)
    try:
        while True:
            message = await queue.get()
            yield message
    finally:
        subscribers.remove(queue)


def get_sub_logger(subsystem: str, log_name: Optional[str] = None, **extra: Any):
    """获取带子系统标记的 logger（用于前端过滤）。

    注意：
    - 不会分流到独立日志文件（避免产生过多碎片日志）
    - 仅通过 record.extra 打标，供内存日志/接口过滤
    """
    subsystem = str(subsystem).strip()
    if not subsystem:
        return logger
    name = (log_name or subsystem).strip() or subsystem
    bound = logger.bind(subsystem=subsystem, **extra)

    def patch_record(record: Any) -> None:
        record["name"] = name

    return bound.patch(patch_record)
