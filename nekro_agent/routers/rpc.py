import asyncio
import pickle
from typing import Any

from fastapi import APIRouter, Request, Response

from nekro_agent.core.logger import logger
from nekro_agent.schemas.http_exception import (
    not_found_exception,
    server_error_exception,
)
from nekro_agent.schemas.rpc import RPCRequest
from nekro_agent.tools.collector import agent_collector

router = APIRouter(prefix="/ext", tags=["Tools"])


@router.post("/rpc_exec", summary="RPC 命令执行")
async def rpc_exec(data: Request) -> Response:
    try:
        rpc_request: RPCRequest = RPCRequest.model_validate(pickle.loads(await data.body()))
    except Exception as e:
        logger.error(f"解析 RPC 请求失败: {e}")
        raise server_error_exception from e

    logger.info(f"收到 RPC 执行请求: {rpc_request.method}")

    method = agent_collector.get_method(rpc_request.method)

    if not method:
        raise not_found_exception

    args = rpc_request.args or []
    kwargs = rpc_request.kwargs or {}

    if asyncio.iscoroutinefunction(method):
        result = await method(*args, **kwargs)
    else:
        result = method(*args, **kwargs)
    return Response(content=pickle.dumps(result), media_type="application/octet-stream")
