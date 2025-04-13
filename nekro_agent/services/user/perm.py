from functools import wraps
from typing import Callable

from fastapi import Depends, HTTPException
from starlette import status

from nekro_agent.models.db_user import DBUser
from nekro_agent.services.user.deps import get_current_active_user
from nekro_agent.services.user.role import Role


def require_role(min_role: Role) -> Callable:
    """
    权限检查装饰器
    :param min_role: 最小所需角色等级
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, _current_user: DBUser = Depends(get_current_active_user), **kwargs):
            if _current_user.perm_level < min_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足",
                )
            return await func(*args, _current_user=_current_user, **kwargs)
        return wrapper
    return decorator


def check_role(user: DBUser, min_role: Role) -> bool:
    """
    检查用户是否具有指定角色权限
    :param user: 用户对象
    :param min_role: 最小所需角色等级
    """
    return user.perm_level >= min_role
