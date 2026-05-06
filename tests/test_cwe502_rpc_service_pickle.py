"""PoC test for CWE-502 in nekro_agent.services.rpc_service.decode_rpc_request.

Imports the rpc_service module by file path so the heavy package __init__
(nonebot, FastAPI, etc.) is not required to run the security regression test.
"""
import importlib.util
import os
import pickle
import sys
import tempfile
import types

import pytest

ROOT = "/Users/sebastion/projects/audits/KroMiose-nekro-agent-worktrees/cwe502-rpc-service-pickle-1c7e"


def _load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Stub the parent packages so relative imports work without running their __init__.
for pkg in ("nekro_agent", "nekro_agent.schemas", "nekro_agent.services"):
    if pkg not in sys.modules:
        m = types.ModuleType(pkg)
        m.__path__ = [os.path.join(ROOT, *pkg.split("."))]
        sys.modules[pkg] = m

errors = _load_module("nekro_agent.schemas.errors", os.path.join(ROOT, "nekro_agent/schemas/errors.py"))
rpc_schema = _load_module("nekro_agent.schemas.rpc", os.path.join(ROOT, "nekro_agent/schemas/rpc.py"))
rpc_service = _load_module("nekro_agent.services.rpc_service", os.path.join(ROOT, "nekro_agent/services/rpc_service.py"))

decode_rpc_request = rpc_service.decode_rpc_request
ValidationError = errors.ValidationError


SENTINEL = os.path.join(tempfile.gettempdir(), "nekro_rpc_pickle_pwn.txt")


class _Pwn:
    def __reduce__(self):
        import os as _os
        return (_os.system, (f"touch {SENTINEL}",))


def test_pickle_payload_does_not_execute():
    if os.path.exists(SENTINEL):
        os.remove(SENTINEL)
    raw = pickle.dumps(_Pwn())
    with pytest.raises(ValidationError):
        decode_rpc_request(raw)
    assert not os.path.exists(SENTINEL), "RCE: pickle payload was executed!"


def test_valid_json_request_is_accepted():
    import json
    body = json.dumps({"method": "foo", "args": [1, "x"], "kwargs": {"a": 1}}).encode()
    req = decode_rpc_request(body)
    assert req.method == "foo"
    assert req.args == [1, "x"]
    assert req.kwargs == {"a": 1}
