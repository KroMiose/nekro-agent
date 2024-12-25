from datetime import datetime
from typing import Optional

from nekro_agent.core import logger
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.http_exception import credentials_exception
from nekro_agent.schemas.message import Ret
from nekro_agent.schemas.user import (
    UserCreate,
    UserLogin,
    UserToken,
)
from nekro_agent.systems.user.auth import (
    create_access_token,
    create_refresh_token,
    get_hashed_password,
    verify_password,
)
from nekro_agent.systems.user.perm import Role


async def query_user_by_bind_qq(qq: str) -> Optional[DBUser]:
    return await DBUser.get_or_none(bind_qq=qq)


async def user_register(data: UserCreate) -> Ret:
    logger.info(f"正在注册用户 {data.username} ...")
    if await DBUser.get_or_none(bind_qq=data.bind_qq):
        return Ret.fail("注册失败，用户已存在")
    try:
        await DBUser.create(
            username=data.username,
            password=get_hashed_password(data.password),
            bind_qq=data.bind_qq,
            perm_level=Role.User,
            login_time=datetime.now(),
        )
        return Ret.success("注册成功")
    except Exception as e:
        logger.error(f"注册用户时发生错误: {e}")
        return Ret.fail("注册失败，请稍后再试。")


async def user_login(data: UserLogin) -> UserToken:
    user: Optional[DBUser] = await DBUser.get_or_none(username=data.username)
    if not user:
        raise credentials_exception
    logger.info(f"用户 {user.username if user else '未知'} 正在登录")
    if user and verify_password(data.password, user.password):
        logger.info(f"用户 {user.username} 登录成功")
        user.login_time = datetime.now()
        await user.save()
        return UserToken(
            access_token=create_access_token(user.username),
            refresh_token=create_refresh_token(user.username),
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
