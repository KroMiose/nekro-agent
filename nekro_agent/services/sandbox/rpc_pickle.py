"""RPC pickle 反序列化安全限制

背景:
`/ext/rpc_exec` 接收来自沙箱(执行 LLM 生成代码的不可信环境)的 pickle 请求体。
pickle 反序列化任意类可导致宿主进程 RCE(如 `__reduce__` gadget)。

方案:
使用受限 Unpickler,仅放行基础内建类型与少量显式白名单标准库类型,
其余任何 GLOBAL/STACK_GLOBAL 加载一律拒绝。
"""

import datetime
import decimal
import io
import pickle
from collections import OrderedDict, defaultdict, deque
from pathlib import Path, PurePath
from types import SimpleNamespace

# 显式允许跨 pickle 边界的类(标准库、无副作用构造函数)
_SAFE_CLASSES: dict[tuple[str, str], type] = {
    ("builtins", "complex"): complex,
    ("collections", "OrderedDict"): OrderedDict,
    ("collections", "defaultdict"): defaultdict,
    ("collections", "deque"): deque,
    ("datetime", "datetime"): datetime.datetime,
    ("datetime", "date"): datetime.date,
    ("datetime", "timedelta"): datetime.timedelta,
    ("datetime", "time"): datetime.time,
    ("decimal", "Decimal"): decimal.Decimal,
    ("pathlib", "Path"): Path,
    ("pathlib", "PosixPath"): Path,
    ("pathlib", "WindowsPath"): Path,
    ("pathlib", "PurePath"): PurePath,
    ("types", "SimpleNamespace"): SimpleNamespace,
}


class RestrictedUnpickler(pickle.Unpickler):
    """拒绝加载任何不在白名单内的全局对象"""

    def find_class(self, module: str, name: str):  # noqa: ANN201, D102
        candidate = _SAFE_CLASSES.get((module, name))
        if candidate is not None:
            return candidate
        raise pickle.UnpicklingError(f"forbidden global: {module}.{name}")

    @classmethod
    def loads(cls, data: bytes) -> object:
        """反序列化 bytes,应用白名单限制"""
        return cls(io.BytesIO(data)).load()


def restricted_pickle_loads(data: bytes) -> object:
    """安全的 pickle 反序列化入口(供 RPC 请求解码使用)"""
    return RestrictedUnpickler.loads(data)
