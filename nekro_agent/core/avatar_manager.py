"""动态头像管理器 - 简化版"""

from typing import Optional

from nekro_agent.core import logger


class AvatarManager:
    """简单的头像名称管理器"""

    def __init__(self):
        self._name = "NekroAgent"
        self._emotion_map = {
            "happy": "NekroAgent 😊",
            "thinking": "NekroAgent 🤔",
            "sleeping": "NekroAgent 😴",
            "neutral": "NekroAgent",
        }

    def set_emotion(self, emotion: str) -> str:
        """根据情绪设置头像名称"""
        self._name = self._emotion_map.get(emotion, "NekroAgent")
        logger.debug(f"头像切换为: {self._name}")
        return self._name

    def get_name(self) -> str:
        """获取当前头像名称"""
        return self._name


# 模块级单例
_avatar_manager: Optional[AvatarManager] = None


def get_avatar_manager() -> AvatarManager:
    """获取头像管理器实例"""
    global _avatar_manager
    if _avatar_manager is None:
        _avatar_manager = AvatarManager()
    return _avatar_manager
