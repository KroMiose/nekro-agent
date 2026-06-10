from tortoise import fields
from tortoise.models import Model


class DBAdapterInstanceEvent(Model):
    """适配器实例事件模型，用于记录实例状态变更与运行事件。"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    instance_id = fields.IntField(index=True, description="适配器实例 ID")
    event_type = fields.CharField(max_length=64, index=True, description="事件类型")
    status_from = fields.CharField(max_length=32, default="", description="变更前状态")
    status_to = fields.CharField(max_length=32, default="", description="变更后状态")
    message = fields.TextField(default="", description="事件消息")
    payload_json = fields.TextField(default="", description="事件载荷(JSON)")
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:  # type: ignore
        table = "adapter_instance_event"
