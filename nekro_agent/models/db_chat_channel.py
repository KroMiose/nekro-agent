from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel
from tortoise import fields
from tortoise.models import Model

from nekro_agent.core import config
from nekro_agent.core.bot import get_bot
from nekro_agent.core.logger import logger
from nekro_agent.models.db_preset import DBPreset
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.plugin.collector import plugin_collector


class DefaultPreset(BaseModel):
    """默认人设"""

    name: str
    content: str


class DBChatChannel(Model):
    """数据库聊天频道模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    chat_key = fields.CharField(max_length=32, index=True, description="会话唯一标识")
    is_active = fields.BooleanField(default=True, description="是否激活")
    preset_id = fields.IntField(default=None, null=True, description="人设 ID")
    data = fields.TextField(description="频道数据")

    channel_name = fields.CharField(max_length=64, null=True, description="频道名称")
    conversation_start_time = fields.DatetimeField(auto_now_add=True, description="对话起始时间")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "chat_channel"

    @classmethod
    async def get_channel(cls, chat_key: str) -> "DBChatChannel":
        """获取聊天频道"""
        assert chat_key, "获取聊天频道失败，chat_key 为空"
        channel = await cls.get_or_none(chat_key=chat_key)
        if not channel:
            chat_type = ChatType.from_chat_key(chat_key)
            channel = await cls.create(
                chat_key=chat_key,
                channel_name="",
                is_active=(
                    config.SESSION_GROUP_ACTIVE_DEFAULT
                    if chat_type == ChatType.GROUP
                    else config.SESSION_PRIVATE_ACTIVE_DEFAULT
                ),
                data="",
            )
            await channel.sync_channel_name()
        return channel

    async def sync_channel_name(self):
        """同步频道名称"""
        self.channel_name = await self.get_channel_name()
        await self.save()

    async def get_channel_name(self) -> str:
        """获取频道名称"""
        chat_type = self.chat_type
        if chat_type == ChatType.GROUP:
            try:
                channel_name = (await get_bot().get_group_info(group_id=int(self.chat_key.replace("group_", ""))))["group_name"]
            except Exception as e:
                logger.error(f"获取群组名称失败: {e!s}")
                channel_name = self.chat_key
        elif chat_type == ChatType.PRIVATE:
            channel_name = (await get_bot().get_stranger_info(user_id=int(self.chat_key.replace("private_", ""))))["nickname"]
        else:
            channel_name = self.chat_key
        return channel_name

    async def reset_channel(self):
        """重置聊天频道"""
        self.conversation_start_time = datetime.now()  # 重置对话起始时间
        await self.save()

        # 执行重置回调
        await plugin_collector.chat_channel_on_reset(AgentCtx(from_chat_key=self.chat_key))

    async def set_active(self, is_active: bool):
        """设置频道是否激活"""
        self.is_active = is_active
        await self.save()

    @property
    def chat_type(self) -> ChatType:
        """获取聊天频道类型"""
        return ChatType.from_chat_key(self.chat_key)

    async def get_preset(self) -> Union[DBPreset, DefaultPreset]:
        """获取人设"""
        preset = await DBPreset.get_or_none(id=self.preset_id)
        if not preset:
            return DefaultPreset(name=config.AI_CHAT_PRESET_NAME, content=config.AI_CHAT_PRESET_SETTING)
        return preset
