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
        """用户是否激活"""
        from datetime import datetime

        now = datetime.now()
        return self.ban_until is None or now > self.ban_until  # 检查是否在封禁期

    @property
    def is_prevent_trigger(self) -> bool:
        """用户是否禁止触发"""
        from datetime import datetime

        now = datetime.now()
        return self.prevent_trigger_until is None or now > self.prevent_trigger_until  # 检查是否在禁止触发期

    class Meta: # type: ignore
        table = "user"
