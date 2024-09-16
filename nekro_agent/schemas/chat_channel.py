import time
from typing import List, Optional

from nonebot.adapters.onebot.v11 import Bot
from pydantic import BaseModel

from nekro_agent.core.bot import get_bot
from nekro_agent.core.config import config
from nekro_agent.core.logger import logger

MAX_PRESET_STATUS_LIST_SIZE = 99
MAX_PRESET_STATUS_SHOW_SIZE = 24


class PresetStatus(BaseModel):
    """预设状态"""

    setting_name: str
    description: str
    translated_timestamp: int


class channelData(BaseModel):
    chat_key: str
    preset_status_list: List[PresetStatus] = []

    def append_preset_status(self, preset_status: PresetStatus):
        self.preset_status_list.append(preset_status)
        if len(self.preset_status_list) > MAX_PRESET_STATUS_LIST_SIZE:
            self.preset_status_list.pop(0)

    async def update_preset_status(self, preset_status: PresetStatus):
        latest_preset_status: Optional[PresetStatus] = self.get_latest_preset_status()
        if latest_preset_status is not None and latest_preset_status.setting_name == preset_status.setting_name:
            self.preset_status_list[-1].translated_timestamp = preset_status.translated_timestamp
        else:
            self.append_preset_status(preset_status)
            chat_type, chat_id = self.chat_key.split("_")
            try:
                await get_bot().set_group_card(
                    group_id=int(chat_id),
                    user_id=int(config.BOT_QQ),
                    card=f"{config.AI_NAME_PREFIX}{preset_status.setting_name}",
                )
            except Exception as e:
                logger.warning(f"会话 {self.chat_key} 尝试更新群名片失败: {e}")

    def get_latest_preset_status(self) -> Optional[PresetStatus]:
        if len(self.preset_status_list) == 0:
            return None
        return self.preset_status_list[-1]

    def render_prompt(self) -> str:
        history_str = ""
        if len(self.preset_status_list) > 1:
            history_str = "History Status:\n "
            for preset_status in self.preset_status_list[-MAX_PRESET_STATUS_SHOW_SIZE:-1]:
                time_diff_str = time.strftime("%H:%M:%S", time.gmtime(time.time() - preset_status.translated_timestamp))
                history_str += f"- {preset_status.setting_name}: {preset_status.description} ({time_diff_str} ago)\n"
            history_str = history_str.strip() + "\n"

        latest_preset_status = self.get_latest_preset_status()
        if latest_preset_status is None:
            return "Current Character Setting status: No special status. (Use `update_preset_status` to update it **immediately**!)"
        time_diff = time.time() - latest_preset_status.translated_timestamp
        time_diff_str = time.strftime("%H:%M:%S", time.gmtime(time_diff))
        addition_str = (
            "Please Use `update_preset_status` to update it."
            if time_diff > 300
            else "Use `update_preset_status` to update it If doesn't fit the current scene description."
        )
        return f"{history_str}Current Character Setting status: {latest_preset_status.setting_name}: {latest_preset_status.description} (updated {time_diff_str} ago. {addition_str})"

    def clear_preset_status_list(self):
        self.preset_status_list = []
