"""MCP 服务器活跑校验

提供"按一次按钮"的 MCP `initialize` 握手能力，对三种传输类型都给出结构化结果。
- HTTP / SSE：直接从 NA 主机使用 `mcp` SDK 走握手；URL 可达性与 CC 容器同网段一致。
- stdio：通过 aiodocker 在 CC 沙盒容器内 exec 子进程，走 newline-delimited JSON-RPC，
        因为 stdio MCP server (npx/uvx 等) 只在容器内可用。
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Literal, Optional

import aiodocker
from pydantic import BaseModel

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_workspace import DBWorkspace

from .schemas import McpServerConfig, McpServerType

logger = get_sub_logger("mcp.validator")

ErrorKind = Literal[
    "schema",
    "spawn_failed",
    "handshake_timeout",
    "transport_error",
    "container_not_running",
    "invalid_response",
]

# MCP 协议常量
_PROTOCOL_VERSION = "2024-11-05"
_CLIENT_INFO = {"name": "nekro-agent-validator", "version": "1.0"}


class McpValidationResult(BaseModel):
    """单次 MCP 验证结果"""

    ok: bool
    server_info: Optional[Dict[str, Any]] = None
    capabilities: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None
    latency_ms: float = 0.0
    error: Optional[str] = None
    error_kind: Optional[ErrorKind] = None


async def validate_server(
    workspace: Optional[DBWorkspace],
    server: McpServerConfig,
    timeout_seconds: float = 15.0,
) -> McpValidationResult:
    """对一个 MCP server 配置发起活跑校验"""
    start = time.perf_counter()
    try:
        if server.type == McpServerType.http:
            return await _validate_http(server, timeout_seconds, start)
        if server.type == McpServerType.sse:
            return await _validate_sse(server, timeout_seconds, start)
        if server.type == McpServerType.stdio:
            return await _validate_stdio(workspace, server, timeout_seconds, start)
    except Exception as e:  # noqa: BLE001
        logger.exception(f"MCP 验证未捕获异常: {e}")
        return _fail("transport_error", str(e), start)
    return _fail("schema", f"未知 transport 类型: {server.type}", start)


# ──────────────────────────────────────────────────────────────
# HTTP / SSE
# ──────────────────────────────────────────────────────────────


async def _validate_http(
    server: McpServerConfig,
    timeout_seconds: float,
    start: float,
) -> McpValidationResult:
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    if not server.url:
        return _fail("schema", "未配置 url", start)

    try:
        async with asyncio.timeout(timeout_seconds):
            async with streamablehttp_client(
                server.url,
                headers=server.headers or None,
                timeout=timeout_seconds,
            ) as (read_stream, write_stream, _get_session_id):
                async with ClientSession(read_stream, write_stream) as session:
                    init_result = await session.initialize()
                    tools_result = await session.list_tools()
                    return _ok(init_result, tools_result, start)
    except TimeoutError:
        return _fail("handshake_timeout", f"握手超时 ({timeout_seconds}s)", start)
    except Exception as e:  # noqa: BLE001
        return _classify_transport_error(e, start)


async def _validate_sse(
    server: McpServerConfig,
    timeout_seconds: float,
    start: float,
) -> McpValidationResult:
    from mcp.client.session import ClientSession
    from mcp.client.sse import sse_client

    if not server.url:
        return _fail("schema", "未配置 url", start)

    try:
        async with asyncio.timeout(timeout_seconds):
            async with sse_client(
                server.url,
                headers=server.headers or None,
                timeout=timeout_seconds,
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    init_result = await session.initialize()
                    tools_result = await session.list_tools()
                    return _ok(init_result, tools_result, start)
    except TimeoutError:
        return _fail("handshake_timeout", f"握手超时 ({timeout_seconds}s)", start)
    except Exception as e:  # noqa: BLE001
        return _classify_transport_error(e, start)


# ──────────────────────────────────────────────────────────────
# stdio (via docker exec inside CC sandbox container)
# ──────────────────────────────────────────────────────────────


async def _validate_stdio(
    workspace: Optional[DBWorkspace],
    server: McpServerConfig,
    timeout_seconds: float,
    start: float,
) -> McpValidationResult:
    # 没有显式指定 workspace（如全局自动注入验证）：兜底找一个正在跑的工作区。
    if workspace is None or not workspace.container_name:
        workspace = await _pick_running_workspace()
    if workspace is None or not workspace.container_name:
        return _fail(
            "container_not_running",
            "stdio 验证需要一个正在运行的工作区容器，请先启动任一工作区",
            start,
        )

    cmd_parts = [server.command or "", *(server.args or [])]
    if not cmd_parts[0]:
        return _fail("schema", "stdio 类型缺少 command", start)

    docker = aiodocker.Docker()
    try:
        try:
            container = await docker.containers.get(workspace.container_name)
            info = await container.show()
            if not info.get("State", {}).get("Running"):
                return _fail(
                    "container_not_running",
                    "工作区容器未运行，请先启动",
                    start,
                )
        except Exception as e:  # noqa: BLE001
            return _fail("container_not_running", f"容器查询失败: {e}", start)

        try:
            exec_inst = await container.exec(
                cmd_parts,
                stdin=True,
                stdout=True,
                stderr=True,
                environment=dict(server.env or {}),
            )
        except Exception as e:  # noqa: BLE001
            return _fail("spawn_failed", f"创建 exec 失败: {e}", start)

        try:
            async with asyncio.timeout(timeout_seconds):
                async with exec_inst.start(detach=False) as stream:
                    return await _do_stdio_handshake(stream, start)
        except TimeoutError:
            return _fail("handshake_timeout", f"握手超时 ({timeout_seconds}s)", start)
        except Exception as e:  # noqa: BLE001
            return _classify_transport_error(e, start)
    finally:
        await docker.close()


async def _do_stdio_handshake(stream: Any, start: float) -> McpValidationResult:
    """在已建立的 docker exec stream 上跑 MCP 握手 + tools/list"""
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": _CLIENT_INFO,
        },
    }
    await stream.write_in((json.dumps(init_msg) + "\n").encode("utf-8"))

    init_response = await _read_jsonrpc_response(stream, expected_id=1)
    if init_response is None:
        return _fail("invalid_response", "未收到 initialize 响应", start)
    if "error" in init_response:
        err = init_response["error"]
        return _fail("transport_error", f"initialize 错误: {err}", start)

    init_result = init_response.get("result", {})
    server_info = init_result.get("serverInfo", {})
    capabilities = init_result.get("capabilities", {})

    # 发送 initialized 通知
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    await stream.write_in((json.dumps(initialized_notification) + "\n").encode("utf-8"))

    # 列工具
    list_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    await stream.write_in((json.dumps(list_msg) + "\n").encode("utf-8"))

    tools_response = await _read_jsonrpc_response(stream, expected_id=2)
    tool_names: Optional[List[str]] = None
    if tools_response and "result" in tools_response:
        tools = tools_response["result"].get("tools", [])
        tool_names = [t.get("name", "") for t in tools if t.get("name")]

    return McpValidationResult(
        ok=True,
        server_info={
            "name": server_info.get("name"),
            "version": server_info.get("version"),
            "protocolVersion": init_result.get("protocolVersion"),
        },
        capabilities=capabilities,
        tools=tool_names,
        latency_ms=_elapsed_ms(start),
    )


async def _read_jsonrpc_response(
    stream: Any,
    expected_id: int,
    buffer: Optional[bytearray] = None,
) -> Optional[Dict[str, Any]]:
    """从 docker exec stdout 中读到指定 id 的 JSON-RPC response

    每条 MCP stdio 消息是一行 newline-delimited JSON。
    """
    if buffer is None:
        buffer = bytearray()

    while True:
        msg = await stream.read_out()
        if msg is None:
            return None
        # msg.stream: 1 = stdout, 2 = stderr。stderr 仅记录日志，不参与协议。
        if getattr(msg, "stream", 1) == 2:
            try:
                logger.debug(f"MCP stdio stderr: {bytes(msg.data).decode('utf-8', 'replace').strip()}")
            except Exception:  # noqa: BLE001
                pass
            continue
        buffer.extend(msg.data)
        while b"\n" in buffer:
            line, _, rest = buffer.partition(b"\n")
            buffer.clear()
            buffer.extend(rest)
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                logger.debug(f"非 JSON 输出，跳过: {text[:200]}")
                continue
            if not isinstance(payload, dict):
                continue
            # 通知 (无 id) 跳过；id 不匹配的响应也跳过
            if "id" not in payload:
                continue
            if payload.get("id") != expected_id:
                continue
            return payload


# ──────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────


def _ok(init_result: Any, tools_result: Any, start: float) -> McpValidationResult:
    server_info = getattr(init_result, "serverInfo", None)
    capabilities = getattr(init_result, "capabilities", None)
    tools = getattr(tools_result, "tools", None) or []
    return McpValidationResult(
        ok=True,
        server_info=(
            {
                "name": getattr(server_info, "name", None),
                "version": getattr(server_info, "version", None),
                "protocolVersion": getattr(init_result, "protocolVersion", None),
            }
            if server_info is not None
            else None
        ),
        capabilities=(
            capabilities.model_dump() if hasattr(capabilities, "model_dump") else None
        ),
        tools=[getattr(t, "name", "") for t in tools if getattr(t, "name", None)],
        latency_ms=_elapsed_ms(start),
    )


def _fail(kind: ErrorKind, message: str, start: float) -> McpValidationResult:
    return McpValidationResult(
        ok=False,
        error=message,
        error_kind=kind,
        latency_ms=_elapsed_ms(start),
    )


def _classify_transport_error(exc: BaseException, start: float) -> McpValidationResult:
    """把常见异常分类成 error_kind，便于前端给精准提示"""
    msg = str(exc) or exc.__class__.__name__
    low = msg.lower()
    if "timeout" in low:
        return _fail("handshake_timeout", msg, start)
    if any(k in low for k in ("refused", "unreachable", "name or service", "dns", "resolve")):
        return _fail("transport_error", msg, start)
    return _fail("transport_error", msg, start)


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


async def _pick_running_workspace() -> Optional[DBWorkspace]:
    """挑选任一 active 状态的工作区，用于在没有显式 workspace 时 exec stdio"""
    return await DBWorkspace.filter(status="active").exclude(container_name="").first()
