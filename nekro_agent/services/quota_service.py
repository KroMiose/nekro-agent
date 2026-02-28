import math
from datetime import datetime
from typing import Dict

from nekro_agent.core.logger import get_sub_logger

logger = get_sub_logger("quota_service")


class QuotaService:
    """配额管理服务

    负责管理聊天频道的AI回复配额，包括：
    - 临时提升额度（当天有效，重启失效）
    - 每小时限额计算
    - 配额进度查询

    数据全部存储在内存中，不依赖数据库。
    """

    def __init__(self):
        # 内存存储结构: {chat_key: {"date": "2024-01-15", "boost": 10}}
        # 临时提升仅当天有效，通过date字段判断是否过期
        self._daily_boosts: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    def _today_str(self) -> str:
        """返回今天的日期字符串，格式 YYYY-MM-DD"""
        return datetime.now().strftime("%Y-%m-%d")

    def _current_hour(self) -> int:
        """返回当前小时 (0-23)"""
        return datetime.now().hour

    # ------------------------------------------------------------------
    # 临时提升 (boost) 相关方法
    # ------------------------------------------------------------------

    def get_boost(self, chat_key: str) -> int:
        """获取指定频道当日的临时提升额度

        临时提升仅当天有效：若记录的日期不是今天，则视为已过期，返回 0。

        Args:
            chat_key: 聊天频道标识（如 "group_123456"）

        Returns:
            int: 当日临时提升的配额数，0 表示无提升或已过期
        """
        info = self._daily_boosts.get(chat_key)
        if not info or info["date"] != self._today_str():
            return 0
        return info["boost"]

    def set_boost(self, chat_key: str, amount: int) -> None:
        """设置指定频道当日的临时提升额度（覆盖原有值）

        Args:
            chat_key: 聊天频道标识
            amount: 要设置的提升配额数，建议 >= 0
        """
        self._daily_boosts[chat_key] = {
            "date": self._today_str(),
            "boost": amount,
        }
        logger.debug(f"[{chat_key}] 临时提升已设置为 {amount}")

    def add_boost(self, chat_key: str, amount: int) -> int:
        """在现有临时提升基础上追加额度

        若当日尚无提升记录，则从 0 开始累加。

        Args:
            chat_key: 聊天频道标识
            amount: 本次要追加的配额数

        Returns:
            int: 追加后的临时提升总额度
        """
        current = self.get_boost(chat_key)
        new_total = current + amount
        self.set_boost(chat_key, new_total)
        logger.debug(f"[{chat_key}] 临时提升追加 {amount}，当前总提升 {new_total}")
        return new_total

    def clear_boost(self, chat_key: str) -> None:
        """清除指定频道的临时提升记录

        清除后 get_boost() 将返回 0，直到再次调用 set_boost/add_boost。

        Args:
            chat_key: 聊天频道标识
        """
        removed = self._daily_boosts.pop(chat_key, None)
        if removed is not None:
            logger.debug(f"[{chat_key}] 临时提升已清除（原值 {removed.get('boost', 0)}）")

    # ------------------------------------------------------------------
    # 配额计算方法
    # ------------------------------------------------------------------

    def calculate_hourly_quota(self, daily_limit: int) -> int:
        """根据每日限额计算每小时限额（向上取整）

        公式: max(1, ceil(daily_limit / 24))

        当 daily_limit <= 0 时返回 0（表示无限额或未启用）。

        Args:
            daily_limit: 每日限额数（含临时提升后的有效限额）

        Returns:
            int: 每小时限额（最少 1 条；daily_limit <= 0 时为 0）

        示例:
            - daily_limit=24  → 1 条/小时
            - daily_limit=50  → 3 条/小时  (ceil(50/24)=3)
            - daily_limit=100 → 5 条/小时  (ceil(100/24)=5)
            - daily_limit=150 → 7 条/小时  (ceil(150/24)=7)
        """
        if daily_limit <= 0:
            return 0
        return max(1, math.ceil(daily_limit / 24))

    def get_hourly_quota_progress(
        self,
        chat_key: str,
        current_hour_count: int,
        hourly_limit: int,
    ) -> Dict:
        """获取当前小时的配额使用进度

        Args:
            chat_key: 聊天频道标识（保留字段，便于未来扩展日志）
            current_hour_count: 本小时已回复的消息数
            hourly_limit: 小时限额

        Returns:
            Dict: 包含以下字段的进度字典
                - hour (int): 当前小时 (0-23)
                - current_count (int): 本小时已使用数
                - hourly_limit (int): 小时限额
                - remaining (int): 剩余可用额度（最小为 0）
                - exceeded (bool): 是否已超限
        """
        return {
            "hour": self._current_hour(),
            "current_count": current_hour_count,
            "hourly_limit": hourly_limit,
            "remaining": max(0, hourly_limit - current_hour_count),
            "exceeded": current_hour_count >= hourly_limit,
        }


# 全局单例，供其他模块直接 import 使用
quota_service = QuotaService()
