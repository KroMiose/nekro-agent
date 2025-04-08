from enum import IntEnum

from tortoise import fields
from tortoise.models import Model


class DBPluginData(Model):
    """数据库插件数据模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    plugin_key = fields.CharField(max_length=128, index=True, description="插件唯一标识")

    data_key = fields.CharField(max_length=128, index=True, description="插件数据键")
    data_value = fields.TextField(description="插件数据值")

    target_chat_key = fields.CharField(max_length=32, index=True, description="目标会话唯一标识")
    target_user_id = fields.CharField(max_length=32, index=True, description="目标用户ID")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "plugin_data"
