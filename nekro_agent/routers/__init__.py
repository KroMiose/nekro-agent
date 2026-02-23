from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles

from nekro_agent.adapters import load_adapters_api
from nekro_agent.core.args import Args
from nekro_agent.core.exception_handlers import register_exception_handlers
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.user import UserLogin, UserToken
from nekro_agent.services.user.util import user_login
from nekro_agent.tools.common_util import get_app_version

from .adapters import router as adapters_router
from .cc_model_presets import router as cc_model_presets_router
from .chat_channel import router as chat_channel_router
from .cloud.auth import router as cloud_auth_router
from .cloud.plugins_market import router as plugins_market_router
from .cloud.presets_market import router as presets_market_router
from .cloud.telemetry import router as telemetry_router
from .common import router as common_router
from .config import router as config_router
from .dashboard import router as dashboard_router
from .logs import router as logs_router
from .plugin_editor import router as plugin_editor_router
from .plugins import router as plugins_router
from .presets import router as presets_router
from .restart import router as restart_router
from .rpc import router as exec_router
from .sandbox import router as sandbox_router
from .skills import router as skills_router
from .space_cleanup import router as space_cleanup_router
from .user import router as user_router
from .user_manager import router as user_manager_router
from .webhook import router as webhook_router
from .workspaces import router as workspaces_router

# 注意：插件路由现在通过插件路由管理器动态挂载，支持热重载
# 不再使用静态路由挂载方式


def mount_middlewares(app: FastAPI):
    """挂载中间件和全局处理器"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册统一的全局异常处理器
    # 支持 AppError 业务错误、验证错误、HTTPException 及通用异常
    register_exception_handlers(app)


def mount_api_routes(app: FastAPI):
    """挂载 API 路由"""
    api = APIRouter(prefix="/api")

    api.include_router(user_router)
    api.include_router(user_manager_router)
    api.include_router(exec_router)
    api.include_router(logs_router)
    api.include_router(config_router)
    api.include_router(plugins_router)
    api.include_router(plugin_editor_router)
    api.include_router(sandbox_router)
    api.include_router(dashboard_router)
    api.include_router(chat_channel_router)
    api.include_router(webhook_router)
    api.include_router(presets_router)
    api.include_router(restart_router)
    api.include_router(telemetry_router)
    api.include_router(presets_market_router)
    api.include_router(plugins_market_router)
    api.include_router(cloud_auth_router)
    api.include_router(adapters_router)
    api.include_router(common_router)
    api.include_router(space_cleanup_router)
    api.include_router(workspaces_router)
    api.include_router(skills_router)
    api.include_router(cc_model_presets_router)

    api.include_router(load_adapters_api())

    @api.get("/health", tags=["Health"], summary="健康检查")
    async def _() -> dict:
        """测试服务是否正常运行"""
        return {"ok": True}

    @api.post("/token", response_model=UserToken, tags=["User"], summary="OpenAPI OAuth2 授权")
    async def _(form_data: OAuth2PasswordRequestForm = Depends()) -> UserToken:
        """登陆获取token"""
        return await user_login(
            UserLogin(username=form_data.username, password=form_data.password),
        )

    if Args.DOCS or OsEnv.ENABLE_OPENAPI_DOCS:
        # 挂载 API 文档
        @api.get("/docs", include_in_schema=False)
        async def custom_swagger_ui_html(request: Request):
            return get_swagger_ui_html(
                openapi_url=request.app.openapi_url,
                title="Nekro Agent API",
                oauth2_redirect_url="/api/token",
            )

        # redoc
        @api.get("/redoc", include_in_schema=False)
        async def redoc_html(request: Request):
            return get_redoc_html(
                openapi_url=request.app.openapi_url,
                title="Nekro Agent API",
            )

        @api.get("/openapi.json", include_in_schema=False)
        async def custom_openapi(request: Request):
            """生成并缓存全局 OpenAPI 文档"""
            app_instance = request.app
            # 总是重新生成，以反映动态添加/删除的路由
            openapi_schema = get_openapi(
                title="Nekro Agent API",
                version=get_app_version(),
                routes=app_instance.routes,
                description="Nekro Agent API 文档（包含动态插件路由）",
            )
            app_instance.openapi_schema = openapi_schema

            # 添加HTTP头，强制浏览器不缓存OpenAPI文档
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
            return JSONResponse(openapi_schema, headers=headers)

    app.include_router(api)

    # 🎯 正确的静态文件挂载方案：/webui + 根路径重定向
    static_dir = Path(OsEnv.STATIC_DIR)
    if static_dir.exists():
        app.mount("/webui", StaticFiles(directory=str(static_dir), html=True), name="webui")
        logger.info(f"✅ 前端静态文件已挂载到 /webui 路径: {static_dir}")

        @app.get("/", include_in_schema=False)
        async def redirect_to_webui():
            """根路径重定向到前端界面"""
            return RedirectResponse(url="/webui", status_code=302)

        @app.get("/index.html", include_in_schema=False)
        async def redirect_index_to_webui():
            """index.html 重定向到前端界面"""
            return RedirectResponse(url="/webui", status_code=302)

        logger.info("✅ 根路径重定向已配置：/ -> /webui/")
    else:
        logger.debug(f"静态文件目录不存在: {static_dir}")

    # 将 OpenAPI 文档生成和 URL 设置移到 app 上，确保全局生效
    app.openapi_url = "/api/openapi.json"
