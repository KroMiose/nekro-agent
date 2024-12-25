from fastapi import APIRouter, Depends

from nekro_agent import config, logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.http_exception import (
    authorization_exception,
    permission_exception,
)
from nekro_agent.schemas.message import Ret
from nekro_agent.schemas.user import (
    LoginRet,
    UpdatePassword,
    UserCreate,
    UserLogin,
)
from nekro_agent.services.user import (
    user_change_password,
    user_delete,
    user_login,
    user_register,
)
from nekro_agent.systems.user.deps import get_current_active_user
from nekro_agent.systems.user.perm import Role, get_perm_role

router = APIRouter(prefix="/user", tags=["User"])


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
    login_token = await user_login(req_data)
    return LoginRet(
        access_token=login_token.access_token,
        refresh_token=login_token.refresh_token,
        token_type=login_token.token_type,
    )


@router.put("/password", summary="用户更新密码")
async def password(
    req_data: UpdatePassword,
    current_user: DBUser = Depends(get_current_active_user),
):
    if req_data.user_id is not None and current_user.id != req_data.user_id and current_user.perm_level < Role.Super:
        raise permission_exception
    return await user_change_password(current_user, req_data.password)


@router.get("/me", summary="用户个人信息")
async def info(current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    logger.info(f"用户 {current_user.username} 正在查询个人信息...")
    return Ret.success(
        "query success",
        data={
            "username": current_user.username,
            "userId": current_user.id,
            "perm_level": current_user.perm_level,
            "perm_role": get_perm_role(current_user.perm_level),
        },
    )


@router.delete("/delete", summary="删除用户")
async def delete(_id: int, current_user: DBUser = Depends(get_current_active_user)) -> Ret:
    logger.info(f"用户 {current_user.username} 正在删除用户 {_id}...")
    if int(str(current_user.perm_level)) < Role.Super:
        return Ret.fail("权限不足")
    try:
        user = await DBUser.get_or_none(id=_id)
        if user is None:
            return Ret.fail("用户不存在")
        await user_delete(user)
        return Ret.success("删除成功")
    except:
        return Ret.fail("删除失败")
