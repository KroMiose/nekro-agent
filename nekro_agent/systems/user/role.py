from enum import IntEnum


class Role(IntEnum):
    """用户角色枚举"""

    Guest = 0
    User = 1
    Admin = 2
    Super = 3


def get_perm_role(level: int) -> str:
    """获取权限角色名称"""
    if level > 3:
        return Role.Super.name
    return Role(level).name
