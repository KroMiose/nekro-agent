import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nekro_agent import config, logger
from nekro_agent.routers import mount_routers

app = FastAPI(
    title="Nekro agent Service",
    description="Nekro agent 后端服务",
    version="0.0.1",
    docs_url="/docs",
)

""" 跨域中间件配置 """
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mount_routers(app)


async def startup_event():
    logger.info("Nekro agent Service started")


async def shutdown_event():
    logger.info("Nekro agent Service stopped")


app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


def start():
    uvicorn.run(
        "nekro_agent.app:app",
        host=config.APP_HOST, # type: ignore
        port=config.APP_PORT, # type: ignore
        log_level=config.UVICORN_LOG_LEVEL.lower(),
    )
