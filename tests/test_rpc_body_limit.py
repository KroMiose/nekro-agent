"""RPC 请求体增量大小限制测试"""

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, Request
from starlette.requests import ClientDisconnect

from nekro_agent.core.exception_handlers import register_exception_handlers
from nekro_agent.routers.rpc import _read_request_body_limited
from nekro_agent.schemas.errors import PayloadTooLargeError, ValidationError


def _make_request(
    chunks: list[bytes],
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[Request, dict[str, int]]:
    messages = [
        {"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
        for index, chunk in enumerate(chunks)
    ] or [{"type": "http.request", "body": b"", "more_body": False}]
    calls = {"receive": 0}

    async def receive() -> dict[str, Any]:
        calls["receive"] += 1
        if messages:
            return messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers or [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }
    return Request(scope, receive), calls


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"", b"abcd", b"abcde"])
async def test_limited_body_accepts_up_to_limit(body: bytes):
    request, _ = _make_request([body])
    assert await _read_request_body_limited(request, 5) == body


@pytest.mark.asyncio
async def test_limited_body_accepts_exact_limit_across_chunks():
    request, calls = _make_request([b"ab", b"cde"])
    assert await _read_request_body_limited(request, 5) == b"abcde"
    assert calls["receive"] == 2


@pytest.mark.asyncio
async def test_limited_body_stops_at_first_oversized_chunk():
    request, calls = _make_request([b"abcde", b"x", b"tail"])
    with pytest.raises(PayloadTooLargeError):
        await _read_request_body_limited(request, 5)
    assert calls["receive"] == 2


@pytest.mark.asyncio
async def test_content_length_over_limit_rejected_before_reading():
    request, calls = _make_request([b"unused"], [(b"content-length", b"6")])
    with pytest.raises(PayloadTooLargeError):
        await _read_request_body_limited(request, 5)
    assert calls["receive"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("declared", [None, b"1", b"5"])
async def test_stream_limit_is_enforced_when_content_length_is_missing_or_small(declared: bytes | None):
    headers = [] if declared is None else [(b"content-length", declared)]
    request, _ = _make_request([b"abc", b"def"], headers)
    with pytest.raises(PayloadTooLargeError):
        await _read_request_body_limited(request, 5)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [b"", b"-1", b"+5", b"5.0", b"abc", b"5, 5"])
async def test_malformed_content_length_rejected_before_reading(value: bytes):
    request, calls = _make_request([b"unused"], [(b"content-length", value)])
    with pytest.raises(ValidationError, match="Content-Length"):
        await _read_request_body_limited(request, 5)
    assert calls["receive"] == 0


@pytest.mark.asyncio
async def test_duplicate_content_length_rejected_before_reading():
    request, calls = _make_request(
        [b"unused"],
        [(b"content-length", b"5"), (b"content-length", b"5")],
    )
    with pytest.raises(ValidationError, match="Content-Length"):
        await _read_request_body_limited(request, 5)
    assert calls["receive"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [0, -1])
async def test_nonpositive_limit_rejected_before_reading(limit: int):
    request, calls = _make_request([b"unused"])
    with pytest.raises(ValueError, match="NEKRO_RPC_MAX_BODY_BYTES"):
        await _read_request_body_limited(request, limit)
    assert calls["receive"] == 0


@pytest.mark.asyncio
async def test_client_disconnect_is_not_relabelled_as_oversize():
    async def receive() -> dict[str, str]:
        return {"type": "http.disconnect"}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
        },
        receive,
    )
    with pytest.raises(ClientDisconnect):
        await _read_request_body_limited(request, 5)


@pytest.mark.asyncio
async def test_http_endpoint_returns_413_for_chunked_oversize():
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/rpc-body")
    async def rpc_body(request: Request):
        return {"body": (await _read_request_body_limited(request, 5)).decode()}

    async def content() -> AsyncIterator[bytes]:
        yield b"abc"
        yield b"def"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/rpc-body", content=content())

    assert response.status_code == 413
    assert response.json()["error"] == "PayloadTooLargeError"
