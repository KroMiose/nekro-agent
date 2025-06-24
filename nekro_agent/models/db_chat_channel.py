import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union

from pydantic import BaseModel
from tortoise import fields
from tortoise.models import Model

from nekro_agent.adapters.utils import adapter_utils
from nekro_agent.core import config
from nekro_agent.core.logger import logger
from nekro_agent.models.db_preset import DBPreset
from nekro_agent.schemas.chat_message import ChatType
from nekro_agent.services.config_resolver import config_resolver
from nekro_agent.services.plugin.collector import plugin_collector

if TYPE_CHECKING:
    from nekro_agent.adapters.interface.base import BaseAdapter
    from nekro_agent.core.config import CoreConfig


class DefaultPreset(BaseModel):
    """默认人设"""

    name: str
    content: str


class DBChatChannel(Model):
    """数据库聊天频道模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    is_active = fields.BooleanField(default=True, description="是否激活")
    preset_id = fields.IntField(default=None, null=True, description="人设 ID")
    data = fields.TextField(description="频道数据")

    adapter_key = fields.CharField(max_length=64, index=True, description="适配器标识")
    channel_id = fields.CharField(max_length=64, index=True, description="频道 ID")
    channel_name = fields.CharField(max_length=64, null=True, description="频道名称")
    channel_type = fields.CharField(max_length=32, null=True, description="频道类型")

    chat_key = fields.CharField(max_length=64, index=True, description="全局会话唯一标识")
    conversation_start_time = fields.DatetimeField(auto_now_add=True, description="对话起始时间")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    _effective_config: Optional["CoreConfig"] = None

    class Meta:  # type: ignore
        table = "chat_channel"

    @classmethod
    async def get_or_create(
        cls,
        adapter_key: str,
        channel_id: str,
        channel_type: ChatType,
        channel_name: str = "",
    ) -> "DBChatChannel":
        """获取或创建聊天频道"""
        channel = await cls.get_or_none(adapter_key=adapter_key, channel_id=channel_id)
        if not channel:
            is_active = (channel_type == ChatType.GROUP and config.SESSION_GROUP_ACTIVE_DEFAULT) or (
                channel_type == ChatType.PRIVATE and config.SESSION_PRIVATE_ACTIVE_DEFAULT
            )
            channel = await cls.create(
                adapter_key=adapter_key,
                channel_id=channel_id,
                channel_type=channel_type.value,
                channel_name=channel_name,
                chat_key=f"{adapter_key}-{channel_id}",
                is_active=is_active,
                data=json.dumps({}),
            )
        else:
            if channel_name and channel.channel_name != channel_name:
                logger.info(f"更新频道名称: {channel.channel_name} -> {channel_name}")
                channel.channel_name = channel_name
                await channel.save()
            if channel_type and channel.channel_type != channel_type.value:
                logger.info(f"更新频道类型: {channel.channel_type} -> {channel_type.value}")
                channel.channel_type = channel_type.value
                await channel.save()
        return channel

    @classmethod
    async def get_channel(cls, chat_key: str) -> "DBChatChannel":
        """获取聊天频道"""
        assert chat_key, "获取聊天频道失败，chat_key 为空"
        channel = await cls.get_or_none(chat_key=chat_key)
        if not channel:
            raise ValueError(f"聊天频道不存在: {chat_key}")
        return channel

    async def sync_channel_name(self):
        """同步频道名称"""
        try:
            self.channel_name = await self.get_channel_name()
        except Exception as e:
            logger.error(f"同步频道名称失败: {e!s}")
        else:
            await self.save()

    async def get_channel_name(self) -> str:
        """获取频道名称"""

        adapter = adapter_utils.get_adapter(self.adapter_key)
        return (await adapter.get_channel_info(self.channel_id)).channel_name

    async def reset_channel(self):
        """重置聊天频道"""
        from nekro_agent.schemas.agent_ctx import AgentCtx

        self.conversation_start_time = datetime.now()  # 重置对话起始时间
        await self.save()

        # 执行重置回调
        await plugin_collector.chat_channel_on_reset(await AgentCtx.create_by_chat_key(chat_key=self.chat_key))

    async def set_active(self, is_active: bool):
        """设置频道是否激活"""
        self.is_active = is_active
        await self.save()

    @property
    def chat_type(self) -> ChatType:
        """获取聊天频道类型"""
        try:
            return ChatType(self.channel_type)
        except ValueError as e:
            logger.error(f"获取聊天频道类型失败: {e!s}")
            return ChatType.UNKNOWN

    async def get_preset(self) -> Union[DBPreset, DefaultPreset]:
        """获取人设"""
        preset = await DBPreset.get_or_none(id=self.preset_id)
        if not preset:
            return DefaultPreset(name=config.AI_CHAT_PRESET_NAME, content=config.AI_CHAT_PRESET_SETTING)
        return preset

    @property
    def adapter(self) -> "BaseAdapter":
        """获取适配器"""
        return adapter_utils.get_adapter(self.adapter_key)

    async def get_effective_config(self) -> "CoreConfig":
        if self._effective_config is None:
            self._effective_config = await config_resolver.get_effective_config(self.chat_key)
        return self._effective_config
