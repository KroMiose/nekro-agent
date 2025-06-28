from datetime import datetime, timezone
from typing import Optional, cast

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from tortoise.expressions import Q

from nekro_agent import logger
from nekro_agent.core.os_env import OsEnv
from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.http_exception import (
    authorization_exception,
    permission_exception,
)
from nekro_agent.schemas.message import Ret
from nekro_agent.schemas.user import UserCreate, UserUpdate
from nekro_agent.services.user.auth import get_hashed_password
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.role import Role, get_perm_role
from nekro_agent.services.user.util import user_register

router = APIRouter(prefix="/user-manager", tags=["UserManager"])


@router.get("/list", summary="获取用户列表")
async def list_users(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取用户列表"""
    if _current_user.perm_level < Role.Admin:
        raise permission_exception

    # 构建查询
    query = DBUser.all()

    # 搜索
    if search:
        query = query.filter(
            Q(username__icontains=search) | Q(platform_userid__icontains=search),
        )

    # 排序
    if sort_by:
        order_by = sort_by
        if sort_order == "desc":
            order_by = f"-{sort_by}"
        query = query.order_by(order_by)
    else:
        query = query.order_by("-id")

    # 分页
    total = await query.count()
    users = await query.offset((page - 1) * page_size).limit(page_size)

    # 转换为响应格式
    user_list = []
    for user in users:
        user_list.append(
            {
                "id": user.id,
                "username": user.username,
                "adapter_key": user.adapter_key,
                "platform_userid": user.platform_userid,
                "unique_id": user.unique_id,
                "perm_level": user.perm_level,
                "perm_role": get_perm_role(user.perm_level),
                "login_time": user.login_time,
                "ban_until": user.ban_until,
                "prevent_trigger_until": user.prevent_trigger_until,
                "is_active": user.is_active,
                "is_prevent_trigger": user.is_prevent_trigger,
                "create_time": user.create_time,
                "update_time": user.update_time,
            },
        )

    return Ret.success(
        "获取成功",
        data={
            "total": total,
            "items": user_list,
            "page": page,
            "page_size": page_size,
        },
    )


@router.get("/{user_id}", summary="获取用户详情")
async def get_user(
    user_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """获取用户详情"""
    if _current_user.perm_level < Role.Admin:
        raise permission_exception

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        return Ret.fail("用户不存在")

    return Ret.success(
        "获取成功",
        data={
            "id": user.id,
            "username": user.username,
            "adapter_key": user.adapter_key,
            "platform_userid": user.platform_userid,
            "unique_id": user.unique_id,
            "perm_level": user.perm_level,
            "perm_role": get_perm_role(user.perm_level),
            "login_time": user.login_time,
            "ban_until": user.ban_until,
            "prevent_trigger_until": user.prevent_trigger_until,
            "is_active": user.is_active,
            "is_prevent_trigger": user.is_prevent_trigger,
            "ext_data": user.ext_data,
            "create_time": user.create_time,
            "update_time": user.update_time,
        },
    )


@router.post("/create", summary="创建新用户")
async def create_user(
    user_data: UserCreate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """创建新用户"""
    if _current_user.perm_level < Role.Admin:
        raise permission_exception

    # 验证访问密钥
    if user_data.access_key != OsEnv.SUPER_ACCESS_KEY:
        raise authorization_exception

    try:
        await user_register(user_data)
        return Ret.success("创建成功")
    except Exception as e:
        logger.error(f"创建用户失败: {e!s}")
        return Ret.fail(f"创建失败: {e!s}")


@router.put("/{user_id}", summary="更新用户信息")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """更新用户信息"""
    if _current_user.perm_level < Role.Admin:
        raise permission_exception

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        return Ret.fail("用户不存在")

    # 验证访问密钥
    if user_data.access_key != OsEnv.SUPER_ACCESS_KEY:
        raise authorization_exception

    user.username = user_data.username
    user.perm_level = user_data.perm_level
    await user.save()

    return Ret.success("更新成功")


class BanUserRequest(BaseModel):
    ban_until: Optional[datetime] = None


@router.post("/{user_id}/ban", summary="封禁/解封用户")
async def ban_user(
    user_id: int,
    ban_data: BanUserRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """封禁/解封用户"""
    if _current_user.perm_level < Role.Admin:
        raise permission_exception

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        return Ret.fail("用户不存在")

    # 类型安全地设置ban_until
    user.ban_until = cast(datetime, ban_data.ban_until)
    await user.save()

    return Ret.success("操作成功")


class PreventTriggerRequest(BaseModel):
    prevent_trigger_until: Optional[datetime] = None


@router.post("/{user_id}/prevent-trigger", summary="设置触发权限")
async def prevent_trigger(
    user_id: int,
    prevent_data: PreventTriggerRequest,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """设置触发权限"""
    if _current_user.perm_level < Role.Admin:
        raise permission_exception

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        return Ret.fail("用户不存在")

    # 类型安全地设置prevent_trigger_until
    user.prevent_trigger_until = cast(datetime, prevent_data.prevent_trigger_until)
    await user.save()

    return Ret.success("操作成功")


@router.post("/{user_id}/reset-password", summary="重置用户密码")
async def reset_password(
    user_id: int,
    password: str = Body(..., embed=True),
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """重置用户密码"""
    if _current_user.perm_level < Role.Admin:
        raise permission_exception

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        return Ret.fail("用户不存在")

    user.password = get_hashed_password(password)
    await user.save()

    return Ret.success("密码重置成功")


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    _current_user: DBUser = Depends(get_current_active_user),
) -> Ret:
    """删除用户"""
    if _current_user.perm_level < Role.Admin:
        raise permission_exception

    user = await DBUser.get_or_none(id=user_id)
    if not user:
        return Ret.fail("用户不存在")

    await user.delete()
    return Ret.success("删除成功")
