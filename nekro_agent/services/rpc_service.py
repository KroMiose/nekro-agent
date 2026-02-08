import asyncio
import pickle
from typing import Any, Tuple

from pydantic import ValidationError as PydanticValidationError

from nekro_agent.schemas.errors import ValidationError
from nekro_agent.schemas.rpc import RPCRequest


def decode_rpc_request(raw_body: bytes) -> RPCRequest:
    try:
        payload = pickle.loads(raw_body)
    except (pickle.UnpicklingError, EOFError, AttributeError, ValueError) as e:
        raise ValidationError(reason="RPC 请求格式错误") from e
    try:
        return RPCRequest.model_validate(payload)
    except PydanticValidationError as e:
        raise ValidationError(reason=str(e)) from e


async def execute_rpc_method(method: Any, args: list[Any], kwargs: dict[str, Any]) -> Tuple[Any, str]:
    try:
        if asyncio.iscoroutinefunction(method):
            result = await method(*args, **kwargs)
        else:
            result = method(*args, **kwargs)
        return result, ""
    except Exception as e:
        return None, str(e)
