"""RPC pickle 反序列化安全测试

对应 PR 安全修复: /ext/rpc_exec 的请求解码使用白名单 RestrictedUnpickler,
阻止来自不可信沙箱的 pickle gadget 导致宿主 RCE。
"""

import pickle

import pytest

from nekro_agent.services.sandbox.rpc_pickle import restricted_pickle_loads


class _RceGadget:
    """经典 __reduce__ 反序列化 gadget(写标记文件作为 RCE 证据)"""

    def __reduce__(self):
        import os

        return (os.system, ("touch /tmp/nekro_rpc_pickle_rce_marker",))


def test_normal_rpc_payload_passes():
    """与沙箱 ext_caller_code.py 构造方式一致的正常请求应正常解码"""
    payload = pickle.dumps({"method": "send_msg_text", "args": ["chat", "hi"], "kwargs": {}})
    obj = restricted_pickle_loads(payload)
    assert obj["method"] == "send_msg_text"
    assert obj["args"] == ["chat", "hi"]


def test_reduce_gadget_rejected():
    """__reduce__ gadget(以 os.system 为例)必须被拒绝且不执行"""
    with pytest.raises(pickle.UnpicklingError):
        restricted_pickle_loads(pickle.dumps(_RceGadget()))


@pytest.mark.parametrize(
    ("opcode_payload", "label"),
    [
        # SHORT_BINUNICODE + STACK_GLOBAL 引用 posix.system
        (b"\x80\x04\x8c\x05posix\x94\x8c\x06system\x94\x93\x94.", "posix.system"),
        # 引用 subprocess.Popen
        (b"\x80\x04\x8c\tsubprocess\x94\x8c\x06Popen\x94\x93\x94.", "subprocess.Popen"),
        # 引用 builtins.eval(非白名单内建)
        (b"\x80\x04\x8c\x08builtins\x94\x8c\x04eval\x94\x93\x94.", "builtins.eval"),
    ],
)
def test_global_opcode_references_rejected(opcode_payload: bytes, label: str):
    """手工 opcode 注入的任意 GLOBAL 引用必须被拒绝"""
    with pytest.raises(pickle.UnpicklingError):
        restricted_pickle_loads(opcode_payload)


def test_whitelisted_stdlib_types_pass():
    """白名单内的标准库类型应正常往返"""
    import datetime
    from collections import OrderedDict

    payload = pickle.dumps({"ts": datetime.datetime(2026, 8, 17, 0, 0, 0), "od": OrderedDict([("a", 1)])})
    obj = restricted_pickle_loads(payload)
    assert obj["ts"] == datetime.datetime(2026, 8, 17)
    assert obj["od"] == OrderedDict([("a", 1)])
