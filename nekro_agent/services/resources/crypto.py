import base64
import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Dict

from Crypto.Cipher import AES

from nekro_agent.core.os_env import OsEnv


class SecretPayloadDecodeError(ValueError):
    """敏感资源载荷无法解码。"""


class SecretPayloadFormat(str, Enum):
    EMPTY = "empty"
    PLAIN = "plain"
    LEGACY_ENCRYPTED = "legacy_encrypted"
    INVALID = "invalid"


@dataclass(frozen=True)
class SecretPayloadDecodeResult:
    payload: Dict[str, str]
    format: SecretPayloadFormat


def _get_secret_key(secret: str | None = None) -> bytes:
    return hashlib.sha256((secret if secret is not None else OsEnv.JWT_SECRET_KEY).encode("utf-8")).digest()


def _normalize_payload(payload: object) -> Dict[str, str]:
    if not isinstance(payload, dict):
        raise SecretPayloadDecodeError("敏感资源载荷必须是 JSON 对象")
    return {str(k): str(v) for k, v in payload.items()}


def _is_legacy_encrypted_payload(data: object) -> bool:
    return isinstance(data, dict) and {"nonce", "ciphertext", "tag"}.issubset(data.keys())


def _decrypt_legacy_payload(data: dict, *, secret: str | None = None) -> Dict[str, str]:
    cipher = AES.new(
        _get_secret_key(secret),
        AES.MODE_GCM,
        nonce=base64.b64decode(data["nonce"]),
    )
    plaintext = cipher.decrypt_and_verify(
        base64.b64decode(data["ciphertext"]),
        base64.b64decode(data["tag"]),
    )
    return _normalize_payload(json.loads(plaintext.decode("utf-8")))


def encrypt_secret_payload(payload: Dict[str, str]) -> str:
    if not payload:
        return ""
    return json.dumps(_normalize_payload(payload), ensure_ascii=False)


def decrypt_secret_payload(value: str, *, legacy_secret: str | None = None) -> Dict[str, str]:
    return decode_secret_payload(value, legacy_secret=legacy_secret).payload


def decode_secret_payload(value: str, *, legacy_secret: str | None = None) -> SecretPayloadDecodeResult:
    if not value.strip():
        return SecretPayloadDecodeResult(payload={}, format=SecretPayloadFormat.EMPTY)
    data = json.loads(value)
    if _is_legacy_encrypted_payload(data):
        try:
            return SecretPayloadDecodeResult(
                payload=_decrypt_legacy_payload(data, secret=legacy_secret),
                format=SecretPayloadFormat.LEGACY_ENCRYPTED,
            )
        except Exception as e:
            raise SecretPayloadDecodeError(
                "旧版加密敏感字段无法解密，请提供创建资源时使用的旧 NEKRO_JWT_SECRET_KEY"
            ) from e
    try:
        return SecretPayloadDecodeResult(payload=_normalize_payload(data), format=SecretPayloadFormat.PLAIN)
    except SecretPayloadDecodeError:
        raise
    except Exception as e:
        raise SecretPayloadDecodeError("敏感资源载荷格式无效") from e
