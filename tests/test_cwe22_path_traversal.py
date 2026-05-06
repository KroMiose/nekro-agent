"""
Test for CWE-22: Path Traversal in convert_to_host_path()

Demonstrates that sandbox paths containing '..' components can escape
the designated uploads_dir / shared_dir and resolve to arbitrary host
files (e.g. /etc/shadow).

The fix should ensure that the resolved host path stays strictly within
the allowed base directory.

NOTE: We import convert_to_host_path by loading the module file directly
to avoid pulling in the heavy nekro_agent.__init__ (which requires nonebot).
The stubbing of dependent modules is performed inside an autouse fixture
so that test module import is side-effect light.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------
UPLOADS_DIR = Path("/data/uploads")
SHARED_DIR = Path("/data/shared")
CHAT_KEY = "test_chat"
CONTAINER_KEY = "container_123"


# ---------------------------------------------------------------------------
# Module loading via fixture (keeps test-module import side-effect light)
# ---------------------------------------------------------------------------
_STUBBED_MODULES = (
    "nekro_agent.core.os_env",
    "nekro_agent.core.logger",
    "nekro_agent.tools.path_convertor",
)


def _load_path_convertor():
    """Stub heavyweight deps and load path_convertor directly from disk."""
    fake_os_env = types.ModuleType("nekro_agent.core.os_env")
    fake_os_env.SANDBOX_SHARED_HOST_DIR = "/data/shared"
    fake_os_env.USER_UPLOAD_DIR = "/data/uploads"
    sys.modules["nekro_agent.core.os_env"] = fake_os_env

    fake_logger_mod = types.ModuleType("nekro_agent.core.logger")

    class _FakeLogger:
        def debug(self, *a, **k): pass
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass

    fake_logger_mod.logger = _FakeLogger()
    sys.modules["nekro_agent.core.logger"] = fake_logger_mod

    spec = importlib.util.spec_from_file_location(
        "nekro_agent.tools.path_convertor",
        _HERE / "nekro_agent" / "tools" / "path_convertor.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["nekro_agent.tools.path_convertor"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def convert_to_host_path():
    """Provide convert_to_host_path with stubbed dependencies, then clean up."""
    saved = {name: sys.modules.get(name) for name in _STUBBED_MODULES}
    try:
        mod = _load_path_convertor()
        yield mod.convert_to_host_path
    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


class TestPathTraversalShared:
    """Path traversal via 'shared' location."""

    def test_traversal_shared_dotdot(self, convert_to_host_path):
        """../../../etc/shadow after 'shared' escapes shared dir."""
        malicious = Path("/app/shared/../../../etc/shadow")
        with pytest.raises(ValueError):
            convert_to_host_path(
                malicious,
                chat_key=CHAT_KEY,
                container_key=CONTAINER_KEY,
                uploads_dir=UPLOADS_DIR,
                shared_dir=SHARED_DIR,
            )

    def test_traversal_shared_relative(self, convert_to_host_path):
        """Relative path variant: shared/../../../etc/passwd."""
        malicious = Path("shared/../../../etc/passwd")
        with pytest.raises(ValueError):
            convert_to_host_path(
                malicious,
                chat_key=CHAT_KEY,
                container_key=CONTAINER_KEY,
                uploads_dir=UPLOADS_DIR,
                shared_dir=SHARED_DIR,
            )


class TestPathTraversalUploads:
    """Path traversal via 'uploads' location."""

    def test_traversal_uploads_dotdot(self, convert_to_host_path):
        """/app/uploads/../../../etc/passwd escapes uploads dir."""
        malicious = Path("/app/uploads/../../../etc/passwd")
        with pytest.raises(ValueError):
            convert_to_host_path(
                malicious,
                chat_key=CHAT_KEY,
                container_key=CONTAINER_KEY,
                uploads_dir=UPLOADS_DIR,
                shared_dir=SHARED_DIR,
            )


class TestLegitPaths:
    """Legitimate sandbox paths must continue to work."""

    def test_shared_normal(self, convert_to_host_path):
        result = convert_to_host_path(
            Path("/app/shared/test.txt"),
            chat_key=CHAT_KEY,
            container_key=CONTAINER_KEY,
            uploads_dir=UPLOADS_DIR,
            shared_dir=SHARED_DIR,
        )
        expected = SHARED_DIR / CONTAINER_KEY / "test.txt"
        assert result == expected

    def test_uploads_normal(self, convert_to_host_path):
        result = convert_to_host_path(
            Path("/app/uploads/test.txt"),
            chat_key=CHAT_KEY,
            container_key=CONTAINER_KEY,
            uploads_dir=UPLOADS_DIR,
            shared_dir=SHARED_DIR,
        )
        expected = UPLOADS_DIR / CHAT_KEY / "test.txt"
        assert result == expected

    def test_shared_subdir(self, convert_to_host_path):
        result = convert_to_host_path(
            Path("/app/shared/subdir/file.png"),
            chat_key=CHAT_KEY,
            container_key=CONTAINER_KEY,
            uploads_dir=UPLOADS_DIR,
            shared_dir=SHARED_DIR,
        )
        expected = SHARED_DIR / CONTAINER_KEY / "subdir" / "file.png"
        assert result == expected

    def test_uploads_relative(self, convert_to_host_path):
        """Relative path (no leading /) also works."""
        result = convert_to_host_path(
            Path("uploads/icon.png"),
            chat_key=CHAT_KEY,
            container_key=CONTAINER_KEY,
            uploads_dir=UPLOADS_DIR,
            shared_dir=SHARED_DIR,
        )
        expected = UPLOADS_DIR / CHAT_KEY / "icon.png"
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
