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
    - Content-Type 校验（非 JSON 响应抛出错误）
    - JSON 解析异常处理

    Args:
        response: httpx 响应对象
        model_cls: Pydantic 模型类
        action_desc: 操作描述（用于日志）

    Returns:
        解析后的 Pydantic 模型实例

    Raises:
        ValueError: 响应体为空、非 JSON 类型、或 JSON 解析失败时
    """
    response_text = response.text.strip()
    if not response_text:
        raise ValueError(f"{action_desc}: empty response, status={response.status_code}")

    content_type = response.headers.get("content-type", "")
    if "json" not in content_type.lower():
        # 非 JSON 响应，记录详细信息并抛出错误
        body_preview = response_text[:500] if response_text else "(empty)"
        logger.error(
            f"{action_desc}: expected JSON but got content-type={content_type}, "
            f"status={response.status_code}, body={body_preview}"
        )
        raise ValueError(
            f"{action_desc}: non-JSON response (content-type={content_type}), "
            f"status={response.status_code}"
        )

    try:
        return model_cls.model_validate_json(response_text)
    except Exception as e:
        # JSON 解析失败
        logger.error(
            f"{action_desc}: JSON parsing failed, status={response.status_code}, "
            f"body={response_text[:200]}, error={e}"
        )
        raise ValueError(f"{action_desc}: JSON parsing failed - {e}")


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
