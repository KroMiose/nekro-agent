"""沙盒环境下的扩展方法调用代理"""

import pickle as _pickle
from typing import Any, Callable, Dict, Tuple

import matplotlib.pyplot as plt
import requests as _requests

# 设置中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial Unicode MS", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

CHAT_API = "{CHAT_API}"
CONTAINER_KEY = "{CONTAINER_KEY}"
FROM_CHAT_KEY = "{FROM_CHAT_KEY}"
RPC_SECRET_KEY = "{RPC_SECRET_KEY}"


def __extension_method_proxy(method: Callable):
    """扩展方法代理执行器"""

    def acutely_call_method(*args: Tuple[Any], **kwargs: Dict[str, Any]):
        """Agent 执行沙盒扩展方法时实际调用的方法"""

        body = {"method": method.__name__, "args": args, "kwargs": kwargs}
        data: bytes = _pickle.dumps(body)
        response = _requests.post(
            f"{CHAT_API}/ext/rpc_exec?container_key={CONTAINER_KEY}&from_chat_key={FROM_CHAT_KEY}",
            data=data,
            headers={
                "Content-Type": "application/octet-stream",
                "X-RPC-Token": RPC_SECRET_KEY,
            },
        )
        if response.status_code == 200:
            if response.headers.get("Run-Error") and response.headers["Run-Error"].lower() == "true":
                print(
                    f"The method `{method.__name__}` returned an error:\n{response.text}",
                )
                exit(1)
            ret_data = _pickle.loads(response.content)
            if response.headers.get("Method-Type") == "agent":
                print(
                    f"The agent method `{method.__name__}` returned:\n{ret_data}\n[result end]\nPlease continue to generate an appropriate response based on the above information.",
                )
                exit(8)
            if response.headers.get("Method-Type") == "multimodal_agent":
                print(
                    f"The multimodal agent method `{method.__name__}` returned:\n{ret_data}\n[result end]",
                )
                exit(11)
            return ret_data
        raise Exception(f"Plugin RPC method `{method.__name__}` call failed: {response.status_code}")

    return acutely_call_method
