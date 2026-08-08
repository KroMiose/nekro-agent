from __future__ import annotations

from contextvars import ContextVar, Token

from nekro_agent.models.db_user import DBUser
from nekro_agent.schemas.errors import UnauthorizedError

_current_user: ContextVar[DBUser | None] = ContextVar("web_chat_mcp_current_user", default=None)


def set_current_user(user: DBUser) -> Token[DBUser | None]:
    return _current_user.set(user)


def reset_current_user(token: Token[DBUser | None]) -> None:
    _current_user.reset(token)


def get_current_user() -> DBUser:
    user = _current_user.get()
    if user is None:
        raise UnauthorizedError
    return user
