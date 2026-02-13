import asyncio
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator, Optional


import aiodocker
from aiodocker.containers import DockerContainer
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from nekro_agent.adapters.utils import adapter_utils
from nekro_agent.core.config import config as core_config
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import (

    NAPCAT_ONEBOT_ADAPTER_DIR,
    ONEBOT_ACCESS_TOKEN,
    OsEnv,
)
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import NotFoundError, OperationFailedError, ValidationError
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

logger = get_sub_logger("adapter.onebot_v11")
if TYPE_CHECKING:
    from nekro_agent.adapters.onebot_v11.adapter import OnebotV11Adapter

router = APIRouter(prefix="/container", tags=["OneBot V11 Container"])


class TokenResponse(BaseModel):
    token: Optional[str]


class ContainerStatus(BaseModel):
    running: bool
    started_at: str


class ActionResponse(BaseModel):
    ok: bool = True


@router.get("/onebot-token")
@require_role(Role.Admin)
async def get_onebot_token(_current_user: DBUser = Depends(get_current_active_user)) -> TokenResponse:
    """获取 OneBot 访问令牌"""
    return TokenResponse(token=ONEBOT_ACCESS_TOKEN or None)


@router.get("/napcat-token")
@require_role(Role.Admin)
async def get_napcat_token(_current_user: DBUser = Depends(get_current_active_user)) -> TokenResponse:
    """获取 NapCat WebUI 访问令牌"""
    try:
        container = await get_container()
        state = (await container.show())["State"]
        if not state["Running"]:
            raise OperationFailedError(operation="获取 NapCat WebUI 访问令牌")

        config_file_path = Path(OsEnv.DATA_DIR) / "napcat_data" / "napcat" / "webui.json"
        if not config_file_path.exists():
            raise NotFoundError(resource="NapCat 配置文件")

        config_text = config_file_path.read_text(encoding="utf-8")
        try:
            config_data = json.loads(config_text)
        except json.JSONDecodeError as e:
            raise ValidationError(reason="配置文件格式错误") from e

        token = config_data.get("token")
        if not token:
            raise ValidationError(reason="配置文件中未找到 token 字段")

        return TokenResponse(token=token)
    except (NotFoundError, ValidationError, OperationFailedError):
        raise
    except Exception as e:
        logger.warning(f"无法获取容器状态: {e!s}")
        raise OperationFailedError(operation="获取 NapCat WebUI 访问令牌") from e


async def get_docker():
    """获取或创建 Docker 客户端"""
    return aiodocker.Docker()


async def get_container() -> DockerContainer:
    """获取 NapCat 容器实例"""
    from nekro_agent.adapters.onebot_v11.adapter import OnebotV11Adapter

    adapter = adapter_utils.get_typed_adapter("onebot_v11", OnebotV11Adapter)

    if not adapter.config.NAPCAT_CONTAINER_NAME:
        raise ValidationError(reason="未设置 NapCat 容器名称")
    try:
        client = await get_docker()
        return await client.containers.get(adapter.config.NAPCAT_CONTAINER_NAME)
    except Exception as e:
        logger.error(f"获取容器失败: {e!s}")
        raise OperationFailedError(operation="获取容器") from e


@router.get("/status")
@require_role(Role.Admin)
async def get_status(_current_user: DBUser = Depends(get_current_active_user)) -> ContainerStatus:
    """获取容器状态"""
    container = await get_container()
    state = (await container.show())["State"]
    return ContainerStatus(
        running=state["Running"],
        started_at=state["StartedAt"],
    )


@router.get("/logs")
@require_role(Role.Admin)
async def get_logs(tail: Optional[int] = 100, _current_user: DBUser = Depends(get_current_active_user)) -> list[str]:
    """获取最近的容器日志"""
    container = await get_container()
    logs = await container.log(stdout=True, stderr=True, tail=tail)
    return logs


@router.get("/logs/stream")
@require_role(Role.Admin)
async def stream_logs(_current_user: DBUser = Depends(get_current_active_user)) -> EventSourceResponse:
    """实时日志流"""

    async def generate() -> AsyncGenerator[str, None]:
        container = await get_container()
        initial_logs = await container.log(stdout=True, stderr=True, tail=100, timestamps=False)
        init_time = time.time()
        for log in initial_logs:
            yield log
            await asyncio.sleep(0.01)

        async for log in container.log(stdout=True, stderr=True, follow=True, since=int(init_time), timestamps=False):
            yield log
            await asyncio.sleep(0.01)

    return EventSourceResponse(generate())


ADAPTER_TEMPLATE = """
{{
  "network": {{
    "httpServers": [],
    "httpSseServers": [],
    "httpClients": [],
    "websocketServers": [],
    "websocketClients": [
      {{
        "enable": true,
        "name": "ws",
        "url": "ws://{instance_name}:{port}/onebot/v11/ws",
        "reportSelfMessage": false,
        "messagePostFormat": "array",
        "token": "{token}",
        "debug": false,
        "heartInterval": 30000,
        "reconnectInterval": 3000
      }}
    ],
    "plugins": []
  }},
  "musicSignUrl": "",
  "enableLocalFile2Url": false,
  "parseMultMsg": false
}}
""".strip()


@router.post("/restart")
@require_role(Role.Admin)
async def restart(_current_user: DBUser = Depends(get_current_active_user)) -> ActionResponse:
    """重启容器"""
    from nekro_agent.adapters.onebot_v11.adapter import OnebotV11Adapter

    adapter = adapter_utils.get_typed_adapter("onebot_v11", OnebotV11Adapter)
    if adapter.config.BOT_QQ:
        adapter_file = Path(NAPCAT_ONEBOT_ADAPTER_DIR) / f"onebot11_{adapter.config.BOT_QQ}.json"
        if not adapter_file.exists():
            logger.info(f"未找到适配器文件: {adapter_file}, 自动创建...")
            adapter_file.write_text(
                ADAPTER_TEMPLATE.format(
                    token=ONEBOT_ACCESS_TOKEN,
                    instance_name=OsEnv.INSTANCE_NAME,
                    port=OsEnv.EXPOSE_PORT,
                ),
                encoding="utf-8",
            )
    container = await get_container()
    asyncio.create_task(container.restart(timeout=30))
    return ActionResponse(ok=True)
