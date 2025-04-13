from typing import Callable

from .base import SandboxMethodType


def get_sandbox_method_type(method: Callable) -> SandboxMethodType:
    if hasattr(method, "_method_type"):
        try:
            return SandboxMethodType(method._method_type)  # noqa: SLF001
        except ValueError as e:
            raise ValueError(f"方法 {method.__name__} 的 _method_type 属性值无效。") from e
    raise AttributeError(f"方法 {method.__name__} 没有 _method_type 属性。")
