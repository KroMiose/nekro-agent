"""沙盒环境下的扩展方法调用代理"""

import pickle as _pickle
from typing import Any, Callable, Dict, Tuple

import requests as _requests

CHAT_API = "{CHAT_API}"
CONTAINER_KEY = "{CONTAINER_KEY}"
FROM_CHAT_KEY = "{FROM_CHAT_KEY}"


def __extension_method_proxy(method: Callable):
    """扩展方法代理执行器"""

    def acutely_call_method(*args: Tuple[Any], **kwargs: Dict[str, Any]):
        """Agent 执行时实际调用的方法"""

        body = {"method": method.__name__, "args": args, "kwargs": kwargs}
        data: bytes = _pickle.dumps(body)
        response = _requests.post(
            f"{CHAT_API}/ext/rpc_exec?container_key={CONTAINER_KEY}&from_chat_key={FROM_CHAT_KEY}",
            data=data,
            headers={"Content-Type": "application/octet-stream"},
        )
        if response.status_code == 200:
            ret_data = _pickle.loads(response.content)
            if response.headers.get("Error-Message"):
                print(
                    f"The method `{method.__name__}` returned an error:\n{response.headers.get('Error-Message')}",
                )
                exit(1)
            if response.headers.get("Method-Type") == "agent":
                print(
                    f"The agent method `{method.__name__}` returned:\n{ret_data}\n[result end]\nPlease generate a new response based on the above information ",
                )
                exit(1)
            return ret_data
        raise Exception(f"Extension call failed: {response.status_code}")

    return acutely_call_method
