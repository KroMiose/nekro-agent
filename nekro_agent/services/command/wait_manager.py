"""交互等待会话管理器"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

from nonebot import logger


@dataclass
class WaitSession:
    """交互等待会话 - 严格绑定 chat_key + user_id"""

    chat_key: str  # 必须：频道标识，wait 只在同一频道内生效
    user_id: str  # 必须：发起用户，只捕获该用户的回复
    callback_cmd: str  # 后续输入路由到的命令
    context_data: dict  # 透传给 callback_cmd 的上下文
    timeout: float  # 超时秒数
    created_at: float = field(default_factory=time.time)  # 创建时间戳
    on_timeout_message: str = "操作超时，已取消"  # 超时提示


class WaitSessionManager:
    """交互等待管理器 - 以 (chat_key, user_id) 为键"""

    def __init__(self):
        self._sessions: dict[tuple[str, str], WaitSession] = {}
        self._timeout_tasks: dict[tuple[str, str], asyncio.Task] = {}

    async def create_session(
        self,
        chat_key: str,
        user_id: str,
        callback_cmd: str,
        context_data: Optional[dict] = None,
        timeout: float = 60.0,
        on_timeout_message: str = "操作超时，已取消",
    ) -> None:
        key = (chat_key, user_id)

        # 取消已有的 wait
        self.cancel(chat_key, user_id)

        # 同一用户在同一频道只能有一个挂起的 wait
        self._sessions[key] = WaitSession(
            chat_key=chat_key,
            user_id=user_id,
            callback_cmd=callback_cmd,
            context_data=context_data or {},
            timeout=timeout,
            on_timeout_message=on_timeout_message,
        )
        # 启动超时清理任务
        self._timeout_tasks[key] = asyncio.create_task(self._timeout_cleanup(key, timeout))

    def try_consume(self, chat_key: str, user_id: str) -> Optional[WaitSession]:
        """尝试消费一个 wait session (匹配 chat_key + user_id)"""
        key = (chat_key, user_id)
        session = self._sessions.pop(key, None)
        if session:
            # 取消超时任务
            task = self._timeout_tasks.pop(key, None)
            if task and not task.done():
                task.cancel()
        return session

    def cancel(self, chat_key: str, user_id: str) -> None:
        """取消挂起的 wait (用户发送了其他命令时调用)"""
        key = (chat_key, user_id)
        self._sessions.pop(key, None)
        task = self._timeout_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()

    def has_pending(self, chat_key: str, user_id: str) -> bool:
        """检查是否有挂起的 wait"""
        return (chat_key, user_id) in self._sessions

    async def _timeout_cleanup(self, key: tuple[str, str], timeout: float) -> None:
        try:
            await asyncio.sleep(timeout)
        except asyncio.CancelledError:
            return

        session = self._sessions.pop(key, None)
        self._timeout_tasks.pop(key, None)
        if session:
            logger.debug(f"WaitSession 超时: chat_key={session.chat_key}, user_id={session.user_id}")
            # 通知用户超时 - 通过适配器发送消息
            await self._send_timeout_message(session)

    async def _send_timeout_message(self, session: WaitSession) -> None:
        """发送超时消息"""
        try:
            from nekro_agent.services.message_service import message_service

            await message_service.push_system_message(
                chat_key=session.chat_key,
                agent_messages=session.on_timeout_message,
            )
        except Exception as e:
            logger.warning(f"发送 wait 超时消息失败: {e}")


wait_manager = WaitSessionManager()
