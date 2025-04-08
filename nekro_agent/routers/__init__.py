from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles

from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.message import Ret
from nekro_agent.schemas.user import UserLogin, UserToken
from nekro_agent.services.user.util import user_login

from .chat_channel import router as chat_channel_router
from .cloud.plugins_market import router as plugins_market_router
from .cloud.presets_market import router as presets_market_router
from .cloud.telemetry import router as telemetry_router
from .config import router as config_router
from .dashboard import router as dashboard_router
from .logs import router as logs_router
from .napcat import router as napcat_router
from .plugin_editor import router as plugin_editor_router
from .plugins import router as plugins_router
from .presets import router as presets_router
from .rpc import router as exec_router
from .sandbox import router as sandbox_router
from .user import router as user_router
from .user_manager import router as user_manager_router
from .webhook import router as webhook_router


def mount_routers(app: FastAPI):
    """挂载 API 路由"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):  # noqa: ARG001
        """全局异常处理器"""
        logger.exception(f"服务器错误: {exc}")
        return JSONResponse(
            status_code=500,
            content=Ret.error(msg=str(exc)).model_dump(),
        )

    api = APIRouter(prefix="/api")

    api.include_router(user_router)
    api.include_router(user_manager_router)
    api.include_router(exec_router)
    api.include_router(logs_router)
    api.include_router(config_router)
    api.include_router(plugins_router)
    api.include_router(plugin_editor_router)
    api.include_router(napcat_router)
    api.include_router(sandbox_router)
    api.include_router(dashboard_router)
    api.include_router(chat_channel_router)
    api.include_router(webhook_router)
    api.include_router(presets_router)
    api.include_router(telemetry_router)
    api.include_router(presets_market_router)
    api.include_router(plugins_market_router)

    @api.get("/health", response_model=Ret, tags=["Health"], summary="健康检查")
    async def _() -> Ret:
        """测试服务是否正常运行"""
        return Ret.success(msg="Nekro agent Service Running...")

    @api.post("/token", response_model=UserToken, tags=["User"], summary="OpenAPI OAuth2 授权")
    async def _(form_data: OAuth2PasswordRequestForm = Depends()) -> UserToken:
        """登陆获取token"""
        return await user_login(
            UserLogin(username=form_data.username, password=form_data.password),
        )

    # 生成 OpenAPI 文档
    @api.get("/openapi.json", include_in_schema=False)
    async def openapi():
        openapi_schema = get_openapi(
            title="Nekro Agent API",
            version="0.1.0",
            routes=api.routes,
            description="Nekro Agent API 文档",
        )
        return JSONResponse(openapi_schema)

    # 挂载 API 文档
    @api.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url="/api/openapi.json",
            title="Nekro Agent API",
            oauth2_redirect_url="/api/token",
        )

    # redoc
    @api.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url="/api/openapi.json",
            title="Nekro Agent API",
        )

    app.include_router(api)

    # 挂载静态文件
    static_dir = Path(OsEnv.STATIC_DIR)
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
