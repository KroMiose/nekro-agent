from tortoise import fields
from tortoise.models import Model


class DBAdapterInstance(Model):
    """适配器实例模型，用于存储通用多实例配置。"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    adapter_key = fields.CharField(max_length=128, index=True, description="适配器唯一标识")
    instance_key = fields.CharField(max_length=128, description="适配器实例唯一标识")
    display_name = fields.CharField(max_length=256, default="", description="实例显示名称")
    status = fields.CharField(max_length=32, default="pending", index=True, description="实例状态")
    enabled = fields.BooleanField(default=True, index=True, description="是否启用")
    is_default = fields.BooleanField(default=False, description="是否默认实例")
    provider = fields.CharField(max_length=128, default="", description="服务提供方")
    provider_account_id = fields.CharField(max_length=256, default="", description="服务提供方账号标识")
    metadata_json = fields.TextField(default="", description="实例元数据(JSON)")
    last_error = fields.TextField(default="", description="最近错误信息")
    last_active_at = fields.DatetimeField(null=True, description="最近活跃时间")
    next_renew_at = fields.DatetimeField(null=True, index=True, description="下次续期时间")
    renew_before_minutes = fields.IntField(default=60, description="提前续期分钟数")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "adapter_instance"
        unique_together = (("adapter_key", "instance_key"),)
