"""沙盒环境下的扩展方法调用代理"""

import pickle as _pickle
from typing import Any, Callable, Dict, Tuple

import requests as _requests

CHAT_API = "{CHAT_API}"


def __extension_method_proxy(method: Callable):
    """扩展方法代理执行器"""

    def acutely_call_method(*args: Tuple[Any], **kwargs: Dict[str, Any]):
        """Agent 执行时实际调用的方法"""

        body = {"method": method.__name__, "args": args, "kwargs": kwargs}
        data: bytes = _pickle.dumps(body)
        response = _requests.post(
            f"{CHAT_API}/ext/rpc_exec",
            data=data,
            headers={"Content-Type": "application/octet-stream"},
        )
        if response.status_code == 200:
            return _pickle.loads(response.content)
        raise Exception(f"Extension call failed: {response.status_code}")

    return acutely_call_method
