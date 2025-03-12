import time
from typing import Dict, List, Optional

from nonebot.adapters.onebot.v11 import Bot
from pydantic import BaseModel

from nekro_agent.core.bot import get_bot
from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.schemas.chat_message import ChatType

MAX_PRESET_STATUS_LIST_SIZE = 99


class PresetStatus(BaseModel):
    """预设状态"""

    setting_name: str
    description: str
    translated_timestamp: int

    def render_prompts(self, extra: bool = False) -> str:
        time_diff = time.time() - self.translated_timestamp
        time_diff_str = time.strftime("%H:%M:%S", time.gmtime(time_diff))
        addition_str = (
            (
                " Please Use `update_preset_status` to update it."
                if time_diff > 300
                else " Use `update_preset_status` to update it If doesn't fit the current scene description."
            )
            if extra
            else ""
        )
        return f"{self.setting_name}: {self.description} (updated {time_diff_str} ago.{addition_str})"


class ChannelData(BaseModel):
    """聊天频道数据"""

    chat_key: str
    preset_status_list: List[PresetStatus] = []

    class Config:
        extra = "ignore"

    def _append_preset_status(self, preset_status: PresetStatus):
        """添加预设状态"""
        self.preset_status_list.append(preset_status)
        if len(self.preset_status_list) > MAX_PRESET_STATUS_LIST_SIZE:
            self.preset_status_list.pop(0)

    async def update_preset_status(self, preset_status: PresetStatus):
        """更新预设状态"""
        latest_preset_status: Optional[PresetStatus] = self.get_latest_preset_status()
        if latest_preset_status is not None and latest_preset_status.setting_name == preset_status.setting_name:
            self.preset_status_list[-1].translated_timestamp = preset_status.translated_timestamp
        else:
            self._append_preset_status(preset_status)
            chat_type, chat_id = self.chat_key.split("_")
            try:
                if chat_type == "group" and config.SESSION_ENABLE_CHANGE_NICKNAME:
                    await get_bot().set_group_card(
                        group_id=int(chat_id),
                        user_id=int(config.BOT_QQ),
                        card=f"{config.SESSION_NICKNAME_PREFIX}{preset_status.setting_name}",
                    )
            except Exception as e:
                logger.warning(f"会话 {self.chat_key} 尝试更新群名片失败: {e}")

    def get_latest_preset_status(self) -> Optional[PresetStatus]:
        if len(self.preset_status_list) == 0:
            return None
        return self.preset_status_list[-1]

    def render_prompts(self) -> str:
        """渲染提示词"""
        latest_preset_status = self.get_latest_preset_status()
        if latest_preset_status is None:
            return "Current Character Setting status: No special status. (Use `update_preset_status` to update it **immediately**!)"

        history_str: str = ""
        if len(self.preset_status_list) > 1:
            history_str = "History Status:\n " + "".join(
                [
                    f"{preset_status.render_prompts()}\n"
                    for preset_status in self.preset_status_list[-config.AI_MAX_PRESET_STATUS_REFER_SIZE : -1]
                ],
            )

        return f"{history_str}" + "Current Character Setting status:" + f"{latest_preset_status.render_prompts(extra=True)}\n\n"

    async def clear_status(self):
        self.preset_status_list = []
        chat_type, chat_id = self.chat_key.split("_")
        if chat_type == "group" and config.SESSION_ENABLE_CHANGE_NICKNAME:
            await get_bot().set_group_card(
                group_id=int(chat_id),
                user_id=int(config.BOT_QQ),
                card=f"{config.SESSION_NICKNAME_PREFIX}{config.AI_CHAT_PRESET_NAME}",
            )

    @property
    def chat_type(self) -> ChatType:
        """获取聊天频道类型"""
        return ChatType.from_chat_key(self.chat_key)
