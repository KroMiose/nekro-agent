"""
SSE 客户端SDK 工具函数
======================

提供SSE SDK所需的各种工具函数和装饰器。
"""

import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

import aiohttp
from loguru import logger

# 添加返回类型变量T用于泛型函数
T = TypeVar("T")


# 添加重试装饰器
async def with_retry(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    retry_count: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 5.0,
    backoff_factor: float = 2.0,
    retry_exceptions: tuple = (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ConnectionError,
    ),
    **kwargs: Any,
) -> T:
    """网络请求重试装饰器

    Args:
        func: 异步函数
        retry_count: 最大重试次数
        initial_delay: 初始延迟时间(秒)
        max_delay: 最大延迟时间(秒)
        backoff_factor: 退避系数，每次重试延迟时间为上次的backoff_factor倍
        retry_exceptions: 需要重试的异常类型

    Returns:
        原函数的返回值
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(retry_count + 1):
        try:
            return await func(*args, **kwargs)
        except retry_exceptions as e:
            last_exception = e
            if attempt == retry_count:
                break

            # 记录重试信息
            logger.warning(f"请求失败，正在进行第{attempt+1}次重试: {e!s}")

            # 计算下次重试等待时间（指数退避）
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)

    # 所有重试都失败了，抛出最后一个异常
    if last_exception:
        raise last_exception

    # 理论上不会到这里，但为了类型安全
    raise RuntimeError("重试失败且没有异常")


def retry_decorator(
    retry_count: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 5.0,
    backoff_factor: float = 2.0,
    retry_exceptions: tuple = (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ConnectionError,
    ),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """可配置的重试装饰器

    Args:
        retry_count: 最大重试次数
        initial_delay: 初始延迟时间(秒)
        max_delay: 最大延迟时间(秒)
        backoff_factor: 退避系数，每次重试延迟时间为上次的backoff_factor倍
        retry_exceptions: 需要重试的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await with_retry(
                func,
                *args,
                retry_count=retry_count,
                initial_delay=initial_delay,
                max_delay=max_delay,
                backoff_factor=backoff_factor,
                retry_exceptions=retry_exceptions,
                **kwargs,
            )

        return wrapper

    return decorator
