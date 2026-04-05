"""Per-container ephemeral RPC token registry.

Instead of sharing the global RPC_SECRET_KEY with every sandbox container,
each container receives a unique short-lived token that is validated
server-side.  This limits the blast radius: a compromised sandbox can
only authenticate as itself, and the token can be revoked when the
container is torn down.
"""

import secrets
import threading
from typing import Dict, Optional


class RPCTokenRegistry:
    """Thread-safe registry for per-container ephemeral RPC tokens."""

    def __init__(self) -> None:
        self._tokens: Dict[str, str] = {}
        self._lock = threading.Lock()

    def create_token(self, container_key: str) -> str:
        """Generate and store a cryptographically random token for *container_key*.

        If a token already exists for the key it is replaced (rotation).
        """
        token = secrets.token_urlsafe(48)
        with self._lock:
            self._tokens[container_key] = token
        return token

    def validate_token(self, container_key: str, token: str) -> bool:
        """Return ``True`` only when *token* matches the stored value for
        *container_key*."""
        with self._lock:
            expected = self._tokens.get(container_key)
        if expected is None:
            return False
        return secrets.compare_digest(expected, token)

    def revoke_token(self, container_key: str) -> None:
        """Remove the token for *container_key* (e.g. on container teardown)."""
        with self._lock:
            self._tokens.pop(container_key, None)

    def get_token(self, container_key: str) -> Optional[str]:
        """Return the current token for *container_key*, or ``None``."""
        with self._lock:
            return self._tokens.get(container_key)


# Module-level singleton used by ext_caller and the RPC router.
rpc_token_registry = RPCTokenRegistry()
