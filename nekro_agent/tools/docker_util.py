import asyncio

import aiodocker
from aiodocker.docker import DockerContainer

from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv


async def get_docker_client() -> aiodocker.Docker:
    """获取Docker客户端"""
    return aiodocker.Docker()


async def get_container(container_name: str) -> DockerContainer:
    """获取指定名称的容器实例

    Args:
        container_name: 容器名称

    Returns:
        DockerContainer: 容器实例

    Raises:
        Exception: 获取容器失败时抛出异常
    """
    try:
        docker = await get_docker_client()
        return await docker.containers.get(container_name)
    except Exception as e:
        logger.error(f"获取容器失败: {e!s}")
        raise


async def get_self_container() -> DockerContainer:
    """获取当前应用所在的容器实例

    Returns:
        DockerContainer: 当前应用容器实例

    Raises:
        Exception: 获取容器失败时抛出异常
    """
    # 从环境变量中获取实例名称前缀
    instance_name = OsEnv.INSTANCE_NAME
    # 构建完整的容器名称
    container_name = f"{instance_name}nekro_agent"
    if not instance_name:
        raise RuntimeError("未设置实例名称")
    try:
        docker = await get_docker_client()
        return await docker.containers.get(container_name)
    except Exception as e:
        logger.error(f"获取自身容器失败: {e!s}")
        raise


async def restart_self(timeout: int = 30) -> bool:
    """重启自身容器

    Args:
        timeout: 重启超时时间(秒)

    Returns:
        bool: 是否成功发送重启命令
    """
    if not OsEnv.RUN_IN_DOCKER:
        raise RuntimeError("当前应用未在 Docker 中运行")
    container = await get_self_container()
    try:
        # 创建任务但不等待完成
        asyncio.create_task(container.restart(timeout=timeout))
    except Exception as e:
        logger.error(f"重启自身容器失败: {e!s}")
        return False
    else:
        return True


async def restart_container(container_id_or_name: str, timeout: int = 30) -> bool:
    """重启指定容器

    Args:
        container_id_or_name: 容器ID或名称
        timeout: 重启超时时间(秒)

    Returns:
        bool: 是否成功重启
    """
    try:
        docker = await get_docker_client()
        container = await docker.containers.get(container_id_or_name)
        await container.restart(timeout=timeout)
    except Exception as e:
        logger.error(f"重启容器失败: {e!s}")
        return False
    else:
        return True
