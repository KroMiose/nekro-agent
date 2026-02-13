from datetime import datetime
from typing import List, Optional, cast

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from tortoise.expressions import Q

from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import NotFoundError, PermissionDeniedError, UnauthorizedError
from nekro_agent.schemas.user import UserCreate, UserUpdate
from nekro_agent.services.user.auth import get_hashed_password
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.role import Role, get_perm_role
from nekro_agent.services.user.util import user_register

router = APIRouter(prefix="/user-manager", tags=["UserManager"])


class ActionResponse(BaseModel):
    ok: bool = True


class UserInfo(BaseModel):
    id: int
    username: str
    adapter_key: str
    platform_userid: str
    unique_id: str
    perm_level: int
    perm_role: str
    login_time: Optional[datetime]
    ban_until: Optional[datetime]
    prevent_trigger_until: Optional[datetime]
    is_active: bool
    is_prevent_trigger: bool
    create_time: Optional[datetime]
    update_time: Optional[datetime]
    ext_data: Optional[dict] = None


class UserListResponse(BaseModel):
    total: int
    items: List[UserInfo]
    page: int
    page_size: int


@router.get("/list", summary="获取用户列表", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> UserListResponse:
    """获取用户列表"""
    if _current_user.perm_level < Role.Admin:
        raise PermissionDeniedError

    query = DBUser.all()

    if search:
        query = query.filter(
            Q(username__icontains=search) | Q(platform_userid__icontains=search),
        )

    if sort_by:
        order_by = f"-{sort_by}" if sort_order == "desc" else sort_by
        query = query.order_by(order_by)
    else:
        query = query.order_by("-id")

    total = await query.count()
    users = await query.offset((page - 1) * page_size).limit(page_size)

    user_list: List[UserInfo] = []
    for user in users:
        user_list.append(
            UserInfo(
                id=user.id,
                username=user.username,
                adapter_key=user.adapter_key,
                platform_userid=user.platform_userid,
                unique_id=user.unique_id,
                perm_level=user.perm_level,
                perm_role=get_perm_role(user.perm_level),
                login_time=user.login_time,
                ban_until=user.ban_until,
                prevent_trigger_until=user.prevent_trigger_until,
                is_active=user.is_active,
                is_prevent_trigger=user.is_prevent_trigger,
                create_time=user.create_time,
                update_time=user.update_time,
            ),
        )

    return UserListResponse(
        total=total,
        items=user_list,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", summary="获取用户详情", response_model=UserInfo)
async def get_user(
    user_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> UserInfo:
    """获取用户详情"""
    if _current_user.perm_level < Role.Admin:
        raise PermissionDeniedError

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        raise NotFoundError(resource="用户")

    return UserInfo(
        id=user.id,
        username=user.username,
        adapter_key=user.adapter_key,
        platform_userid=user.platform_userid,
        unique_id=user.unique_id,
        perm_level=user.perm_level,
        perm_role=get_perm_role(user.perm_level),
        login_time=user.login_time,
        ban_until=user.ban_until,
        prevent_trigger_until=user.prevent_trigger_until,
        is_active=user.is_active,
        is_prevent_trigger=user.is_prevent_trigger,
        ext_data=user.ext_data,
        create_time=user.create_time,
        update_time=user.update_time,
    )


@router.post("/create", summary="创建新用户", response_model=ActionResponse)
async def create_user(
    user_data: UserCreate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """创建新用户"""
    if _current_user.perm_level < Role.Admin:
        raise PermissionDeniedError

    if user_data.access_key != OsEnv.SUPER_ACCESS_KEY:
        raise UnauthorizedError

    await user_register(user_data)
    return ActionResponse(ok=True)


@router.put("/{user_id}", summary="更新用户信息", response_model=ActionResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """更新用户信息"""
    if _current_user.perm_level < Role.Admin:
        raise PermissionDeniedError

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        raise NotFoundError(resource="用户")

    if user_data.access_key != OsEnv.SUPER_ACCESS_KEY:
        raise UnauthorizedError

    user.username = user_data.username
    user.perm_level = user_data.perm_level
    await user.save()

    return ActionResponse(ok=True)


class BanUserRequest(BaseModel):
    ban_until: Optional[datetime] = None


@router.post("/{user_id}/ban", summary="封禁/解封用户", response_model=ActionResponse)
async def ban_user(
    user_id: int,
    ban_data: BanUserRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """封禁/解封用户"""
    if _current_user.perm_level < Role.Admin:
        raise PermissionDeniedError

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        raise NotFoundError(resource="用户")

    user.ban_until = cast(datetime, ban_data.ban_until)
    await user.save()

    return ActionResponse(ok=True)


class PreventTriggerRequest(BaseModel):
    prevent_trigger_until: Optional[datetime] = None


@router.post("/{user_id}/prevent-trigger", summary="设置触发权限", response_model=ActionResponse)
async def prevent_trigger(
    user_id: int,
    prevent_data: PreventTriggerRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """设置触发权限"""
    if _current_user.perm_level < Role.Admin:
        raise PermissionDeniedError

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        raise NotFoundError(resource="用户")

    user.prevent_trigger_until = cast(datetime, prevent_data.prevent_trigger_until)
    await user.save()

    return ActionResponse(ok=True)


@router.post("/{user_id}/reset-password", summary="重置用户密码", response_model=ActionResponse)
async def reset_password(
    user_id: int,
    password: str = Body(..., embed=True),
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """重置用户密码"""
    if _current_user.perm_level < Role.Admin:
        raise PermissionDeniedError

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        raise NotFoundError(resource="用户")

    user.password = get_hashed_password(password)
    await user.save()
    return ActionResponse(ok=True)


@router.delete("/{user_id}", summary="删除用户", response_model=ActionResponse)
async def delete_user(
    user_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> ActionResponse:
    """删除用户"""
    if _current_user.perm_level < Role.Admin:
        raise PermissionDeniedError

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        raise NotFoundError(resource="用户")

    await user.delete()
    return ActionResponse(ok=True)
