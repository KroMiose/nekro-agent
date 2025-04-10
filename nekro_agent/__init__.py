import logging

import weave
from nonebot import get_app, get_driver
from nonebot.adapters.onebot.v11 import Bot
from nonebot.plugin import PluginMetadata
from pydantic import BaseModel

import nekro_agent.core.bot
import nekro_agent.matchers
from nekro_agent.core.args import Args
from nekro_agent.core.config import config
from nekro_agent.core.database import init_db
from nekro_agent.core.logger import logger
from nekro_agent.models.db_chat_channel import DBChatChannel
from nekro_agent.routers import mount_routers
from nekro_agent.services.festival_service import festival_service
from nekro_agent.services.mail.mail_service import send_bot_status_email

# from nekro_agent.services.extension import init_extensions, reload_ext_workdir
from nekro_agent.services.plugin.collector import init_plugins
from nekro_agent.services.timer_service import timer_service
from nekro_agent.systems.cloud.scheduler import start_telemetry_task

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
# init_extensions()
# reload_ext_workdir()


@get_driver().on_startup
async def on_startup():
    await init_db()
    await init_plugins()
    await timer_service.start()
    logger.info("Timer service initialized")

    # 初始化节日提醒
    await festival_service.init_festivals()
    logger.info("Festival service initialized")

    # 遥测任务
    start_telemetry_task()


@get_driver().on_shutdown
async def on_shutdown():
    await timer_service.stop()
    logger.info("Timer service stopped")


@get_driver().on_bot_connect
async def on_bot_connect(bot: Bot):
    adapter: str = bot.adapter.get_name()
    bot_id: str = bot.self_id
    await send_bot_status_email(adapter, bot_id, True)


@get_driver().on_bot_disconnect
async def on_bot_disconnect(bot: Bot):
    adapter: str = bot.adapter.get_name()
    bot_id: str = bot.self_id
    await send_bot_status_email(adapter, bot_id, False)


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
