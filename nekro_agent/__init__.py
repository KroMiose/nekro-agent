import sys
import threading

from nonebot import get_app, get_driver
from nonebot.plugin import PluginMetadata
from pydantic import BaseModel

import nekro_agent.core.bot
import nekro_agent.matchers
from nekro_agent.core.args import Args
from nekro_agent.core.config import config
from nekro_agent.core.logger import logger
from nekro_agent.routers import mount_routers

from .app import start


class _Config(BaseModel):
    pass


mount_routers(get_app())


__plugin_meta__ = PluginMetadata(
    name="nekro-agent",
    description="",
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
