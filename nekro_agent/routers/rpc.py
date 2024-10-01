import asyncio
import pickle
from typing import Any

from fastapi import APIRouter, Request, Response

from nekro_agent.core.logger import logger
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.schemas.http_exception import (
    not_found_exception,
    server_error_exception,
)
from nekro_agent.schemas.rpc import RPCRequest
from nekro_agent.systems.message.push_bot_msg import push_system_message
from nekro_agent.tools.collector import MethodType, agent_collector

router = APIRouter(prefix="/ext", tags=["Tools"])


@router.post("/rpc_exec", summary="RPC 命令执行")
async def rpc_exec(container_key: str, from_chat_key: str, data: Request) -> Response:
    try:
        rpc_request: RPCRequest = RPCRequest.model_validate(pickle.loads(await data.body()))
    except Exception as e:
        logger.error(f"解析 RPC 请求失败: {e}")
        raise server_error_exception from e

    logger.info(f"收到 RPC 执行请求: {rpc_request.method}")

    method = agent_collector.get_method(rpc_request.method)
    if not method:
        raise not_found_exception
    method_type: MethodType = agent_collector.get_method_type(method=method)

    if not method:
        raise not_found_exception

    args = rpc_request.args or []
    kwargs = rpc_request.kwargs or {}
    ctx = AgentCtx(container_key=container_key, from_chat_key=from_chat_key)
    kwargs["_ctx"] = ctx

    result = None

    try:
        if asyncio.iscoroutinefunction(method):
            result = await method(*args, **kwargs)
        else:
            result = method(*args, **kwargs)
    except Exception as e:
        logger.error(f"执行 RPC 请求失败: {e}")
        error_message = str(e)
    else:
        error_message = ""

    if method_type in [MethodType.BEHAVIOR, MethodType.AGENT]:
        await push_system_message(chat_key=from_chat_key, agent_messages=str(result))
    return Response(
        content=error_message or pickle.dumps(result),
        media_type="application/octet-stream",
        headers={"Method-Type": method_type.value, "Run-Error": "True" if error_message else "False"},
    )
