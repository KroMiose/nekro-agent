"""适配器工具库

提供延迟加载的适配器相关工具方法，避免在业务逻辑中重复导入。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nekro_agent.adapters.interface.base import BaseAdapter
    from nekro_agent.api.schemas import AgentCtx


class AdapterUtils:
    """适配器工具类"""

    @staticmethod
    def get_adapter(adapter_key: str) -> "BaseAdapter":
        """获取适配器实例

        Args:
            adapter_key (str): 适配器标识

        Returns:
            BaseAdapter: 适配器实例
        """
        from nekro_agent.adapters import get_adapter

        return get_adapter(adapter_key)

    @staticmethod
    async def get_adapter_for_chat(chat_key: str) -> "BaseAdapter":
        """根据聊天标识获取适配器

        Args:
            chat_key (str): 聊天标识

        Returns:
            BaseAdapter: 适配器实例
        """
        from nekro_agent.models.db_chat_channel import DBChatChannel

        db_chat_channel = await DBChatChannel.get_channel(chat_key=chat_key)
        return AdapterUtils.get_adapter(db_chat_channel.adapter_key)

    @staticmethod
    async def get_adapter_for_ctx(ctx: "AgentCtx") -> "BaseAdapter":
        """根据上下文获取适配器

        Args:
            ctx (AgentCtx): 代理上下文

        Returns:
            BaseAdapter: 适配器实例
        """
        return await AdapterUtils.get_adapter_for_chat(ctx.from_chat_key)


# 创建全局实例，便于使用
adapter_utils = AdapterUtils()
