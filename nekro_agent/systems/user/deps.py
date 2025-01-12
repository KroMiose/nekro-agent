from datetime import datetime, timedelta, timezone

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from nekro_agent.core import config
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.http_exception import (
    credentials_exception,
    login_expired_exception,
)
from nekro_agent.systems.user.auth import get_hashed_password
from nekro_agent.systems.user.perm import Role

reuseable_oauth = OAuth2PasswordBearer(tokenUrl="/login", scheme_name="JWT")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前用户"""

    class TokenData(BaseModel):
        username: str
        bind_qq: str

    try:
        payload = jwt.decode(
            token,
            OsEnv.JWT_SECRET_KEY,
            algorithms=[OsEnv.ENCRYPT_ALGORITHM],
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, bind_qq=username)
    except JWTError as e:
        raise credentials_exception from e
    if token_data.username == "admin":
        user = await DBUser.get_or_none(username="admin")
        if user is None:
            return await DBUser.create(
                username="admin",
                password=get_hashed_password(""),
                bind_qq="",
                perm_level=Role.Super,
                login_time=datetime.now(),
            )
        return user
    user = await DBUser.get_or_none(bind_qq=token_data.bind_qq)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: DBUser = Depends(get_current_user),
) -> DBUser:
    """获取当前激活用户"""

    expiration_time = current_user.login_time + timedelta(
        minutes=OsEnv.ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60,
    )

    if expiration_time < datetime.now(timezone.utc):
        raise login_expired_exception
    return current_user
