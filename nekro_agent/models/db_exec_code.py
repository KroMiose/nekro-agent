from enum import IntEnum

from tortoise import fields
from tortoise.models import Model


class ExecStopType(IntEnum):
    """执行停止类型"""

    NORMAL = 0  # 正常结束
    ERROR = 1  # 错误停止
    TIMEOUT = 2  # 超时停止
    AGENT = 8  # 代理停止
    MANUAL = 9  # 手动停止
    SECURITY = 10  # 安全停止
    MULTIMODAL_AGENT = 11  # 多模态代理停止


class DBExecCode(Model):
    """数据库执行代码模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    chat_key = fields.CharField(max_length=32, index=True, description="会话唯一标识")
    trigger_user_id = fields.IntField(default=0, index=True, description="触发用户ID")
    trigger_user_name = fields.CharField(max_length=128, default="System", description="触发用户名")
    success = fields.BooleanField(default=False, description="是否成功")
    code_text = fields.TextField(description="执行代码文本")
    outputs = fields.TextField(description="输出结果")
    use_model = fields.CharField(max_length=128, null=True, default="", description="使用模型")

    thought_chain = fields.TextField(null=True, description="思维链信息")
    stop_type = fields.IntEnumField(ExecStopType, default=ExecStopType.NORMAL, description="停止类型")
    exec_time_ms = fields.IntField(default=0, description="执行时间(毫秒)")
    generation_time_ms = fields.IntField(default=0, description="生成时间(毫秒)")
    total_time_ms = fields.IntField(default=0, description="响应总耗时(毫秒)")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "exec_code"
