from tortoise import fields
from tortoise.models import Model


class DBWorkspace(Model):
    """工作区数据模型"""

    id = fields.IntField(pk=True, generated=True, description="ID")
    name = fields.CharField(max_length=64, unique=True, index=True, description="工作区名称")
    description = fields.TextField(default="", description="工作区描述")
    status = fields.CharField(max_length=16, default="stopped", description="状态: active|stopped|failed|deleting")

    # 镜像配置
    sandbox_image = fields.CharField(max_length=128, default="", description="cc-sandbox 镜像名")
    sandbox_version = fields.CharField(max_length=64, default="latest", description="镜像版本/Build Tag")

    # 容器标识（container_name 同时作为 Docker 内网 DNS 主机名）
    container_name = fields.CharField(
        max_length=64,
        unique=True,
        null=True,
        description="容器名，格式: nekro-cc-{hex8}，同时用作 Docker 内网主机名",
    )
    container_id = fields.CharField(max_length=128, null=True, description="容器 ID（运行时填充）")

    # 宿主机端口（从高位端口段随机分配，inspect 验证后写入）
    host_port = fields.IntField(null=True, description="宿主机映射端口")

    # 运行策略
    runtime_policy = fields.CharField(max_length=16, default="agent", description="运行策略: agent|relaxed|strict")

    # 运行时状态
    last_heartbeat = fields.DatetimeField(null=True, description="最近心跳时间")
    last_error = fields.TextField(null=True, description="最近错误信息")

    # 元数据（skills 列表、mcp 配置等）
    metadata = fields.JSONField(default=dict, description="元数据")

    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:  # type: ignore
        table = "workspace"

    @property
    def api_endpoint(self) -> str:
        from nekro_agent.core.config import config
        from nekro_agent.core.os_env import OsEnv

        if OsEnv.RUN_IN_DOCKER and self.container_name:
            return f"http://{self.container_name}:{config.CC_SANDBOX_INTERNAL_PORT}"
        if self.host_port:
            return f"http://127.0.0.1:{self.host_port}"
        raise ValueError(f"Workspace {self.id} 尚无可用的 API 地址")
