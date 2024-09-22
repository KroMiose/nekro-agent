import asyncio
import inspect

import nekro_agent.services.sandbox.ext_caller_code
from nekro_agent.core import config, logger
from nekro_agent.tools.collector import agent_collector

CODE_PREAMBLE = """
from api_caller import *
"""

METHOD_REG_TEMPLATE = """
@__extension_method_proxy
def {method_name}(*args, **kwargs):
    pass
"""  #! 沙盒环境下不需要使用异步方式调用，因为实际执行是通过 RPC 调用的


def get_api_caller_code(container_key: str, from_chat_key: str):
    base_code = (
        inspect.getsource(nekro_agent.services.sandbox.ext_caller_code)
        .replace("{CHAT_API}", config.SANDBOX_CHAT_API_URL)
        .replace("{CONTAINER_KEY}", container_key)
        .replace("{FROM_CHAT_KEY}", from_chat_key)
    )
    methods = agent_collector.get_all_methods()

    for method in methods:
        base_code += METHOD_REG_TEMPLATE.format(method_name=method.__name__)
    return base_code.strip()
