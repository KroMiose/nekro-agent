from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.http_exception import (
    authorization_exception,
    credentials_exception,
)
from nekro_agent.schemas.token import TokenData
from nekro_agent.systems.user.role import Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> DBUser:
    """获取当前用户"""
    try:
        payload = jwt.decode(token, OsEnv.JWT_SECRET_KEY, algorithms=[OsEnv.ENCRYPT_ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = await DBUser.get_or_none(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: DBUser = Depends(get_current_user)) -> DBUser:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_super_user(current_user: DBUser = Depends(get_current_active_user)) -> DBUser:
    """获取当前超级用户"""
    if current_user.perm_level < Role.Super:
        raise authorization_exception
    return current_user
