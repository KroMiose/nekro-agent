import asyncio
from datetime import datetime
from weakref import WeakKeyDictionary

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

# 锁必须跟着事件循环走：模块级 asyncio.Lock 会绑死在首个 await 所在的循环上，
# 之后换循环（重载、脚本、测试）再复用就直接 RuntimeError。
#
# 注意这里只保证单进程内互斥：NoneBot 与 uvicorn 启动路径都没有 workers，Docker
# 也固定了 container_name 因而不便横向扩容。若将来真的多实例共库，串行化必须落到
# user 表 (adapter_key, platform_userid) 的唯一约束上，进程内的锁兜不住。
_REGISTER_LOCKS: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = WeakKeyDictionary()


def _user_register_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    lock = _REGISTER_LOCKS.get(loop)
    if lock is None:
        lock = asyncio.Lock()
        _REGISTER_LOCKS[loop] = lock
    return lock


async def user_register(data: UserCreate) -> None:
    logger.info(f"正在注册用户 {data.username} ...")
    if data.username == "admin":
        raise ConflictError(resource="用户名")
    # user 表上没有 (adapter_key, platform_userid) 唯一约束，先查后插必须整体串行；
    # 否则同一用户并发发言时两个任务都查不到而各插一行，之后该用户每条消息都会读失败。
    # 摘要放在锁外算：它是锁无关的纯计算，留在临界区里会把不相干用户的建档也串起来。
    hashed_password = get_hashed_password(data.password)
    async with _user_register_lock():
        if await DBUser.get_by_union_id(adapter_key=data.adapter_key, platform_userid=data.platform_userid):
            raise ConflictError(resource="用户")
        try:
            await DBUser.create(
                username=data.username,
                password=hashed_password,
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
