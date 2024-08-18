from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import jwt
from passlib.context import CryptContext

from nekro_agent.core.os_env import OsEnv

ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 1 day
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * OsEnv.ACCESS_TOKEN_EXPIRE_DAYS
JWT_SECRET_KEY = OsEnv.JWT_SECRET_KEY
JWT_REFRESH_SECRET_KEY = OsEnv.JWT_REFRESH_SECRET_KEY

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hashed_password(password: str) -> str:
    """获取加密后的密码"""

    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    """验证密码"""

    return password_context.verify(password, hashed_pass)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[int] = None,
) -> str:
    """创建token"""

    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta  # type: ignore
    else:
        expires_delta = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # type: ignore

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    return jwt.encode(to_encode, JWT_SECRET_KEY, OsEnv.ENCRYPT_ALGORITHM)


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[int] = None,
) -> str:
    """创建refresh token"""

    if expires_delta is not None:
        expires_delta = datetime.utcnow() + expires_delta  # type: ignore
    else:
        expires_delta = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)  # type: ignore

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    return jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, OsEnv.ENCRYPT_ALGORITHM)
