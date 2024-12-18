import os
from typing import Dict, List

from .exceptions import InvalidCredentialException, RunOutOfCredentialException

_iter_idx_dict: Dict[str, int] = {}


def iter_credential(credentials: List[str], iter_key: str = "openai"):
    """迭代器装饰器，用于对请求进行多次尝试，以防止因密钥失效或其他原因导致请求失败。

    Args:
        credentials (List[str]): 用于请求的密钥列表。
        iter_key (str, optional): 迭代器的唯一标识符，默认为 "openai"。

    Returns:
        装饰器函数。

    Raises:
        RunOutOfCredentialException: 当所有密钥均已尝试过且仍然失败时抛出。
    """

    def _iterator_decorator(req_func):
        async def _wrapper(**kwargs):
            global _iter_idx_dict
            _iter_start_idx = _iter_idx_dict.get(iter_key, 0)

            try_cnt = len(credentials)
            while try_cnt > 0:
                try_cnt -= 1
                _iter_start_idx = (_iter_start_idx + 1) % len(credentials)
                try:
                    return await req_func(
                        api_key=(
                            credentials[_iter_start_idx]
                            if "api_key" not in kwargs
                            else kwargs["api_key"]
                        ),
                        **kwargs,
                    )
                except InvalidCredentialException:
                    pass
            else:
                raise RunOutOfCredentialException

        return _wrapper

    return _iterator_decorator


def in_test():
    return os.getenv("IN_TEST_MODE", "false").lower() == "true"
