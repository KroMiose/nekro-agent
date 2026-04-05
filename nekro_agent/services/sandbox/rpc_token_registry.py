"""Per-container ephemeral RPC token registry.

Instead of sharing the global RPC_SECRET_KEY with every sandbox container,
each container receives a unique token that is validated server-side.
This limits the blast radius: a compromised sandbox can only authenticate
as itself, and the token can be revoked when the container is torn down.

Tokens are automatically expired based on a configurable TTL (default 600 s).
They may also be rotated via ``create_token`` or explicitly revoked via
``revoke_token``.
"""

import secrets
import threading
import time
from typing import Dict, Optional, Tuple


class RPCTokenRegistry:
    """Thread-safe registry for per-container ephemeral RPC tokens.

    Tokens are automatically expired based on ``ttl_seconds`` configured at
    construction time.  They may also be rotated via :meth:`create_token` or
    explicitly revoked via :meth:`revoke_token`.
    """

    def __init__(self, ttl_seconds: float = 600.0) -> None:
        """Create a new token registry.

        Args:
            ttl_seconds: Time-to-live in seconds for issued tokens.  Tokens
                older than this are treated as invalid and are removed on
                validation.
        """
        # Maps container_key -> (token, created_at_monotonic)
        self._tokens: Dict[str, Tuple[str, float]] = {}
        self._ttl_seconds = float(ttl_seconds)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_token(self, container_key: str) -> str:
        """Generate and store a cryptographically random token for *container_key*.

        If a token already exists for the key it is replaced (rotation).
        The token will be considered valid only until its TTL expires.
        """
        token = secrets.token_urlsafe(48)
        created_at = time.monotonic()
        with self._lock:
            self._tokens[container_key] = (token, created_at)
        return token

    def validate_token(self, container_key: str, token: str) -> bool:
        """Return ``True`` only when *token* matches the stored value for
        *container_key* and the token has not expired."""
        with self._lock:
            entry = self._tokens.get(container_key)
            if entry is None:
                return False

            expected, created_at = entry
            if self._is_expired(created_at):
                # Drop expired token on access to keep the registry bounded.
                self._tokens.pop(container_key, None)
                return False

        return secrets.compare_digest(expected, token)

    def revoke_token(self, container_key: str) -> None:
        """Remove the token for *container_key* (e.g. on container teardown)."""
        with self._lock:
            self._tokens.pop(container_key, None)

    def get_token(self, container_key: str) -> Optional[str]:
        """Return the current token for *container_key*, or ``None``.

        Returns ``None`` if the token has expired.
        """
        with self._lock:
            entry = self._tokens.get(container_key)
            if entry is None:
                return None
            token, created_at = entry
            if self._is_expired(created_at):
                self._tokens.pop(container_key, None)
                return None
            return token

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_expired(self, created_at: float) -> bool:
        """Return ``True`` if the token created at *created_at* is past its TTL."""
        return (time.monotonic() - created_at) > self._ttl_seconds


# Module-level singleton used by ext_caller and the RPC router.
rpc_token_registry = RPCTokenRegistry()
