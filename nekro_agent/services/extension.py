from importlib import import_module
from typing import Optional

from pydantic import BaseModel

from nekro_agent.core.config import config
from nekro_agent.core.logger import logger


class ExtMetaData(BaseModel):
    name: str
    version: str
    author: str
    author_email: Optional[str] = None
    description: str
    url: Optional[str] = None
    license: Optional[str] = None


def init_extensions():
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

            else:
                logger.warning(f'加载扩展模块: "{module_path}" 元数据格式错误')

        else:
            logger.warning(f'加载扩展模块: "{module_path}" 缺少元数据')
