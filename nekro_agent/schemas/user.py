from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .message import ret_data_class


class User(BaseModel):
    id: int
    username: str
    password: str
    perm_level: int
    login_time: datetime
    is_active: bool = True

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str
    adapter_key: str
    platform_userid: str
    access_key: Optional[str] = None


class UserUpdate(BaseModel):
    access_key: str
    username: str
    perm_level: int


class UpdatePassword(BaseModel):
    user_id: Optional[int] = None
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


@ret_data_class
class LoginRet(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class UserToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
