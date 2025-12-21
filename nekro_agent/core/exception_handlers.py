"""全局异常处理器

核心职责:
1. 将所有异常统一转换为标准 HTTP 响应
2. 统一记录异常日志（路由中不需要 logger.exception）
3. 根据 Accept-Language 返回本地化消息
4. 提取请求上下文用于日志追踪

使用方式:
    from nekro_agent.core.exception_handlers import register_exception_handlers
    
    app = FastAPI()
    register_exception_handlers(app)
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from nekro_agent.core.logger import logger
from nekro_agent.schemas.errors import AppError, ValidationError
from nekro_agent.schemas.i18n import SupportedLang, i18n_text


def get_request_lang(request: Request) -> SupportedLang:
    """从请求头获取语言偏好

    Args:
        request: FastAPI Request 对象

    Returns:
        解析出的语言枚举
    """
    accept_lang = request.headers.get("Accept-Language", "zh-CN")
    return SupportedLang.from_accept_language(accept_lang)


def get_request_context(request: Request) -> str:
    """提取请求上下文用于日志

    Args:
        request: FastAPI Request 对象

    Returns:
        格式化的请求上下文字符串
    """
    method = request.method
    path = request.url.path
    client = request.client.host if request.client else "unknown"
    return f"{method} {path} from {client}"


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理应用自定义业务错误

    业务错误是预期内的，根据严重程度记录不同级别日志
    """
    # 类型断言，此处理器仅处理 AppError
    assert isinstance(exc, AppError)

    lang = get_request_lang(request)
    ctx = get_request_context(request)

    if exc.http_status >= 500:
        # 500 级别：服务端错误，记录完整堆栈
        logger.exception(
            f"[{exc.get_error_name()}] {ctx} - {exc.detail or exc.get_message(lang)}",
        )
    elif exc.http_status >= 400:
        # 400 级别：客户端错误，只记录警告
        logger.warning(
            f"[{exc.get_error_name()}] {ctx} - {exc.get_message(lang)}",
        )

    return JSONResponse(
        status_code=exc.http_status,
        content=exc.to_response(lang),
    )


async def request_validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """处理 FastAPI 请求验证错误

    当请求体、查询参数等不符合 Pydantic 模型定义时触发
    """
    # 类型断言，此处理器仅处理 RequestValidationError
    assert isinstance(exc, RequestValidationError)

    lang = get_request_lang(request)
    ctx = get_request_context(request)

    # 提取所有错误信息
    errors = exc.errors()
    error_details = []
    for err in errors:
        field = ".".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        error_details.append(f"{field}: {msg}" if field else msg)

    reason = "; ".join(error_details) if error_details else "Validation error"

    logger.warning(f"[RequestValidationError] {ctx} - {reason}")

    error = ValidationError(reason=reason)
    return JSONResponse(
        status_code=error.http_status,
        content=error.to_response(lang),
    )


async def pydantic_validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """处理 Pydantic 验证错误

    当手动调用 model_validate 等方法失败时触发
    """
    # 类型断言，此处理器仅处理 PydanticValidationError
    assert isinstance(exc, PydanticValidationError)

    lang = get_request_lang(request)
    ctx = get_request_context(request)

    # 提取所有错误信息
    errors = exc.errors()
    error_details = []
    for err in errors:
        field = ".".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        error_details.append(f"{field}: {msg}" if field else msg)

    reason = "; ".join(error_details) if error_details else "Validation error"

    logger.warning(f"[PydanticValidationError] {ctx} - {reason}")

    error = ValidationError(reason=reason)
    return JSONResponse(
        status_code=error.http_status,
        content=error.to_response(lang),
    )


async def http_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """处理 FastAPI/Starlette 原生 HTTPException

    兼容已有的 HTTPException 用法，逐步迁移到 AppError
    """
    # 类型断言，此处理器仅处理 StarletteHTTPException
    assert isinstance(exc, StarletteHTTPException)

    ctx = get_request_context(request)

    logger.warning(f"[HTTPException] {ctx} - {exc.status_code}: {exc.detail}")

    # 构建与 AppError 兼容的响应格式
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "message": str(exc.detail),
            "detail": None,
            "data": None,
        },
    )


# 通用错误消息（用于兜底）
_GENERIC_ERROR_MESSAGE = i18n_text(
    zh_CN="服务器内部错误",
    en_US="Internal server error",
)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的异常

    这是最后的兜底，所有未被捕获的异常都会到这里
    必须记录完整堆栈，便于排查问题
    """
    lang = get_request_lang(request)
    ctx = get_request_context(request)

    # 记录完整异常堆栈 - 这是唯一需要 logger.exception 的地方
    logger.exception(f"[UnhandledException] {ctx} - {type(exc).__name__}: {exc}")

    # 生产环境不暴露详细错误信息
    # 使用枚举的字符串值作为键
    message = _GENERIC_ERROR_MESSAGE.get(lang.value, "Internal server error")

    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": message,
            "detail": None,
            "data": None,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册异常处理器到 FastAPI 应用

    处理器注册顺序很重要：
    1. 具体异常类型优先匹配
    2. Exception 作为最后兜底

    Args:
        app: FastAPI 应用实例
    """
    # 自定义业务错误
    app.add_exception_handler(AppError, app_error_handler)

    # FastAPI 请求验证错误
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)

    # Pydantic 验证错误
    app.add_exception_handler(PydanticValidationError, pydantic_validation_error_handler)

    # 原生 HTTPException（兼容现有代码）
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 兜底：所有未处理的异常
    app.add_exception_handler(Exception, generic_exception_handler)

