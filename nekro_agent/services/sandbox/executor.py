import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Dict

import aiodocker
from aiodocker.docker import DockerContainer

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import SANDBOX_SHARED_HOST_DIR, USER_UPLOAD_DIR, OsEnv
from nekro_agent.models.db_exec_code import DBExecCode

from ..ext_caller import CODE_PREAMBLE, get_api_caller_code

# 主机共享目录
HOST_SHARED_DIR = (
    Path(SANDBOX_SHARED_HOST_DIR) if SANDBOX_SHARED_HOST_DIR.startswith("/") else Path(SANDBOX_SHARED_HOST_DIR).resolve()
)
# 用户上传目录
USER_UPLOAD_DIR = Path(USER_UPLOAD_DIR) if USER_UPLOAD_DIR.startswith("/") else Path(USER_UPLOAD_DIR).resolve()

IMAGE_NAME = config.SANDBOX_IMAGE_NAME  # Docker 镜像名称
CONTAINER_SHARE_DIR = "/app/shared"  # 容器内共享目录 (读写)
CONTAINER_UPLOAD_DIR = "/app/uploads"  # 容器上传目录 (只读)
CONTAINER_WORK_DIR = "/app"  # 容器工作目录

CODE_FILENAME = "run_script.py.code"  # 要执行的代码文件名
RUN_CODE_FILENAME = "run_script.py"  # 要执行的代码文件名

API_CALLER_FILENAME = "api_caller.py.code"  # 外部 API 调用器文件名
RUN_API_CALLER_FILENAME = "api_caller.py"  # 外部 API 调用器文件名

CODE_RUN_ERROR_FLAG = "[CODE_RUN_ERROR]"  # 代码运行错误标记

EXEC_SCRIPT = f"""
rm -f {CONTAINER_WORK_DIR}/{RUN_CODE_FILENAME} &&
cp {CONTAINER_SHARE_DIR}/{CODE_FILENAME} {CONTAINER_WORK_DIR}/{RUN_CODE_FILENAME} &&
cp {CONTAINER_SHARE_DIR}/{API_CALLER_FILENAME} {CONTAINER_WORK_DIR}/{RUN_API_CALLER_FILENAME} &&
export MPLCONFIGDIR=/app/tmp/matplotlib &&
python {RUN_CODE_FILENAME}
if [ $? -ne 0 ]; then
    echo "{CODE_RUN_ERROR_FLAG}"
fi
"""

# 会话沙盒活跃时间记录表
chat_key_sandbox_map: Dict[str, float] = {}

# 会话沙盒容器记录表
chat_key_sandbox_container_map: Dict[str, DockerContainer] = {}

# 会话清理任务记录表
chat_key_sandbox_cleanup_task_map: Dict[str, asyncio.Task] = {}

# 沙盒并发限制
semaphore = asyncio.Semaphore(config.SANDBOX_MAX_CONCURRENT)


async def limited_run_code(code_text: str, from_chat_key: str, output_limit: int = 1000) -> str:
    """限制并发运行代码"""

    async with semaphore:
        return await run_code_in_sandbox(code_text, from_chat_key, output_limit)


async def run_code_in_sandbox(code_text: str, from_chat_key: str, output_limit: int) -> str:
    """在沙盒容器中运行代码并获取输出"""

    # container_key = f'{time.strftime("%Y%m%d%H%M%S")}_{os.urandom(4).hex()}'
    container_key = f"sandbox_{from_chat_key}"
    container_name = f"nekro-agent-sandbox-{container_key}-{os.urandom(4).hex()}"

    host_shared_dir = Path(HOST_SHARED_DIR / container_key)
    host_shared_dir.mkdir(parents=True, exist_ok=True)

    # 写入预置依赖代码
    api_caller_file_path = Path(host_shared_dir) / API_CALLER_FILENAME
    Path.write_text(api_caller_file_path, get_api_caller_code(container_key=container_key, from_chat_key=from_chat_key))

    # 写入要执行的代码
    code_file_path = Path(host_shared_dir) / CODE_FILENAME
    Path.write_text(code_file_path, f"{CODE_PREAMBLE.strip()}\n\n{code_text}")

    # 设置共享目录权限
    try:
        Path.chmod(host_shared_dir, 0o777)
        logger.debug(f"设置共享目录权限: {host_shared_dir} 777")
    except Exception as e:
        logger.error(f"设置共享目录权限失败: {e}")

    # 清理过期任务
    if from_chat_key in chat_key_sandbox_cleanup_task_map:
        try:
            chat_key_sandbox_cleanup_task_map[from_chat_key].cancel()
            logger.debug(f"清理过期任务: {from_chat_key}")
        except Exception as e:
            logger.error(f"清理过期任务失败: {e}")
        del chat_key_sandbox_cleanup_task_map[from_chat_key]

    # 清理过期沙盒
    if from_chat_key in chat_key_sandbox_container_map:
        try:
            await chat_key_sandbox_container_map[from_chat_key].delete()
            logger.debug(f"清理过期沙盒: {from_chat_key} | {container_name}")
        except Exception as e:
            if "404" in str(e):
                logger.debug(f"沙盒容器已不存在: {from_chat_key} | {container_name}")
            else:
                logger.error(f"清理过期沙盒失败: {e}")
        del chat_key_sandbox_container_map[from_chat_key]

    # 启动容器
    docker = aiodocker.Docker()
    container: DockerContainer = await docker.containers.run(
        name=container_name,
        config={
            "Image": IMAGE_NAME,
            "Cmd": ["bash", "-c", EXEC_SCRIPT],
            "HostConfig": {
                "Binds": [
                    f"{host_shared_dir}:{CONTAINER_SHARE_DIR}:rw",
                    f"{USER_UPLOAD_DIR}/{from_chat_key}:{CONTAINER_UPLOAD_DIR}:ro",
                ],
                "Memory": 512 * 1024 * 1024,  # 内存限制 (512MB)
                "NanoCPUs": 1000000000,  # CPU 限制 (1 core)
                "SecurityOpt": (
                    []
                    if OsEnv.RUN_IN_DOCKER
                    else [
                        # "no-new-privileges",  # 禁止提升权限
                        "apparmor=unconfined",  # 禁止 AppArmor 配置
                    ]
                ),
                "NetworkMode": "bridge",
                "ExtraHosts": ["host.docker.internal:host-gateway"],
            },
            "User": "nobody",  # 非特权用户
            "AutoRemove": True,
        },
    )
    chat_key_sandbox_container_map[from_chat_key] = container
    logger.debug(f"启动容器: {container_name} | ID: {container.id}")

    # 等待容器执行并限制时间
    output_text = await run_container_with_timeout(
        container,
        config.SANDBOX_RUNNING_TIMEOUT,
    )

    logger.debug(f"容器 {container_name} 输出: {output_text}")

    # 沙盒共享目录超过 30 分钟未活动，则自动清理
    async def cleanup_container_shared_dir(box_last_active_time):
        nonlocal from_chat_key, container
        await asyncio.sleep(30 * 60)
        if box_last_active_time == chat_key_sandbox_map.get(from_chat_key):
            try:
                shutil.rmtree(host_shared_dir)
            except Exception as e:
                logger.error(f"清理容器共享目录时发生错误: {e}")
            # 清理沙盒
            try:
                await container.delete()
            except Exception as e:
                logger.error(f"清理沙盒时发生错误: {e}")

    box_last_active_time = time.time()
    chat_key_sandbox_map[from_chat_key] = box_last_active_time
    chat_key_sandbox_cleanup_task_map[from_chat_key] = asyncio.create_task(
        cleanup_container_shared_dir(box_last_active_time),
    )

    await DBExecCode.create(
        chat_key=from_chat_key,
        code_text=code_text,
        outputs=output_text,
        success=CODE_RUN_ERROR_FLAG not in output_text,
    )

    return (
        output_text
        if len(output_text) <= output_limit
        else f"(output too long, hidden {len(output_text) - output_limit} characters)...{output_text[-output_limit:]}"
    )


async def run_container_with_timeout(container: DockerContainer, timeout: int) -> str:
    try:
        task = asyncio.create_task(asyncio.wait_for(container.wait(), timeout=timeout))
        await asyncio.wait_for(task, timeout=timeout)
        outputs = await container.log(stdout=True, stderr=True)
        await container.delete()
        logger.info(f"容器 {container.id} 运行结束退出")
    except asyncio.TimeoutError:
        logger.warning(f"容器 {container.id} 运行超过 {timeout} 秒，强制停止容器")
        outputs = await container.log(stdout=True, stderr=True)
        outputs.append(f"# This container has been killed because it exceeded the {timeout} seconds limit.")
        await container.kill()
        await container.delete()

    # 获取容器输出
    return "".join(outputs).strip()


async def cleanup_sandbox_containers():
    docker = aiodocker.Docker()
    try:
        containers = await docker.containers.list(all=True)
        for container in containers:
            container_info = await container.show()
            if IMAGE_NAME in container_info["Name"]:
                await container.kill()
                await container.delete()
                logger.info(f"已清理容器 {container_info['Name']}")
    finally:
        await docker.close()
