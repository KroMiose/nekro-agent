"""HMAC signer for the NA-Tools daemon protocol."""

import hashlib
import hmac
import secrets
import time


def now_unix_ms() -> str:
    """Return the current unix timestamp in milliseconds."""

    return str(int(time.time() * 1000))


def new_nonce() -> str:
    """Return a random 128-bit nonce as lowercase hex."""

    return secrets.token_hex(16)


def build_signature_headers(
    *,
    token: bytes,
    instance_id: str,
    method: str,
    path_with_query: str,
    body: bytes = b"",
    timestamp: str | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    """Build daemon HMAC headers for one request."""

    timestamp = timestamp or now_unix_ms()
    nonce = nonce or new_nonce()
    body_hash = hashlib.sha256(body).hexdigest()
    plaintext = "\n".join([method.upper(), path_with_query, timestamp, nonce, body_hash])
    digest = hmac.new(token, plaintext.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "X-NA-Instance": instance_id,
        "X-NA-Timestamp": timestamp,
        "X-NA-Nonce": nonce,
        "X-NA-Signature": f"v1={digest}",
    }

