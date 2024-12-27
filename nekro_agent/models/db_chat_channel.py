from tortoise import fields
from tortoise.models import Model

from nekro_agent.core import config
from nekro_agent.core.logger import logger
from nekro_agent.schemas.chat_channel import ChannelData
from nekro_agent.schemas.chat_message import ChatType


class DBChatChannel(Model):
    """数据库聊天频道模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    chat_key = fields.CharField(max_length=32, index=True, description="会话唯一标识")
    is_active = fields.BooleanField(default=True, description="是否激活")
    data = fields.TextField(description="频道数据")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
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
                is_active=(
                    config.SESSION_GROUP_ACTIVE_DEFAULT
                    if chat_type == ChatType.GROUP
                    else config.SESSION_PRIVATE_ACTIVE_DEFAULT
                ),
                data=ChannelData(chat_key=chat_key).model_dump_json(),
            )
        return channel

    async def get_channel_data(self) -> ChannelData:
        """获取聊天频道数据"""
        try:
            return ChannelData.model_validate_json(self.data)
        except Exception as e:
            logger.error(f"获取聊天频道数据失败，{e} 重置使用新数据")
            await self.reset_channel()
            return ChannelData(chat_key=self.chat_key)

    async def save_channel_data(self, data: ChannelData):
        """保存聊天频道数据"""
        self.data = data.model_dump_json()
        await self.save()

    async def reset_channel(self):
        """重置聊天频道"""
        chanel_data = await self.get_channel_data()
        await chanel_data.clear_status()
        self.data = ChannelData(chat_key=self.chat_key).model_dump_json()
        await self.save()

    async def set_active(self, is_active: bool):
        """设置频道是否激活"""
        self.is_active = is_active
        await self.save()

    @property
    def chat_type(self) -> ChatType:
        """获取聊天频道类型"""
        channel_data = ChannelData.model_validate_json(self.data)
        return channel_data.chat_type
