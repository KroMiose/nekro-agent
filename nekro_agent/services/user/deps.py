from typing import Optional

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.auth_token import TokenData
from nekro_agent.schemas.errors import (
    PermissionDeniedError,
    TokenExpiredError,
    UnauthorizedError,
)
from nekro_agent.services.user.role import Role

logger = get_sub_logger("auth")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")


async def get_current_user(request: Request, token: Optional[str] = None) -> DBUser:
    """
    Get current user from token.
    """
    try:
        # 首先尝试从 URL 参数获取 token
        url_token = request.query_params.get("token")
        if url_token:
            logger.debug(f"Raw token from URL: {url_token}")
            # 处理可能带有 Bearer 前缀的 token
            if url_token.startswith("Bearer "):
                url_token = url_token.split(" ")[1]
            token = url_token
            logger.debug(f"Processed token from URL: {token}")
        # 如果 URL 中没有 token，则尝试从 header 获取
        elif not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
            else:
                logger.debug("No valid token found in header")
                raise UnauthorizedError

        if not token:
            logger.debug("No token found in URL or header")
            raise UnauthorizedError

        payload = jwt.decode(token, OsEnv.JWT_SECRET_KEY, algorithms=[OsEnv.ENCRYPT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise UnauthorizedError
        token_data = TokenData(username=username)
    except ExpiredSignatureError as e:
        logger.debug(f"JWT expired: {e!s}")
        raise TokenExpiredError from e
    except JWTError as e:
        logger.debug(f"JWT validation failed: {e!s}")
        raise UnauthorizedError from e
    if token_data.username == "admin":
        user = await DBUser.get_or_none(username="admin")
    else:
        user = await DBUser.get_or_none(username=token_data.username)
    if user is None:
        logger.debug(f"User '{token_data.username}' not found")
        raise UnauthorizedError
    return user


async def get_current_active_user(current_user: DBUser = Depends(get_current_user)) -> DBUser:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise PermissionDeniedError
    return current_user


async def get_current_super_user(current_user: DBUser = Depends(get_current_active_user)) -> DBUser:
    """获取当前超级用户"""
    if current_user.perm_level < Role.Super:
        logger.debug(f"User {current_user.username} is not a super user")
        raise PermissionDeniedError
    return current_user
