from datetime import datetime

from nekro_agent.core import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import (
    ConflictError,
    InvalidCredentialsError,
    OperationFailedError,
)
from nekro_agent.schemas.user import (
    UserCreate,
    UserLogin,
    UserToken,
)
from nekro_agent.services.user.auth import (
    create_access_token,
    create_refresh_token,
    get_hashed_password,
)
from nekro_agent.services.user.perm import Role


async def user_register(data: UserCreate) -> None:
    logger.info(f"正在注册用户 {data.username} ...")
    if data.username == "admin":
        raise ConflictError(resource="用户名")
    if await DBUser.get_or_none(adapter_key=data.adapter_key, platform_userid=data.platform_userid):
        raise ConflictError(resource="用户")
    try:
        await DBUser.create(
            username=data.username,
            password=get_hashed_password(data.password),
            adapter_key=data.adapter_key,
            platform_userid=data.platform_userid,
            perm_level=Role.User,
            login_time=datetime.now(),
        )
    except Exception as e:
        logger.error(f"注册用户时发生错误: {e}")
        raise OperationFailedError(operation="注册用户") from e


async def user_login(data: UserLogin) -> UserToken:
    if data.username != "admin":
        raise InvalidCredentialsError
    if OsEnv.ADMIN_PASSWORD and data.username == "admin" and data.password == OsEnv.ADMIN_PASSWORD:
        user = await DBUser.get_or_none(username="admin")
        if not user:
            await DBUser.create(
                username="admin",
                password=get_hashed_password(data.password),
                adapter_key="",
                platform_userid="",
                perm_level=Role.Admin,
                login_time=datetime.now(),
            )
        return UserToken(
            access_token=create_access_token(data.username),
            refresh_token=create_refresh_token(data.username),
            token_type="bearer",
        )
    raise InvalidCredentialsError


async def user_change_password(user: DBUser, new_password: str) -> None:
    try:
        user.password = get_hashed_password(new_password)
        await user.save()
    except Exception as e:
        raise OperationFailedError(operation="修改密码") from e


async def user_delete(user: DBUser) -> None:
    try:
        await user.delete()
    except Exception as e:
        raise OperationFailedError(operation="删除用户") from e
