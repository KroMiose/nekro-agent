from enum import IntEnum


class Role(IntEnum):
    User = 0
    Admin = 10
    Super = 20


def get_perm_role(perm_level: int) -> str:
    """获取权限角色"""

    if perm_level < Role.Admin:
        return "User"
    if perm_level < Role.Super:
        return "Admin"
    return "Super"
