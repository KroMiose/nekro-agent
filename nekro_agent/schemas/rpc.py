from pydantic import BaseModel, Field


class RPCRequest(BaseModel):
    method: str = Field(..., description="远程调用的方法名")
    args: list = Field(default_factory=list, description="远程调用方法的参数")
    kwargs: dict = Field(default_factory=dict, description="远程调用方法的关键字参数")
