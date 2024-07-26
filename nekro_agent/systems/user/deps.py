from datetime import datetime, timedelta

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from nekro_agent.core import config
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.http_exception import (
    credentials_exception,
    login_expired_exception,
)

reuseable_oauth = OAuth2PasswordBearer(tokenUrl="/login", scheme_name="JWT")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前用户"""

    class TokenData(BaseModel):
        username: str

    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.ENCRYPT_ALGORITHM],
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        raise credentials_exception from e
    user = DBUser.get_by_field(field=DBUser.username, value=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: DBUser = Depends(get_current_user),
) -> DBUser:
    """获取当前激活用户"""

    expiration_time = current_user.login_time + timedelta(
        minutes=config.ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60,
    )

    if expiration_time < datetime.now():  # type: ignore
        raise login_expired_exception
    return current_user
