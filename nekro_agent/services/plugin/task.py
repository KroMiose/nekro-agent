"""异步任务框架

提供统一的异步任务暂停/恢复机制，支持多种触发方式恢复任务。

核心组件：
- TaskSignal: 任务信号类型枚举
- TaskCtl: 任务控制信号
- AsyncTaskHandle: 异步任务句柄，提供 wait/notify 能力
- TaskRunner: 任务运行器，管理任务生命周期
- task: 便捷 API 入口
"""

from __future__ import annotations

import asyncio
import contextlib
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    TypeVar,
)

from pydantic import BaseModel, Field

from nekro_agent.core import logger

if TYPE_CHECKING:
    from nekro_agent.services.plugin.base import NekroPlugin


class TaskSignal(str, Enum):
    """任务信号类型"""

    PROGRESS = "progress"  # 进度更新
    SUCCESS = "success"  # 成功完成
    FAIL = "fail"  # 失败
    CANCEL = "cancel"  # 取消


class TaskCtl(BaseModel):
    """任务控制信号

    不可变对象，用于任务函数通过 yield 报告状态。
    """

    model_config = {"frozen": True}

    signal: TaskSignal
    message: str
    data: Optional[Any] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)

    @classmethod
    def report_progress(cls, message: str, percent: int = 0) -> "TaskCtl":
        """报告进度

        Args:
            message: 进度消息
            percent: 进度百分比 (0-100)
        """
        return cls(signal=TaskSignal.PROGRESS, message=message, progress=percent)

    @classmethod
    def success(cls, message: str = "完成", data: Any = None) -> "TaskCtl":
        """任务成功完成

        Args:
            message: 完成消息
            data: 任务结果数据
        """
        return cls(signal=TaskSignal.SUCCESS, message=message, data=data)

    @classmethod
    def fail(cls, message: str, error: Optional[Exception] = None) -> "TaskCtl":
        """任务失败

        Args:
            message: 错误消息
            error: 异常对象
        """
        return cls(signal=TaskSignal.FAIL, message=message, data=error)

    @classmethod
    def cancel(cls, message: str = "已取消") -> "TaskCtl":
        """任务取消

        Args:
            message: 取消消息
        """
        return cls(signal=TaskSignal.CANCEL, message=message)

    @property
    def is_terminal(self) -> bool:
        """是否为终态"""
        return self.signal in (TaskSignal.SUCCESS, TaskSignal.FAIL, TaskSignal.CANCEL)


class AsyncTaskHandle:
    """异步任务句柄

    提供任务内部使用的等待和通知能力。

    注意：与 AgentCtx 完全不同：
    - AgentCtx: Agent 执行上下文，包含会话、用户、文件系统等
    - AsyncTaskHandle: 异步任务控制句柄，仅用于 wait/notify

    Example:
        ```python
        async def my_task(handle: AsyncTaskHandle, prompt: str):
            yield TaskCtl.report_progress("等待审批")
            approved = await handle.wait("approval", timeout=3600)
            if approved:
                yield TaskCtl.success("已批准")
        ```
    """

    def __init__(self, task_id: str, chat_key: str, plugin: "NekroPlugin"):
        self.task_id = task_id
        self.chat_key = chat_key
        self.plugin = plugin
        self._waiters: Dict[str, asyncio.Future] = {}
        self._cancelled = False

    async def wait(self, key: str, timeout: Optional[float] = None) -> Any:
        """等待外部信号

        任务在此处暂停，直到外部调用 notify() 恢复。

        Args:
            key: 等待键（用于区分多个等待点）
            timeout: 超时秒数（None 表示永不超时）

        Returns:
            外部传入的数据

        Raises:
            asyncio.TimeoutError: 超时
            asyncio.CancelledError: 任务被取消
        """
        if self._cancelled:
            raise asyncio.CancelledError("Task has been cancelled")

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._waiters[key] = future

        try:
            if timeout:
                return await asyncio.wait_for(future, timeout)
            return await future
        finally:
            self._waiters.pop(key, None)

    def notify(self, key: str, data: Any = None) -> bool:
        """通知等待点恢复

        Args:
            key: 等待键
            data: 传递给等待方的数据

        Returns:
            是否成功通知（等待点存在且未完成）
        """
        future = self._waiters.get(key)
        if future and not future.done():
            future.set_result(data)
            return True
        return False

    def cancel_wait(self, key: str) -> bool:
        """取消特定等待点

        Args:
            key: 等待键

        Returns:
            是否成功取消
        """
        future = self._waiters.get(key)
        if future and not future.done():
            future.cancel()
            return True
        return False

    def cancel_all(self) -> int:
        """取消所有等待点

        Returns:
            取消的等待点数量
        """
        self._cancelled = True
        count = 0
        for future in self._waiters.values():
            if not future.done():
                future.cancel()
                count += 1
        return count

    async def notify_agent(self, message: str, trigger: bool = True) -> None:
        """通知主 Agent

        向主 Agent 推送系统消息。

        Args:
            message: 消息内容
            trigger: 是否触发 Agent 响应
        """
        from nekro_agent.services.message_service import message_service

        await message_service.push_system_message(
            chat_key=self.chat_key,
            agent_messages=message,
            trigger_agent=trigger,
        )

    @property
    def is_cancelled(self) -> bool:
        """任务是否已取消"""
        return self._cancelled


T = TypeVar("T")
AsyncTaskFunc = Callable[
    ...,
    AsyncGenerator["TaskCtl", None] | Coroutine[Any, Any, None],
]


class TaskRunner:
    """任务运行器

    管理所有异步任务的生命周期。全局单例模式。
    """

    _instance: Optional["TaskRunner"] = None

    def __new__(cls) -> "TaskRunner":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()  # noqa: SLF001
        return cls._instance

    def _initialize(self) -> None:
        self._handles: Dict[str, AsyncTaskHandle] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._states: Dict[str, TaskCtl] = {}
        self._task_funcs: Dict[str, AsyncTaskFunc] = {}

    def register_task_type(self, task_type: str, func: AsyncTaskFunc) -> None:
        """注册任务类型

        Args:
            task_type: 任务类型标识
            func: 任务函数
        """
        self._task_funcs[task_type] = func
        logger.debug(f"注册异步任务类型: {task_type}")

    async def start(
        self,
        task_type: str,
        task_id: str,
        chat_key: str,
        plugin: "NekroPlugin",
        *args: Any,
        **kwargs: Any,
    ) -> AsyncTaskHandle:
        """启动任务

        Args:
            task_type: 任务类型
            task_id: 任务 ID
            chat_key: 会话 Key
            plugin: 插件实例
            *args: 传递给任务函数的位置参数
            **kwargs: 传递给任务函数的关键字参数

        Returns:
            任务句柄

        Raises:
            ValueError: 任务类型未注册或任务已存在
        """
        key = f"{task_type}:{task_id}"

        if key in self._tasks:
            existing_task = self._tasks[key]
            if not existing_task.done():
                raise ValueError(f"任务 {key} 已在运行中")
            # 清理已完成的任务
            del self._tasks[key]
            self._handles.pop(key, None)
            self._states.pop(key, None)

        func = self._task_funcs.get(task_type)
        if not func:
            raise ValueError(f"未注册的任务类型: {task_type}")

        handle = AsyncTaskHandle(task_id, chat_key, plugin)
        self._handles[key] = handle

        # 创建并启动任务
        task = asyncio.create_task(self._execute(key, func, handle, *args, **kwargs))
        self._tasks[key] = task

        logger.info(f"启动异步任务: {key}")
        return handle

    def get_handle(self, task_type: str, task_id: str) -> Optional[AsyncTaskHandle]:
        """获取任务句柄

        Args:
            task_type: 任务类型
            task_id: 任务 ID

        Returns:
            任务句柄，不存在则返回 None
        """
        return self._handles.get(f"{task_type}:{task_id}")

    def get_state(self, task_type: str, task_id: str) -> Optional[TaskCtl]:
        """获取任务最新状态

        Args:
            task_type: 任务类型
            task_id: 任务 ID

        Returns:
            任务最新状态，不存在则返回 None
        """
        return self._states.get(f"{task_type}:{task_id}")

    def is_running(self, task_type: str, task_id: str) -> bool:
        """检查任务是否正在运行

        Args:
            task_type: 任务类型
            task_id: 任务 ID

        Returns:
            是否正在运行
        """
        key = f"{task_type}:{task_id}"
        task = self._tasks.get(key)
        return task is not None and not task.done()

    async def cancel(self, task_type: str, task_id: str) -> bool:
        """取消任务

        Args:
            task_type: 任务类型
            task_id: 任务 ID

        Returns:
            是否成功取消
        """
        key = f"{task_type}:{task_id}"
        task = self._tasks.get(key)
        handle = self._handles.get(key)

        if not task or task.done():
            return False

        # 先取消所有等待点
        if handle:
            handle.cancel_all()

        # 然后取消任务
        task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await task

        self._states[key] = TaskCtl.cancel("任务被取消")
        logger.info(f"取消异步任务: {key}")
        return True

    async def stop_all(self) -> int:
        """停止所有任务

        Returns:
            停止的任务数量
        """
        count = 0
        for key in list(self._tasks.keys()):
            task_type, task_id = key.split(":", 1)
            if await self.cancel(task_type, task_id):
                count += 1
        return count

    def get_running_tasks(self) -> List[str]:
        """获取所有正在运行的任务 Key

        Returns:
            任务 Key 列表
        """
        return [key for key, task in self._tasks.items() if not task.done()]

    async def _execute(
        self,
        key: str,
        func: AsyncTaskFunc,
        handle: AsyncTaskHandle,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """执行任务

        Args:
            key: 任务 Key
            func: 任务函数
            handle: 任务句柄
            *args: 位置参数
            **kwargs: 关键字参数
        """
        try:
            # 调用任务函数
            result = func(handle, *args, **kwargs)

            # 使用 collections.abc 正确检查类型
            from collections.abc import AsyncGenerator as ABCAsyncGenerator

            if isinstance(result, ABCAsyncGenerator):
                # 异步生成器模式
                async for ctl in result:
                    self._states[key] = ctl
                    if ctl.is_terminal:
                        break
            else:
                # 普通协程模式
                await result
                self._states[key] = TaskCtl.success("完成")

        except asyncio.CancelledError:
            self._states[key] = TaskCtl.cancel("任务被取消")
            logger.info(f"异步任务被取消: {key}")
        except Exception as e:
            self._states[key] = TaskCtl.fail(str(e), error=e)
            logger.exception(f"异步任务执行异常: {key}")
        finally:
            # 清理 handle（保留 state 用于查询）
            self._handles.pop(key, None)
            self._tasks.pop(key, None)


class TaskAPI:
    """任务便捷 API

    提供静态方法访问 TaskRunner 功能。

    Example:
        ```python
        # 启动任务
        handle = await task.start("video_gen", "V001", chat_key, plugin, prompt="...")

        # 获取句柄并通知
        handle = task.get_handle("video_gen", "V001")
        handle.notify("approval", True)

        # 取消任务
        await task.cancel("video_gen", "V001")
        ```
    """

    @staticmethod
    def runner() -> TaskRunner:
        """获取 TaskRunner 实例"""
        return TaskRunner()

    @staticmethod
    async def start(
        task_type: str,
        task_id: str,
        chat_key: str,
        plugin: "NekroPlugin",
        *args: Any,
        **kwargs: Any,
    ) -> AsyncTaskHandle:
        """启动任务"""
        return await TaskRunner().start(
            task_type,
            task_id,
            chat_key,
            plugin,
            *args,
            **kwargs,
        )

    @staticmethod
    def get_handle(task_type: str, task_id: str) -> Optional[AsyncTaskHandle]:
        """获取任务句柄"""
        return TaskRunner().get_handle(task_type, task_id)

    @staticmethod
    def get_state(task_type: str, task_id: str) -> Optional[TaskCtl]:
        """获取任务状态"""
        return TaskRunner().get_state(task_type, task_id)

    @staticmethod
    def is_running(task_type: str, task_id: str) -> bool:
        """检查任务是否运行中"""
        return TaskRunner().is_running(task_type, task_id)

    @staticmethod
    async def cancel(task_type: str, task_id: str) -> bool:
        """取消任务"""
        return await TaskRunner().cancel(task_type, task_id)

    @staticmethod
    async def stop_all() -> int:
        """停止所有任务"""
        return await TaskRunner().stop_all()

    @staticmethod
    def get_running_tasks() -> List[str]:
        """获取运行中的任务列表"""
        return TaskRunner().get_running_tasks()


# 全局便捷 API 实例
task = TaskAPI()
