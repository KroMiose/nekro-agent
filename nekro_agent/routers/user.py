from datetime import datetime, timedelta

from fastapi import APIRouter, Depends

from nekro_agent import config, logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.http_exception import (
    authorization_exception,
    permission_exception,
    too_many_attempts_exception,
)
from nekro_agent.schemas.message import Ret
from nekro_agent.schemas.user import (
    LoginRet,
    UpdatePassword,
    UserCreate,
    UserLogin,
)
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.role import Role, get_perm_role
from nekro_agent.services.user.util import (
    user_change_password,
    user_delete,
    user_login,
    user_register,
)

router = APIRouter(prefix="/user", tags=["User"])

# 登录尝试记录：{username: {attempts: int, last_attempt: datetime}}
login_attempts = {}
# 最大尝试次数和锁定时间
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=30)


# 清理过期的登录尝试记录
def clean_expired_attempts():
    now = datetime.now()
    expired_users = []
    for username, data in login_attempts.items():
        if data["last_attempt"] + LOCKOUT_DURATION < now:
            expired_users.append(username)
    for username in expired_users:
        login_attempts.pop(username)


@router.post("/register", summary="用户注册")
async def register(req_data: UserCreate) -> Ret:
    if req_data.access_key != OsEnv.SUPER_ACCESS_KEY:
        raise authorization_exception
    try:
        await user_register(req_data)
        return Ret.success("注册成功")
    except:
        return Ret.fail("注册失败")


@router.post("/login", summary="用户登录")
async def login(req_data: UserLogin) -> LoginRet:
    # 清理过期的尝试记录
    clean_expired_attempts()

    # 检查当前用户是否已经尝试过多次
    if req_data.username in login_attempts:
        user_attempts = login_attempts[req_data.username]
        if user_attempts["attempts"] >= MAX_LOGIN_ATTEMPTS:
            now = datetime.now()
            lock_expires = user_attempts["last_attempt"] + LOCKOUT_DURATION
            if now < lock_expires:
                logger.warning(f"用户 {req_data.username} 尝试登录次数过多，账户被锁定到 {lock_expires}")
                raise too_many_attempts_exception
            # 锁定已过期，重置计数
            login_attempts.pop(req_data.username)

    try:
        login_token = await user_login(req_data)
        # 登录成功，清除尝试记录
        if req_data.username in login_attempts:
            login_attempts.pop(req_data.username)
        return LoginRet(
            access_token=login_token.access_token,
            refresh_token=login_token.refresh_token,
            token_type=login_token.token_type,
        )
    except Exception:
        # 登录失败，记录尝试次数
        now = datetime.now()
        if req_data.username not in login_attempts:
            login_attempts[req_data.username] = {"attempts": 1, "last_attempt": now}
        else:
            login_attempts[req_data.username]["attempts"] += 1
            login_attempts[req_data.username]["last_attempt"] = now
        logger.warning(f"用户 {req_data.username} 登录失败，当前尝试次数: {login_attempts[req_data.username]['attempts']}")
        # 重新抛出原始异常
        raise


@router.put("/password", summary="用户更新密码")
async def password(
    req_data: UpdatePassword,
    _current_user: DBUser = Depends(get_current_active_user),
):
    if req_data.user_id is not None and _current_user.id != req_data.user_id and _current_user.perm_level < Role.Super:
        raise permission_exception
    return await user_change_password(_current_user, req_data.password)


@router.get("/me", summary="用户个人信息")
async def info(_current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    logger.info(f"用户 {_current_user.username} 正在查询个人信息...")
    return Ret.success(
        "query success",
        data={
            "username": _current_user.username,
            "userId": _current_user.id,
            "perm_level": _current_user.perm_level,
            "perm_role": get_perm_role(_current_user.perm_level),
        },
    )


@router.delete("/delete", summary="删除用户")
async def delete(_id: int, _current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    logger.info(f"用户 {_current_user.username} 正在删除用户 {_id}...")
    if int(str(_current_user.perm_level)) < Role.Super:
        return Ret.fail("权限不足")
    try:
        user = await DBUser.get_or_none(id=_id)
        if user is None:
            return Ret.fail("用户不存在")
        await user_delete(user)
        return Ret.success("删除成功")
    except:
        return Ret.fail("删除失败")
