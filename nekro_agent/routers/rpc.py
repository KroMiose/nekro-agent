import json
import pickle

from fastapi import APIRouter, Depends, Header, Request, Response

from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.schemas.errors import NotFoundError, UnauthorizedError
from nekro_agent.schemas.rpc import RPCRequest
from nekro_agent.services.message_service import message_service
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.plugin.schema import SandboxMethodType
from nekro_agent.services.plugin.utils import get_sandbox_method_type
from nekro_agent.services.rpc_service import decode_rpc_request, execute_rpc_method

logger = get_sub_logger("rpc_bridge")
router = APIRouter(prefix="/ext", tags=["Tools"])


async def verify_rpc_token(x_rpc_token: str = Header(...)):
    """验证 RPC 调用令牌"""
    if not OsEnv.RPC_SECRET_KEY or x_rpc_token != OsEnv.RPC_SECRET_KEY:
        logger.warning("非法的 RPC 调用令牌")
        raise UnauthorizedError
    return True


@router.post("/rpc_exec", summary="RPC 命令执行", dependencies=[Depends(verify_rpc_token)])
async def rpc_exec(container_key: str, from_chat_key: str, data: Request) -> Response:
    rpc_request: RPCRequest = decode_rpc_request(await data.body())

    logger.info(f"收到 RPC 执行请求: {rpc_request.method}")

    method = plugin_collector.get_method(rpc_request.method)
    if not method:
        raise NotFoundError(resource="RPC 方法")
    method_type: SandboxMethodType = get_sandbox_method_type(method=method)

    if not method:
        raise NotFoundError(resource="RPC 方法")

    ctx: AgentCtx = await AgentCtx.create_by_chat_key(
        chat_key=from_chat_key,
        container_key=container_key,
    )
    args = [ctx, *rpc_request.args] if rpc_request.args else [ctx]
    kwargs = rpc_request.kwargs or {}

    result, error_message = await execute_rpc_method(method, args, kwargs)

    if method_type in [SandboxMethodType.AGENT, SandboxMethodType.BEHAVIOR]:
        await message_service.push_system_message(chat_key=from_chat_key, agent_messages=str(result))
    if method_type == SandboxMethodType.MULTIMODAL_AGENT:
        result = f"<AGENT_RESULT>{json.dumps(result, ensure_ascii=False)}</AGENT_RESULT>"
    return Response(
        content=error_message or pickle.dumps(result),
        media_type="application/octet-stream",
        headers={"Method-Type": method_type.value, "Run-Error": "True" if error_message else "False"},
    )
