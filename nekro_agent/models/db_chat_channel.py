import datetime

from miose_toolkit_db import Mapped, MappedColumn, MioModel
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func

from nekro_agent.core.database import orm
from nekro_agent.core.logger import logger
from nekro_agent.schemas.chat_channel import channelData


@orm.reg_predefine_data_model(table_name="chat_channel", primary_key="id")
class DBChatChannel(MioModel):
    """数据库聊天频道模型"""

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True, comment="ID")

    chat_key: Mapped[str] = MappedColumn(String(32), comment="会话唯一标识", index=True)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True, comment="是否激活")
    data: Mapped[str] = MappedColumn(Text, comment="频道数据")

    create_time: Mapped[datetime.datetime] = MappedColumn(DateTime, server_default=func.now(), comment="创建时间")
    update_time: Mapped[datetime.datetime] = MappedColumn(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
        index=True,
    )

    @classmethod
    def get_channel(cls, chat_key: str) -> "DBChatChannel":
        """获取聊天频道"""
        assert chat_key, "获取聊天频道失败，chat_key 为空"
        data = cls.filter(conditions={DBChatChannel.chat_key: chat_key}, limit=1)
        return (
            data[0]
            if data
            else cls.add(
                data={DBChatChannel.chat_key: chat_key, DBChatChannel.data: channelData(chat_key=chat_key).model_dump_json()},
            )
        )

    async def get_channel_data(self) -> channelData:
        """获取聊天频道数据"""
        try:
            return channelData.model_validate_json(self.data)
        except Exception as e:
            logger.error(f"获取聊天频道数据失败，{e} 重置使用新数据")
            await self.reset_channel()
            return channelData(chat_key=self.chat_key)

    def save_channel_data(self, data: channelData):
        """保存聊天频道数据"""
        self.update({DBChatChannel.data: data.model_dump_json()})

    async def reset_channel(self):
        """重置聊天频道"""
        chanel_data = await self.get_channel_data()
        await chanel_data.clear_status()
        self.update({DBChatChannel.data: channelData(chat_key=self.chat_key).model_dump_json()})

    async def set_active(self, is_active: bool):
        """设置频道是否激活"""
        self.update({DBChatChannel.is_active: is_active})
