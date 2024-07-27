import json
import time
from typing import List

from miose_toolkit_llm import BaseStore
from miose_toolkit_llm.components import BaseComponent

from nekro_agent.core import config
from nekro_agent.models.db_chat_message import DBChatMessage


class ChatHistoryComponent(BaseComponent):
    """聊天历史记录组件

    组件参数：
        - chat_key: 向量数据库使用的集合名称
    """

    chat_history: List[str] = []

    class Params(BaseComponent.Params):
        pass

    def append_chat_message(self, message: DBChatMessage):
        """向聊天历史记录中添加一条消息"""
        self.chat_history.append(message.parse_chat_history_prompt())

    async def render(self) -> str:
        """渲染组件"""

        return "Last Chat Messages:\n" + "\n\n".join(self.chat_history)
