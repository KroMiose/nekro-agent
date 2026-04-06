"""
Test for CWE-22: Path Traversal in convert_to_host_path()

Demonstrates that sandbox paths containing '..' components can escape
the designated uploads_dir / shared_dir and resolve to arbitrary host
files (e.g. /etc/shadow).

The fix should ensure that the resolved host path stays strictly within
the allowed base directory.

NOTE: We import convert_to_host_path by loading the module file directly
to avoid pulling in the heavy nekro_agent.__init__ (which requires nonebot).
"""

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Direct import of path_convertor without triggering nekro_agent.__init__
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent.parent

# First, provide a stub for nekro_agent.core.os_env so it doesn't fail
# when path_convertor imports SANDBOX_SHARED_HOST_DIR / USER_UPLOAD_DIR.
_os_env_spec = importlib.util.spec_from_file_location(
    "nekro_agent.core.os_env",
    _HERE / "nekro_agent" / "core" / "os_env.py",
)

# We also need the core_utils dep. Let's stub os_env entirely instead:
# Provide a minimal fake os_env module.
import types

_fake_os_env = types.ModuleType("nekro_agent.core.os_env")
_fake_os_env.SANDBOX_SHARED_HOST_DIR = "/data/shared"
_fake_os_env.USER_UPLOAD_DIR = "/data/uploads"
sys.modules["nekro_agent.core.os_env"] = _fake_os_env

# Stub out nekro_agent.core.logger too
_fake_logger_mod = types.ModuleType("nekro_agent.core.logger")


class _FakeLogger:
    def debug(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


_fake_logger_mod.logger = _FakeLogger()
sys.modules["nekro_agent.core.logger"] = _fake_logger_mod

# Now load the path_convertor module directly
_spec = importlib.util.spec_from_file_location(
    "nekro_agent.tools.path_convertor",
    _HERE / "nekro_agent" / "tools" / "path_convertor.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["nekro_agent.tools.path_convertor"] = _mod
_spec.loader.exec_module(_mod)

convert_to_host_path = _mod.convert_to_host_path

# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------
UPLOADS_DIR = Path("/data/uploads")
SHARED_DIR = Path("/data/shared")
CHAT_KEY = "test_chat"
CONTAINER_KEY = "container_123"


class TestPathTraversalShared:
    """Path traversal via 'shared' location."""

    def test_traversal_shared_dotdot(self):
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

    def test_traversal_shared_relative(self):
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

    def test_traversal_uploads_dotdot(self):
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

    def test_shared_normal(self):
        result = convert_to_host_path(
            Path("/app/shared/test.txt"),
            chat_key=CHAT_KEY,
            container_key=CONTAINER_KEY,
            uploads_dir=UPLOADS_DIR,
            shared_dir=SHARED_DIR,
        )
        expected = SHARED_DIR / CONTAINER_KEY / "test.txt"
        assert result == expected

    def test_uploads_normal(self):
        result = convert_to_host_path(
            Path("/app/uploads/test.txt"),
            chat_key=CHAT_KEY,
            container_key=CONTAINER_KEY,
            uploads_dir=UPLOADS_DIR,
            shared_dir=SHARED_DIR,
        )
        expected = UPLOADS_DIR / CHAT_KEY / "test.txt"
        assert result == expected

    def test_shared_subdir(self):
        result = convert_to_host_path(
            Path("/app/shared/subdir/file.png"),
            chat_key=CHAT_KEY,
            container_key=CONTAINER_KEY,
            uploads_dir=UPLOADS_DIR,
            shared_dir=SHARED_DIR,
        )
        expected = SHARED_DIR / CONTAINER_KEY / "subdir" / "file.png"
        assert result == expected

    def test_uploads_relative(self):
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
