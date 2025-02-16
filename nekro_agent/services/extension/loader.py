"""扩展加载器

负责扩展的加载和重载功能。
"""

import sys
from importlib import import_module, reload
from pathlib import Path
from typing import List

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import EXT_WORKDIR
from nekro_agent.tools.collector import agent_collector

from .models import ExtMetaData

# 存储已加载的扩展元数据
BUILTIN_EXT_META_DATA: List[ExtMetaData] = []
WORKDIR_EXT_META_DATA: List[ExtMetaData] = []
reloaded_modules: List[str] = []

# 初始化工作目录
ext_workdir = Path(EXT_WORKDIR)
ext_workdir.mkdir(parents=True, exist_ok=True)

# 将 ext_workdir 添加到 Python 模块搜索路径
ext_workdir_str = str(ext_workdir.absolute())
if ext_workdir_str not in sys.path:
    sys.path.insert(0, ext_workdir_str)


def init_extensions() -> None:
    """初始化并加载所有内置扩展"""
    for module_path in config.EXTENSION_MODULES:
        logger.info(f"正在加载扩展模块: {module_path}")
        try:
            module = import_module(module_path)
        except ImportError:
            logger.error(f"从 {module_path} 加载扩展模块失败")
            continue

        if hasattr(module, "__meta__"):
            module_meta_data = module.__meta__

            if isinstance(module_meta_data, ExtMetaData):
                logger.success(
                    f'从 "{module_path}" 扩展模块: "{module_meta_data.name}" by "{module_meta_data.author or "Unknown"}" 加载验证成功',
                )
                BUILTIN_EXT_META_DATA.append(module_meta_data)
            else:
                logger.warning(f'加载扩展模块: "{module_path}" 元数据格式错误')
        else:
            logger.warning(f'加载扩展模块: "{module_path}" 缺少元数据')


def reload_ext_workdir() -> List[str]:
    """重载工作目录下的所有扩展模块

    Returns:
        List[str]: 重载的模块列表
    """
    # 清空工作目录扩展元数据列表
    WORKDIR_EXT_META_DATA.clear()

    # 从所有标签中移除工作目录模块的方法
    for tag, methods in agent_collector.tag_map.items():
        # 创建一个新的集合来存储要保留的方法
        preserved_methods = {
            method
            for method in methods
            if not (hasattr(method, "__module__") and method.__module__ not in config.EXTENSION_MODULES)
        }
        agent_collector.tag_map[tag] = preserved_methods

    try:
        # 遍历 ext_workdir 目录下的所有 Python 文件
        for py_file in ext_workdir.rglob("*.py"):
            # 获取相对路径并转换为模块路径
            rel_path = py_file.relative_to(ext_workdir)
            module_path = str(rel_path.with_suffix("")).replace("/", ".")

            try:
                # 尝试导入并重载模块
                if module_path in sys.modules:
                    module = reload(sys.modules[module_path])
                else:
                    module = import_module(module_path)
                reloaded_modules.append(module_path)

                # 检查并添加模块元数据
                if hasattr(module, "__meta__"):
                    module_meta_data = module.__meta__
                    if isinstance(module_meta_data, ExtMetaData):
                        WORKDIR_EXT_META_DATA.append(module_meta_data)
                        logger.success(
                            f'从扩展工作目录加载模块: "{module_meta_data.name}" by "{module_meta_data.author or "Unknown"}" 加载验证成功',
                        )
                    else:
                        logger.warning(f'扩展工作目录模块: "{module_path}" 元数据格式错误')
                else:
                    logger.warning(f'工作目录扩展模块: "{module_path}" 缺少元数据')

                logger.success(f"重载模块成功: {module_path}")
            except Exception as e:
                logger.error(f"重载模块失败 {module_path}: {e!s}")
                continue
    except Exception as e:
        logger.error(f"重载 ext_workdir 失败: {e!s}")

    return reloaded_modules
