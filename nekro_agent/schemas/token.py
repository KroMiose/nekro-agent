from pydantic import BaseModel


class TokenData(BaseModel):
    """Token 数据"""
    username: str 