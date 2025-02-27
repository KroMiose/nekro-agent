from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from tortoise import fields
from tortoise.models import Model


class DBUser(Model):
    """数据库用户模型"""

    id = fields.IntField(pk=True, generated=True, description="用户ID")
    username = fields.CharField(max_length=128, description="用户名")
    password = fields.CharField(max_length=128, description="密码")
    bind_qq = fields.CharField(max_length=32, unique=True, description="绑定的QQ号")

    perm_level = fields.IntField(description="权限等级")
    login_time = fields.DatetimeField(description="上次登录时间")

    ban_until = fields.DatetimeField(null=True, description="封禁截止时间")
    prevent_trigger_until = fields.DatetimeField(null=True, description="禁止触发截止时间")
    ext_data = fields.JSONField(default=dict, description="扩展数据")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    @property
    def is_active(self) -> bool:
        """检查用户是否处于活跃状态（未被封禁）"""
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        if self.ban_until is None:
            return True
        # 确保 ban_until 也是带时区的，如果是 UTC 时间则转换为上海时间
        ban_until = self.ban_until
        if ban_until.tzinfo is None:
            ban_until = ban_until.replace(tzinfo=ZoneInfo("UTC"))
        ban_until = ban_until.astimezone(ZoneInfo("Asia/Shanghai"))
        return now > ban_until  # 检查是否在封禁期

    @property
    def is_prevent_trigger(self) -> bool:
        """检查用户是否被禁止触发（临时或永久）"""
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        if self.prevent_trigger_until is None:
            return False
        # 确保 prevent_trigger_until 也是带时区的，如果是 UTC 时间则转换为上海时间
        prevent_until = self.prevent_trigger_until
        if prevent_until.tzinfo is None:
            prevent_until = prevent_until.replace(tzinfo=ZoneInfo("UTC"))
        prevent_until = prevent_until.astimezone(ZoneInfo("Asia/Shanghai"))
        return now < prevent_until  # 检查是否在禁止触发期间（现在时间小于结束时间）

    class Meta:  # type: ignore
        table = "user"
