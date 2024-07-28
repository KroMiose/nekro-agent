import asyncio
import inspect

import nekro_agent.services.sandbox.ext_caller_code
from nekro_agent.core import logger
from nekro_agent.tools.collector import agent_collector

CODE_PREAMBLE = """
from api_caller import *
"""

METHOD_REG_TEMPLATE = """
@__extension_method_proxy
def {method_name}(*args, **kwargs):
    pass
"""

ASYNC_METHOD_REG_TEMPLATE = """
@__extension_method_proxy
async def {method_name}(*args, **kwargs):
    pass
"""


def get_api_caller_code():
    base_code = inspect.getsource(nekro_agent.services.sandbox.ext_caller_code).replace(
        "{CHAT_API}",
        "http://host.docker.internal:8001/api",
    )
    methods = agent_collector.get_all_methods()

    logger.info(f"正在注册 {len(methods)} 个扩展方法...")

    for method in methods:
        if asyncio.iscoroutinefunction(method) and False:
            #! 沙盒环境下不需要使用异步方式调用，因为实际执行是通过 RPC 调用的
            code = ASYNC_METHOD_REG_TEMPLATE.format(method_name=method.__name__)
        else:
            code = METHOD_REG_TEMPLATE.format(method_name=method.__name__)
        base_code += code
    return base_code.strip()
