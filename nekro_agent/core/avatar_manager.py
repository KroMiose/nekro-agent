"""动态头像管理器 - 支持定时、状态、指令切换头像"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from nekro_agent.core import logger


class AvatarTriggerType(str, Enum):
    """头像触发类型"""
    TIMER = "timer"           # 定时切换
    STATE = "state"          # 状态变化触发
    COMMAND = "command"       # 指令切换
    EMOTION = "emotion"       # 情绪触发


class AvatarProfile(BaseModel):
    """头像配置"""
    name: str = "NekroAgent"
    avatar_url: str = ""     # 可选的虚拟头像 URL（用于展示）
    emotion_tag: str = "neutral"  # 关联情绪标签


@dataclass
class AvatarState:
    """头像状态"""
    current_profile: AvatarProfile
    emotion: str = "neutral"
    last_changed: float = field(default_factory=time.time)
    change_reason: str = ""


class DynamicAvatarManager:
    """动态头像管理器

    支持多种切换模式：
    1. 定时切换：根据时间自动更换头像
    2. 状态切换：根据 Agent 状态变化更换头像
    3. 指令切换：通过指令手动更换头像
    4. 情绪切换：根据情绪状态更换对应头像
    """

    def __init__(self):
        self._profiles: Dict[str, AvatarProfile] = {}
        self._state = AvatarState(current_profile=AvatarProfile())
        self._timers: Dict[str, float] = {}  # trigger_id -> last_trigger_time
        self._emotion_map: Dict[str, str] = {}  # emotion -> profile_name
        self._listeners: List[Callable] = []
        self._running = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """初始化默认头像配置"""
        # 注册默认头像配置
        await self.register_profile(AvatarProfile(
            name="NekroAgent",
            emotion_tag="neutral"
        ))
        await self.register_profile(AvatarProfile(
            name="NekroAgent 😊",
            emotion_tag="happy"
        ))
        await self.register_profile(AvatarProfile(
            name="NekroAgent 🤔",
            emotion_tag="thinking"
        ))
        await self.register_profile(AvatarProfile(
            name="NekroAgent 😴",
            emotion_tag="sleeping"
        ))
        logger.info("DynamicAvatarManager 初始化完成")

    async def register_profile(self, profile: AvatarProfile) -> None:
        """注册头像配置"""
        async with self._lock:
            self._profiles[profile.name] = profile
            if profile.emotion_tag and profile.emotion_tag != "neutral":
                self._emotion_map[profile.emotion_tag] = profile.name

    async def unregister_profile(self, name: str) -> None:
        """注销头像配置"""
        async with self._lock:
            if name in self._profiles:
                profile = self._profiles[name]
                if profile.emotion_tag in self._emotion_map:
                    del self._emotion_map[profile.emotion_tag]
                del self._profiles[name]

    async def switch_avatar(
        self,
        profile_name: str,
        reason: str = ""
    ) -> Optional[AvatarProfile]:
        """切换到指定头像配置"""
        async with self._lock:
            if profile_name not in self._profiles:
                logger.warning(f"头像配置不存在: {profile_name}")
                return None

            profile = self._profiles[profile_name]
            self._state = AvatarState(
                current_profile=profile,
                last_changed=time.time(),
                change_reason=reason or "manual_switch"
            )

            logger.info(f"头像切换: {profile.name} (原因: {reason})")

            # 通知监听器
            for listener in self._listeners:
                try:
                    if asyncio.iscoroutinefunction(listener):
                        await listener(profile, reason)
                    else:
                        listener(profile, reason)
                except Exception as e:
                    logger.error(f"头像切换监听器执行失败: {e}")

            return profile

    async def set_emotion(self, emotion: str) -> Optional[AvatarProfile]:
        """根据情绪设置头像"""
        if emotion == self._state.emotion:
            return self._state.current_profile

        self._state.emotion = emotion

        # 如果有对应的情绪配置，切换头像
        if emotion in self._emotion_map:
            profile_name = self._emotion_map[emotion]
            return await self.switch_avatar(profile_name, reason=f"emotion_{emotion}")

        return self._state.current_profile

    async def get_current_profile(self) -> AvatarProfile:
        """获取当前头像配置"""
        return self._state.current_profile

    async def get_sender_info(self) -> Dict[str, str]:
        """获取当前发送者信息（用于消息发送）

        Returns:
            包含 name 和可选的 avatar_url 的字典
        """
        profile = self._state.current_profile
        return {
            "name": profile.name,
            "avatar_url": profile.avatar_url,
        }

    def add_listener(self, listener: Callable) -> None:
        """添加头像切换监听器"""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable) -> None:
        """移除头像切换监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)

    async def list_profiles(self) -> List[AvatarProfile]:
        """列出所有头像配置"""
        return list(self._profiles.values())

    async def get_state_info(self) -> Dict[str, Any]:
        """获取当前头像状态信息"""
        return {
            "current_profile": self._state.current_profile.model_dump(),
            "emotion": self._state.emotion,
            "last_changed": datetime.fromtimestamp(self._state.last_changed).isoformat(),
            "change_reason": self._state.change_reason,
            "available_profiles": list(self._profiles.keys()),
            "emotion_map": self._emotion_map,
        }


# 全局单例
_avatar_manager: Optional[DynamicAvatarManager] = None
_manager_initialized = False


def get_avatar_manager() -> DynamicAvatarManager:
    """获取全局头像管理器实例"""
    global _avatar_manager, _manager_initialized
    if _avatar_manager is None:
        _avatar_manager = DynamicAvatarManager()
        # 尝试自动初始化（同步方式，仅设置基本配置）
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在运行，则创建任务初始化
                asyncio.create_task(_async_init())
            else:
                loop.run_until_complete(_async_init())
        except RuntimeError:
            # 如果没有事件循环，稍后初始化
            pass
    return _avatar_manager


async def _async_init() -> None:
    """异步初始化头像管理器"""
    global _manager_initialized
    if not _manager_initialized:
        manager = get_avatar_manager()
        await manager.initialize()
        _manager_initialized = True


async def initialize_avatar_manager() -> DynamicAvatarManager:
    """初始化并返回全局头像管理器"""
    manager = get_avatar_manager()
    await manager.initialize()
    return manager
