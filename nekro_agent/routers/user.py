from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import (
    AppError,
    NotFoundError,
    PermissionDeniedError,
    TooManyAttemptsError,
    UnauthorizedError,
)
from nekro_agent.schemas.user import (
    UpdatePassword,
    UserCreate,
    UserLogin,
    UserToken,
)
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.role import Role, get_perm_role
from nekro_agent.services.user.util import (
    user_change_password,
    user_delete,
    user_login,
    user_register,
)

logger = get_sub_logger("auth")
router = APIRouter(prefix="/user", tags=["User"])

# 登录尝试记录：{username: {attempts: int, last_attempt: datetime}}
login_attempts = {}
# 最大尝试次数和锁定时间
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=30)


class ActionResponse(BaseModel):
    ok: bool = True


class UserInfoResponse(BaseModel):
    username: str
    userId: int
    perm_level: int
    perm_role: str


# 清理过期的登录尝试记录
def clean_expired_attempts():
    now = datetime.now()
    expired_users = []
    for username, data in login_attempts.items():
        if data["last_attempt"] + LOCKOUT_DURATION < now:
            expired_users.append(username)
    for username in expired_users:
        login_attempts.pop(username)


@router.post("/register", summary="用户注册", response_model=ActionResponse)
async def register(req_data: UserCreate) -> ActionResponse:
    if req_data.access_key != OsEnv.SUPER_ACCESS_KEY:
        raise UnauthorizedError
    await user_register(req_data)
    return ActionResponse(ok=True)


@router.post("/login", summary="用户登录", response_model=UserToken)
async def login(req_data: UserLogin) -> UserToken:
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
                raise TooManyAttemptsError
            # 锁定已过期，重置计数
            login_attempts.pop(req_data.username)

    try:
        login_token = await user_login(req_data)
        if req_data.username in login_attempts:
            login_attempts.pop(req_data.username)
        return login_token
    except AppError:
        now = datetime.now()
        if req_data.username not in login_attempts:
            login_attempts[req_data.username] = {"attempts": 1, "last_attempt": now}
        else:
            login_attempts[req_data.username]["attempts"] += 1
            login_attempts[req_data.username]["last_attempt"] = now
        logger.warning(
            f"用户 {req_data.username} 登录失败，当前尝试次数: {login_attempts[req_data.username]['attempts']}"
        )
        raise


@router.put("/password", summary="用户更新密码", response_model=ActionResponse)
async def password(
    req_data: UpdatePassword,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    if req_data.user_id is not None and _current_user.id != req_data.user_id and _current_user.perm_level < Role.Super:
        raise PermissionDeniedError
    await user_change_password(_current_user, req_data.password)
    return ActionResponse(ok=True)


@router.get("/me", summary="用户个人信息", response_model=UserInfoResponse)
async def info(_current_user: DBUser = Depends(get_current_active_user)) -> UserInfoResponse:
    return UserInfoResponse(
        username=_current_user.username,
        userId=_current_user.id,
        perm_level=_current_user.perm_level,
        perm_role=get_perm_role(_current_user.perm_level),
    )


@router.delete("/delete", summary="删除用户", response_model=ActionResponse)
async def delete(_id: int, _current_user: DBUser = Depends(get_current_active_user)) -> ActionResponse:
    if int(str(_current_user.perm_level)) < Role.Super:
        raise PermissionDeniedError
    user = await DBUser.get_or_none(id=_id)
    if user is None:
        raise NotFoundError(resource="用户")
    await user_delete(user)
    return ActionResponse(ok=True)
