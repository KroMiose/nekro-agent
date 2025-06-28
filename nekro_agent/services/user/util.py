from datetime import datetime
from typing import Optional

from nekro_agent.core import config, logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.http_exception import credentials_exception
from nekro_agent.schemas.message import Ret
from nekro_agent.schemas.user import (
    UserCreate,
    UserLogin,
    UserToken,
)
from nekro_agent.services.user.auth import (
    create_access_token,
    create_refresh_token,
    get_hashed_password,
    verify_password,
)
from nekro_agent.services.user.perm import Role


async def user_register(data: UserCreate) -> Ret:
    logger.info(f"正在注册用户 {data.username} ...")
    if data.username == "admin":
        return Ret.fail("注册失败，管理员保留用户名无法注册")
    if await DBUser.get_or_none(adapter_key=data.adapter_key, platform_userid=data.platform_userid):
        return Ret.fail("注册失败，用户已存在")
    try:
        await DBUser.create(
            username=data.username,
            password=get_hashed_password(data.password),
            adapter_key=data.adapter_key,
            platform_userid=data.platform_userid,
            perm_level=Role.User,
            login_time=datetime.now(),
        )
        return Ret.success("注册成功")
    except Exception as e:
        logger.error(f"注册用户时发生错误: {e}")
        return Ret.fail("注册失败，请稍后再试。")


async def user_login(data: UserLogin) -> UserToken:
    if OsEnv.ADMIN_PASSWORD and data.username == "admin" and data.password == OsEnv.ADMIN_PASSWORD:
        # logger.debug(f"管理员登录: {data} | {OsEnv.ADMIN_PASSWORD}")
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
    user: Optional[DBUser] = await DBUser.get_or_none(unique_id=data.username)
    if not user:
        raise credentials_exception
    if user.unique_id not in config.SUPER_USERS and not config.ALLOW_SUPER_USERS_LOGIN:
        raise credentials_exception
    logger.info(f"用户 {user.username if user else '未知'} 正在登录")
    if user and verify_password(data.password, user.password):
        logger.info(f"用户 {user.username} 登录成功")
        if user.unique_id in config.SUPER_USERS:
            user.perm_level = Role.Admin.value
        user.login_time = datetime.now()
        await user.save()
        return UserToken(
            access_token=create_access_token(user.unique_id),
            refresh_token=create_refresh_token(user.unique_id),
            token_type="bearer",
        )
    logger.info(f"用户 {data.username} 登录校验失败 ")
    raise credentials_exception


async def user_change_password(user: DBUser, new_password: str) -> Ret:
    try:
        user.password = get_hashed_password(new_password)
        await user.save()
        return Ret.success("密码修改成功")
    except:
        return Ret.fail("密码修改失败")


async def user_delete(user: DBUser):
    try:
        await user.delete()
        return Ret.success("删除成功")
    except:
        return Ret.fail("删除失败")
