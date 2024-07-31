import json
import time
from typing import List

from miose_toolkit_llm import BaseStore
from miose_toolkit_llm.components import BaseComponent
from miose_toolkit_llm.scene import BaseScene

from nekro_agent.core import config
from nekro_agent.models.db_chat_message import DBChatMessage


class ChatHistoryComponent(BaseComponent):
    """聊天历史记录组件

    组件参数：
        - one_time_code: 一次性代码，用于分隔聊天历史记录
    """

    chat_history: List[str]

    class Params(BaseComponent.Params):
        one_time_code: str = ""

    def __init__(self, scene: BaseScene):
        self.chat_history = []
        super().__init__(scene)

    def append_chat_message(self, message: DBChatMessage):
        """向聊天历史记录中添加一条消息"""
        self.chat_history.append(message.parse_chat_history_prompt(self.params.one_time_code))

    async def render(self) -> str:
        """渲染组件"""

        return (
            f"Current Time: {time.strftime('%Y-%m-%d %H:%M:%S %Z %A', time.localtime())}\n"
            "Recent Messages:\n"
            f"\n<{self.params.one_time_code} | message separator>\n".join(self.chat_history)
        )
