import logging
import os
import threading

import weave
from nonebot import get_app, get_driver
from nonebot.plugin import PluginMetadata
from pydantic import BaseModel

import nekro_agent.core.bot
import nekro_agent.matchers
from nekro_agent.core.args import Args
from nekro_agent.core.config import config
from nekro_agent.core.database import init_db
from nekro_agent.core.logger import logger
from nekro_agent.routers import mount_routers
from nekro_agent.services.extension import init_extensions

from .app import start

logging.getLogger("passlib").setLevel(logging.ERROR)


class _Config(BaseModel):
    pass


if config.WEAVE_ENABLED:
    logger.info("正在连接 Weave 服务...")
    try:
        weave.init(config.WEAVE_PROJECT_NAME)
        logger.success("Weave 服务连接成功")
    except Exception as e:
        logger.error(f"Weave 服务连接失败: {e}")

mount_routers(get_app())
init_extensions()


@get_driver().on_startup
async def on_startup():
    await init_db()


__plugin_meta__ = PluginMetadata(
    name="nekro-agent",
    description="集代码执行/高度可扩展性为一体的聊天机器人，应用了容器化技术快速构建沙盒环境",
    usage="",
    type="application",
    homepage="https://github.com/KroMiose/nekro-agent",
    supported_adapters={"~onebot.v11"},
    config=_Config,
)

global_config = get_driver().config


# 启动 Api 服务进程
# threading.Thread(target=start, daemon=True).start()

if Args.LOAD_TEST:
    logger.success("Plugin load tested successfully")
    exit(0)
