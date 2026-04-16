import base64
import hashlib
import json
from typing import Dict

from Crypto.Cipher import AES

from nekro_agent.core.os_env import OsEnv


def _get_secret_key() -> bytes:
    return hashlib.sha256(OsEnv.JWT_SECRET_KEY.encode("utf-8")).digest()


def encrypt_secret_payload(payload: Dict[str, str]) -> str:
    if not payload:
        return ""
    cipher = AES.new(_get_secret_key(), AES.MODE_GCM)
    plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return json.dumps(
        {
            "nonce": base64.b64encode(cipher.nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            "tag": base64.b64encode(tag).decode("ascii"),
        },
        ensure_ascii=False,
    )


def decrypt_secret_payload(value: str) -> Dict[str, str]:
    if not value.strip():
        return {}
    data = json.loads(value)
    cipher = AES.new(
        _get_secret_key(),
        AES.MODE_GCM,
        nonce=base64.b64decode(data["nonce"]),
    )
    plaintext = cipher.decrypt_and_verify(
        base64.b64decode(data["ciphertext"]),
        base64.b64decode(data["tag"]),
    )
    parsed = json.loads(plaintext.decode("utf-8"))
    return {str(k): str(v) for k, v in parsed.items()}
