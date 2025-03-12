import asyncio
import json
import pickle
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, Response

from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.http_exception import (
    forbidden_exception,
    not_found_exception,
    server_error_exception,
)
from nekro_agent.schemas.rpc import RPCRequest
from nekro_agent.services.message.message_service import message_service
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.plugin.schema import SandboxMethodType
from nekro_agent.services.plugin.utils import get_sandbox_method_type

router = APIRouter(prefix="/ext", tags=["Tools"])


async def verify_rpc_token(x_rpc_token: str = Header(...)):
    """验证 RPC 调用令牌"""
    if not OsEnv.RPC_SECRET_KEY or x_rpc_token != OsEnv.RPC_SECRET_KEY:
        logger.warning("非法的 RPC 调用令牌")
        raise forbidden_exception
    return True


@router.post("/rpc_exec", summary="RPC 命令执行", dependencies=[Depends(verify_rpc_token)])
async def rpc_exec(container_key: str, from_chat_key: str, data: Request) -> Response:
    try:
        rpc_request: RPCRequest = RPCRequest.model_validate(pickle.loads(await data.body()))
    except Exception as e:
        logger.error(f"解析 RPC 请求失败: {e}")
        raise server_error_exception from e

    logger.info(f"收到 RPC 执行请求: {rpc_request.method}")

    method = plugin_collector.get_method(rpc_request.method)
    if not method:
        raise not_found_exception
    method_type: SandboxMethodType = get_sandbox_method_type(method=method)

    if not method:
        raise not_found_exception

    ctx = AgentCtx(container_key=container_key, from_chat_key=from_chat_key)
    args = [ctx, *rpc_request.args] if rpc_request.args else [ctx]
    kwargs = rpc_request.kwargs or {}

    result = None

    try:
        if asyncio.iscoroutinefunction(method):
            result = await method(*args, **kwargs)
        else:
            result = method(*args, **kwargs)
    except Exception as e:
        logger.exception(f"执行 RPC 请求方法失败: {e}")
        error_message = str(e)
    else:
        error_message = ""

    if method_type in [SandboxMethodType.AGENT, SandboxMethodType.BEHAVIOR]:
        await message_service.push_system_message(chat_key=from_chat_key, agent_messages=str(result))
    if method_type == SandboxMethodType.MULTIMODAL_AGENT:
        result = f"<AGENT_RESULT>{json.dumps(result, ensure_ascii=False)}</AGENT_RESULT>"
    return Response(
        content=error_message or pickle.dumps(result),
        media_type="application/octet-stream",
        headers={"Method-Type": method_type.value, "Run-Error": "True" if error_message else "False"},
    )
