from tortoise import fields
from tortoise.models import Model


class DBExecCode(Model):
    """数据库执行代码模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    chat_key = fields.CharField(max_length=32, index=True, description="会话唯一标识")
    trigger_user_id = fields.IntField(default=0, index=True, description="触发用户ID")
    trigger_user_name = fields.CharField(max_length=128, default="System", description="触发用户名")
    success = fields.BooleanField(default=False, description="是否成功")
    code_text = fields.TextField(description="执行代码文本")
    outputs = fields.TextField(description="输出结果")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "exec_code"
