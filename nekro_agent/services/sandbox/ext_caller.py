from pathlib import Path
from typing import Optional

from nekro_agent.core import config
from nekro_agent.schemas.agent_ctx import AgentCtx
from nekro_agent.services.plugin.collector import plugin_collector
from nekro_agent.services.sandbox.rpc_token_registry import rpc_token_registry

CODE_PREAMBLE = """
from api_caller import *

_ck = FROM_CHAT_KEY
"""

METHOD_REG_TEMPLATE = """
@__extension_method_proxy
def {method_name}(*args, **kwargs):
    pass
"""  #! 沙盒环境下不需要使用异步方式调用，因为实际执行是通过 RPC 调用的


async def get_api_caller_code(container_key: str, from_chat_key: str, ctx: Optional[AgentCtx] = None):
    # Generate a per-container ephemeral token instead of leaking the
    # global RPC_SECRET_KEY into the sandbox environment.
    ephemeral_token = rpc_token_registry.create_token(container_key)

    base_code = (
        Path("nekro_agent/services/sandbox/ext_caller_code.py")
        .read_text(encoding="utf-8")
        .replace("{CHAT_API}", config.SANDBOX_CHAT_API_URL)
        .replace("{CONTAINER_KEY}", container_key)
        .replace("{FROM_CHAT_KEY}", from_chat_key)
        .replace("{RPC_SECRET_KEY}", ephemeral_token)
    )
    methods = await plugin_collector.get_all_sandbox_methods(ctx)

    for method in methods:
        if method.func.__name__ != "dynamic_importer":
            base_code += METHOD_REG_TEMPLATE.format(method_name=method.func.__name__)
    return base_code.strip()
