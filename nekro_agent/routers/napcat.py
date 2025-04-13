import asyncio
import time
from pathlib import Path
from typing import AsyncGenerator, Optional

import aiodocker
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import (
    NAPCAT_ONEBOT_ADAPTER_DIR,
    ONEBOT_ACCESS_TOKEN,
    OsEnv,
)
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.message import Ret
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.perm import Role, require_role

router = APIRouter(prefix="/napcat", tags=["NapCat"])


@router.get("/onebot-token")
@require_role(Role.Admin)
async def get_onebot_token(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取 OneBot 访问令牌"""
    if not ONEBOT_ACCESS_TOKEN:
        return Ret.success(data=None, msg="未设置 OneBot 访问令牌")
    return Ret.success(data=ONEBOT_ACCESS_TOKEN, msg="获取 OneBot 访问令牌成功")


async def get_docker():
    """获取或创建 Docker 客户端"""
    return aiodocker.Docker()


async def get_container():
    """获取 NapCat 容器实例"""
    if not config.NAPCAT_CONTAINER_NAME:
        raise HTTPException(status_code=500, detail="未设置 NapCat 容器名称")
    try:
        client = await get_docker()
        return await client.containers.get(config.NAPCAT_CONTAINER_NAME)
    except Exception as e:
        logger.error(f"获取容器失败: {e!s}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/status")
@require_role(Role.Admin)
async def get_status(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取容器状态"""
    try:
        container = await get_container()
        state = (await container.show())["State"]
        return Ret.success(
            data={
                "running": state["Running"],
                "started_at": state["StartedAt"],
            },
            msg="获取容器状态成功",
        )
    except HTTPException as e:
        return Ret.fail(e.detail)
    except Exception as e:
        logger.error(f"获取状态失败: {e!s}")
        return Ret.fail(str(e))


@router.get("/logs")
@require_role(Role.Admin)
async def get_logs(tail: Optional[int] = 100, _current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取最近的容器日志"""
    try:
        container = await get_container()
        logs = await container.log(stdout=True, stderr=True, tail=tail)
        return Ret.success(data=logs, msg="获取日志成功")
    except HTTPException as e:
        return Ret.fail(e.detail)
    except Exception as e:
        logger.error(f"获取日志失败: {e!s}")
        return Ret.fail(str(e))


@router.get("/logs/stream")
@require_role(Role.Admin)
async def stream_logs(_current_user: DBUser = Depends(get_current_active_user)) -> EventSourceResponse:
    """实时日志流"""
    try:

        async def generate() -> AsyncGenerator[str, None]:
            try:
                container = await get_container()
                # 先发送最近的日志
                initial_logs = await container.log(stdout=True, stderr=True, tail=100, timestamps=False)
                init_time = time.time()
                for log in initial_logs:
                    # if log.startswith("20"):  # 移除时间戳前缀
                    #     log = log.split("Z ", 1)[1]
                    yield log
                    await asyncio.sleep(0.01)  # 避免发送过快

                # 然后开始实时流式传输
                async for log in container.log(stdout=True, stderr=True, follow=True, since=int(init_time), timestamps=False):
                    # if log.startswith("20"):
                    #     log = log.split("Z ", 1)[1]
                    yield log
                    await asyncio.sleep(0.01)  # 避免发送过快
            except Exception as e:
                logger.error(f"日志流异常: {e!s}")
                raise

        return EventSourceResponse(generate())
    except Exception as e:
        logger.error(f"日志流异常: {e!s}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
async def restart(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """重启容器"""
    if config.BOT_QQ:
        adapter_file = Path(NAPCAT_ONEBOT_ADAPTER_DIR) / f"onebot11_{config.BOT_QQ}.json"
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
    try:
        container = await get_container()
        # 发送重启命令后立即返回，不等待重启完成
        asyncio.create_task(container.restart(timeout=30))
        return Ret.success(data=True, msg="重启命令已发送")
    except HTTPException as e:
        return Ret.fail(e.detail)
    except Exception as e:
        logger.error(f"重启失败: {e!s}")
        return Ret.fail(str(e))
