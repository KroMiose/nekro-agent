import hashlib
import os
import platform
import socket
import uuid
from pathlib import Path
from typing import Dict, Optional

from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv


def is_running_in_docker() -> bool:
    """检查是否在Docker容器中运行

    Returns:
        bool: 如果在Docker中运行，则返回True，否则返回False
    """
    return bool(OsEnv.RUN_IN_DOCKER)


def get_system_info() -> Dict[str, str]:
    """获取系统信息

    Returns:
        Dict[str, str]: 系统信息字典
    """
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "system": platform.system(),
        "release": platform.release(),
    }


_INSTANCE_ID: Optional[str] = None


def generate_instance_id() -> str:
    """生成实例唯一ID

    基于当前系统环境和硬件信息生成一个唯一ID

    Returns:
        str: 实例唯一ID
    """
    global _INSTANCE_ID
    if _INSTANCE_ID is not None:
        return _INSTANCE_ID

    # 收集环境信息
    system_info = get_system_info()

    # 获取cpu信息
    try:
        import psutil

        cpu_count = psutil.cpu_count()
        memory_info = str(psutil.virtual_memory().total)
    except ImportError:
        logger.warning("psutil库未安装，无法获取详细硬件信息")
        cpu_count = os.cpu_count() or 0
        memory_info = "unknown"

    # 获取环境变量指纹
    env_keys = sorted(os.environ.keys())
    env_fingerprint = ",".join(env_keys)

    # 获取计算机UUID（如有）
    computer_id = ""
    try:
        if platform.system() == "Windows":
            computer_id = os.popen("wmic csproduct get uuid").read()
        elif platform.system() == "Linux":
            with Path("/var/lib/dbus/machine-id").open() as f:
                computer_id = f.read()
        elif platform.system() == "Darwin":  # macOS
            computer_id = os.popen('ioreg -rd1 -c IOPlatformExpertDevice | grep -i "UUID" | cut -c27-62').read()
    except:
        computer_id = str(uuid.getnode())  # 使用网卡MAC地址的整数表示作为备选

    # 组合所有信息
    fingerprint = (
        f"{system_info['hostname']}|"
        f"{system_info['platform']}|"
        f"{computer_id}|"
        f"{cpu_count}|"
        f"{memory_info}|"
        f"{env_fingerprint}"
    )

    # 生成 SHA256 哈希
    instance_id = hashlib.sha256(fingerprint.encode()).hexdigest()
    _INSTANCE_ID = instance_id
    return instance_id
