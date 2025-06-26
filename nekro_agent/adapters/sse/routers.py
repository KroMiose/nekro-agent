"""
SSE 路由模块
==========

负责注册和挂载SSE协议的FastAPI路由。
"""

import inspect
import uuid
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Body, Header, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from nekro_agent.adapters.utils import adapter_utils
from nekro_agent.core import logger

from .commands import (
    _command_handlers,
    _command_models,
    set_client_manager,
)
from .core.client import SseClient, SseClientManager, sse_stream

# 全局客户端管理器 - 将由 mount_adapter_router 初始化
client_manager: Optional[SseClientManager] = None


# 设置client_manager的函数，在路由挂载时调用
def set_router_client_manager(manager: SseClientManager) -> None:
    """设置路由使用的客户端管理器

    Args:
        manager: 客户端管理器实例
    """
    global client_manager
    client_manager = manager
    # 同时也设置commands.py中的client_manager
    set_client_manager(manager)


def create_sse_response(request: Request, client: Union[SseClient, str]) -> EventSourceResponse:
    """创建SSE响应

    Args:
        request: 请求对象
        client: 客户端实例或客户端名称

    Returns:
        EventSourceResponse: SSE响应对象
    """
    assert client_manager is not None, "客户端管理器未初始化"
    # 如果是字符串，则创建新客户端
    if isinstance(client, str):
        existing_client = client_manager.get_client_by_name(client)
        client = existing_client or client_manager.register_client(client)

    # 返回SSE响应
    return EventSourceResponse(sse_stream(request, client))


router = APIRouter()


# 辅助函数，用于抽象化异常抛出
def _raise_http_exception(status_code: int, detail: str) -> None:
    """抛出HTTP异常

    Args:
        status_code: HTTP状态码
        detail: 异常详情
    """
    raise HTTPException(status_code=status_code, detail=detail)


@router.post("/connect")
async def command_endpoint(
    command_payload: Dict[str, Any] = Body(...),
    client_id_header: Optional[str] = Header(None, alias="X-Client-ID"),
    access_key_header: Optional[str] = Header(None, alias="X-Access-Key"),
):
    """命令处理端点"""
    # 访问密钥校验
    sse_adapter = adapter_utils.get_adapter("sse")
    if sse_adapter.config.ACCESS_KEY and access_key_header != sse_adapter.config.ACCESS_KEY:
        _raise_http_exception(401, "无效的访问密钥")

    cmd = command_payload.get("cmd")
    if not cmd:
        raise HTTPException(status_code=400, detail="缺少cmd字段")

    logger.info(f"收到命令: {cmd} (Client-ID: {client_id_header})")

    handler = _command_handlers.get(cmd)
    if not handler:
        raise HTTPException(status_code=400, detail=f"未知命令: {cmd}")

    try:
        model_cls = _command_models.get(cmd)
        # 使用 pydantic 模型验证和转换数据
        command_data_obj = model_cls(**command_payload) if model_cls else command_payload

        sig = inspect.signature(handler)
        params_for_handler: Dict[str, Any] = {}

        if "command" in sig.parameters:
            params_for_handler["command"] = command_data_obj

        current_cmd_client_id = client_id_header  # 使用从header获取的ID

        # 仅当处理器需要 client_id 时才传递
        if "client_id" in sig.parameters:
            # 对于非注册命令，如果处理器需要 client_id 但未提供，则报错
            if not current_cmd_client_id and cmd != "register":
                _raise_http_exception(400, f"命令 '{cmd}' 需要 X-Client-ID 请求头")
            params_for_handler["client_id"] = current_cmd_client_id

        # 更新心跳 (使用已设置为 adapter.client_manager 的模块级 client_manager)
        if current_cmd_client_id and client_manager:
            client_obj = client_manager.get_client(current_cmd_client_id)
            if client_obj:
                client_obj.update_heartbeat()
            elif cmd != "register":  # 如果不是注册，但客户端不存在，可能记录一个警告
                logger.warning(f"Command '{cmd}' from unknown client_id: {current_cmd_client_id}")

        # 确保客户端管理器已初始化
        if client_manager is None and cmd == "register":
            _raise_http_exception(500, "SSE服务未正确初始化，客户端管理器未设置")

        return await handler(**params_for_handler)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"处理命令失败: {cmd}, 错误: {e!r}")
        raise HTTPException(status_code=500, detail=f"处理 {cmd} 命令失败: {e!s}") from e


@router.get("/connect")
async def sse_endpoint(
    request: Request,
    client_name: str = "",
    client_id_query: Optional[str] = None,  # 名称区分来自查询参数
    platform: str = "unknown",
    access_key: Optional[str] = None,
):
    """SSE 连接端点"""
    # 访问密钥校验
    sse_adapter = adapter_utils.get_adapter("sse")
    if sse_adapter.config.ACCESS_KEY and access_key != sse_adapter.config.ACCESS_KEY:
        logger.error("SSE 连接失败: 无效的访问密钥。")
        raise HTTPException(status_code=401, detail="无效的访问密钥")

    if not client_manager:
        logger.error("SSE 连接失败: client_manager 未初始化。请检查 SSEAdapter 初始化流程。")
        raise HTTPException(status_code=500, detail="SSE 服务内部错误，未能正确初始化。")

    active_client: SseClient
    effective_client_id = client_id_query

    if effective_client_id:
        client_from_manager = client_manager.get_client(effective_client_id)
        if client_from_manager:
            active_client = client_from_manager
            # 只更新心跳，不更新平台信息
            active_client.update_heartbeat()
            logger.info(f"SSE客户端重连: ID={effective_client_id}, Name='{client_from_manager.name}', Platform='{platform}'")
        else:
            # 如果提供了ID但找不到，则用此ID注册新客户端
            # client_name 优先使用查询参数，其次用ID做名称
            name_for_new_client = client_name or effective_client_id
            active_client = client_manager.register_client(name_for_new_client, platform)
            logger.info(
                f"SSE新客户端注册 (通过ID): ID={effective_client_id}, Name='{name_for_new_client}', Platform='{platform}'",
            )
    else:
        # 没有提供client_id，基于client_name注册新客户端
        if not client_name:  # 如果连name都没有，就生成一个
            client_name = f"sse-client-{uuid.uuid4().hex[:8]}"
            logger.info(f"SSE客户端名称未提供，已自动生成: {client_name}")
        active_client = client_manager.register_client(client_name, platform)
        logger.info(f"SSE新客户端注册: Name='{client_name}', Platform='{platform}', Assigned ID='{active_client.client_id}'")

    # 更新心跳，确保客户端活跃
    active_client.update_heartbeat()
    return EventSourceResponse(sse_stream(request, active_client))


logger.info("SSE Router mounted on adapter.router and using adapter.client_manager!")
