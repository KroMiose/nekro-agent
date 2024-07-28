from fastapi import APIRouter, Depends, FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from nekro_agent.schemas.message import Ret
from nekro_agent.schemas.user import UserLogin, UserToken
from nekro_agent.services.user import user_login

from .rpc import router as exec_router
from .tools import router as tools_router
from .user import router as user_router


def mount_routers(app: FastAPI):

    api = APIRouter(prefix="/api")

    api.include_router(user_router)
    api.include_router(tools_router)
    api.include_router(exec_router)

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

    app.include_router(api)
