import math
from dataclasses import dataclass
from typing import Optional

import httpx

from nekro_agent.services.agent.openai import _create_http_client


@dataclass
class AnthropicTestResponse:
    model: str
    response_text: str
    input_tokens: int
    output_tokens: int


def resolve_cc_test_model(
    *,
    model_type: str,
    preset_model: str = "",
    anthropic_model: str = "",
    small_fast_model: str = "",
    default_sonnet: str = "",
    default_opus: str = "",
    default_haiku: str = "",
) -> str:
    """为 CC 模型组选择一个可直接发起 Anthropic Messages 请求的测试模型。"""

    if model_type == "manual":
        candidates = [
            anthropic_model,
            default_sonnet,
            default_opus,
            default_haiku,
            small_fast_model,
        ]
    else:
        candidates = [
            anthropic_model,
            default_sonnet,
            default_opus,
            default_haiku,
            small_fast_model,
            preset_model,
        ]

    for candidate in candidates:
        candidate = candidate.strip()
        if candidate:
            return candidate
    return ""


def _normalize_messages_endpoint(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/v1/messages"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/messages"
    return f"{normalized}/v1/messages"


def _resolve_timeout_seconds(timeout_ms: Optional[str]) -> int:
    try:
        parsed_ms = int((timeout_ms or "").strip())
    except (TypeError, ValueError):
        return 30

    if parsed_ms <= 0:
        return 30
    return max(5, min(math.ceil(parsed_ms / 1000), 60))


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        text = response.text.strip()
        return text or f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()

    return f"HTTP {response.status_code}"


async def test_anthropic_messages(
    *,
    base_url: str,
    auth_token: str,
    model: str,
    api_timeout_ms: Optional[str] = None,
) -> AnthropicTestResponse:
    """通过 Anthropic Messages API 发起最小请求，验证模型组是否可调用。"""

    endpoint = _normalize_messages_endpoint(base_url)
    timeout_seconds = _resolve_timeout_seconds(api_timeout_ms)
    payload = {
        "model": model,
        "max_tokens": 16,
        "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
    }
    headers = {
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
        "x-api-key": auth_token.strip(),
        "authorization": f"Bearer {auth_token.strip()}",
    }

    async with _create_http_client(
        read_timeout=timeout_seconds,
        write_timeout=timeout_seconds,
        connect_timeout=min(timeout_seconds, 10),
        pool_timeout=min(timeout_seconds, 10),
    ) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        if response.is_error:
            raise ValueError(_extract_error_message(response))
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("响应格式无效")

        content = payload.get("content")
        response_text = ""
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                    text_parts.append(item["text"])
            response_text = "".join(text_parts).strip()

        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        input_tokens = usage.get("input_tokens") if isinstance(usage.get("input_tokens"), int) else 0
        output_tokens = usage.get("output_tokens") if isinstance(usage.get("output_tokens"), int) else 0
        actual_model = payload.get("model") if isinstance(payload.get("model"), str) else model

        return AnthropicTestResponse(
            model=actual_model,
            response_text=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
