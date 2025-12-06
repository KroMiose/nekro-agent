import asyncio
<<<<<<< HEAD
import json
=======
<<<<<<< HEAD
import json
=======
<<<<<<< HEAD
import json
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
import time
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator, Optional

import aiodocker
from aiodocker.containers import DockerContainer
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from nekro_agent.adapters.utils import adapter_utils
from nekro_agent.core.config import config as core_config
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

router = APIRouter(prefix="/container", tags=["OneBot V11 Container"])


@router.get("/onebot-token")
@require_role(Role.Admin)
async def get_onebot_token(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取 OneBot 访问令牌"""
    if not ONEBOT_ACCESS_TOKEN:
        return Ret.success(data=None, msg="未设置 OneBot 访问令牌")
    return Ret.success(data=ONEBOT_ACCESS_TOKEN, msg="获取 OneBot 访问令牌成功")


<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
@router.get("/napcat-token")
@require_role(Role.Admin)
async def get_napcat_token(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    """获取 NapCat WebUI 访问令牌

    通过读取宿主机上挂载的 NapCat 配置文件来获取 WebUI token。
    配置文件路径: ${DATA_DIR}/napcat_data/napcat/webui.json
    """
    try:
        # 检查容器状态
        try:
            container = await get_container()
            state = (await container.show())["State"]
            if not state["Running"]:
                return Ret.fail("NapCat 容器未运行")
        except Exception as e:
            logger.warning(f"无法获取容器状态: {e!s}")
            return Ret.fail("无法连接到 NapCat 容器")

        # 构建配置文件路径（从宿主机读取）
        from nekro_agent.core.os_env import OsEnv

        config_file_path = Path(OsEnv.DATA_DIR) / "napcat_data" / "napcat" / "webui.json"

        # 检查文件是否存在
        if not config_file_path.exists():
            logger.error(f"配置文件不存在: {config_file_path}")
            return Ret.fail("配置文件不存在，请确保 NapCat 已完成初始化")

        # 读取配置文件
        try:
            config_text = config_file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"读取配置文件失败: {e!s}")
            return Ret.fail("读取配置文件失败")

        # 解析 JSON 并提取 token
        try:
            config_data = json.loads(config_text)
            token = config_data.get("token")

            if not token:
                return Ret.fail("配置文件中未找到 token 字段")

            return Ret.success(data=token, msg="获取 NapCat WebUI 访问令牌成功")
        except json.JSONDecodeError as e:
            logger.error(f"解析 NapCat 配置文件失败: {e!s}")
            return Ret.fail("配置文件格式错误，请检查 JSON 格式是否正确")

    except Exception as e:
        logger.error(f"获取 NapCat WebUI 令牌失败: {e!s}")
        return Ret.fail(f"获取令牌失败: {e!s}")


<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
=======
>>>>>>> 6cf9d37 (增加PYPI源自定义和代理功能)
>>>>>>> a776096 (增加PYPI源自定义和代理功能)
>>>>>>> e26199f (增加PYPI源自定义和代理功能)
async def get_docker():
    """获取或创建 Docker 客户端"""
    return aiodocker.Docker()


async def get_container() -> DockerContainer:
    """获取 NapCat 容器实例"""
    from nekro_agent.adapters.onebot_v11.adapter import OnebotV11Adapter

    adapter = adapter_utils.get_typed_adapter("onebot_v11", OnebotV11Adapter)

    if not adapter.config.NAPCAT_CONTAINER_NAME:
        raise HTTPException(status_code=500, detail="未设置 NapCat 容器名称")
    try:
        client = await get_docker()
        return await client.containers.get(adapter.config.NAPCAT_CONTAINER_NAME)
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
                    yield log
                    await asyncio.sleep(0.01)  # 避免发送过快

                # 然后开始实时流式传输
                async for log in container.log(stdout=True, stderr=True, follow=True, since=int(init_time), timestamps=False):
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
