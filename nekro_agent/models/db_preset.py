from enum import IntEnum

from tortoise import fields
from tortoise.models import Model


class DBPreset(Model):
    """数据库预设模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    remote_id = fields.CharField(max_length=54, null=True, index=True, description="远程预设ID")
    on_shared = fields.BooleanField(default=False, description="是否在共享预设中")

    name = fields.CharField(max_length=256, index=True, description="预设名称")
    title = fields.CharField(max_length=128, index=True, description="标题")
    avatar = fields.TextField(description="预设头像(base64)")
    content = fields.TextField(description="预设内容")
    description = fields.TextField(description="预设描述")
    tags = fields.CharField(max_length=512, description="预设标签(逗号分隔)")
    ext_data = fields.JSONField(null=True, description="扩展数据")

    author = fields.CharField(max_length=128, description="作者")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "presets"
