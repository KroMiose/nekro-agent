"""Cloud API 基础工具模块

提供统一的 HTTP 响应解析方法，避免在各 API 模块中重复代码。
"""
from typing import Any, Dict, Type, TypeVar

import httpx
from pydantic import BaseModel

from nekro_agent.core.logger import get_sub_logger

logger = get_sub_logger("cloud_api")

T = TypeVar("T", bound=BaseModel)


def parse_json_response(response: httpx.Response, model_cls: Type[T], action_desc: str) -> T:
    """统一解析 HTTP JSON 响应

    包含：
    - 空响应检查
    - Content-Type 校验
    - 日志记录

    Args:
        response: httpx 响应对象
        model_cls: Pydantic 模型类
        action_desc: 操作描述（用于日志）

    Returns:
        解析后的 Pydantic 模型实例

    Raises:
        ValueError: 响应体为空时
    """
    response_text = response.text.strip()
    if not response_text:
        raise ValueError(f"{action_desc}: empty response, status={response.status_code}")

    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower():
        logger.warning(f"{action_desc}: non-JSON, type={content_type}, body={response_text[:200]}")

    return model_cls.model_validate_json(response_text)


def parse_json_dict(response: httpx.Response, action_desc: str) -> Dict[str, Any]:
    """解析 HTTP 响应为字典（用于 community-stats 等场景）

    Args:
        response: httpx 响应对象
        action_desc: 操作描述

    Returns:
        解析后的字典

    Raises:
        ValueError: 响应体为空时
    """
    import json as json_lib

    response_text = response.text.strip()
    if not response_text:
        raise ValueError(f"{action_desc}: empty, status={response.status_code}")

    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower():
        logger.warning(f"{action_desc}: non-JSON, type={content_type}, body={response_text[:200]}")

    return json_lib.loads(response_text)
