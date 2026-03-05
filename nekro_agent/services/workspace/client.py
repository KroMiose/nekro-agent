import json
from collections.abc import Awaitable, Callable
from typing import AsyncGenerator, List

import httpx

from nekro_agent.core.logger import get_sub_logger
from nekro_agent.models.db_workspace import DBWorkspace

logger = get_sub_logger("cc_sandbox_client")


class CCSandboxError(Exception):
    pass


class CCSandboxClient:
    def __init__(self, workspace: DBWorkspace, timeout: float = 300.0) -> None:
        self._base_url = workspace.api_endpoint
        self._timeout = timeout
        # 连接/写入超时短（死容器快速失败），读取超时长（支持长任务流式传输）
        self._stream_timeout = httpx.Timeout(
            connect=15.0,
            read=self._timeout,
            write=15.0,
            pool=15.0,
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/health")
                return resp.status_code == 200 and resp.json().get("status") == "healthy"
        except Exception:
            return False

    async def send_message(
        self,
        content: str,
        workspace_id: str = "default",
        source_chat_key: str = "",
        env_vars: "dict[str, str] | None" = None,
    ) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/api/v1/message",
                json={
                    "role": "user",
                    "content": content,
                    "workspace_id": workspace_id,
                    "source_chat_key": source_chat_key,
                    "env_vars": env_vars or {},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                err = data.get("error") or {}
                raise CCSandboxError(f"CC 响应错误: {err.get('message', 'unknown')}")
            return str(data.get("message", ""))

    async def stream_message(
        self,
        content: str,
        workspace_id: str = "default",
        source_chat_key: str = "",
        on_queued: Callable[[dict], Awaitable[None]] | None = None,
        env_vars: "dict[str, str] | None" = None,
    ) -> AsyncGenerator[str | dict, None]:
        logger.debug(
            f"[cc_client] Opening SSE stream: base_url={self._base_url} "
            f"workspace={workspace_id} source_chat_key={source_chat_key!r} "
            f"content_len={len(content)} read_timeout={self._stream_timeout.read}"
        )
        async with httpx.AsyncClient(timeout=self._stream_timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/v1/message/stream",
                json={
                    "role": "user",
                    "content": content,
                    "workspace_id": workspace_id,
                    "source_chat_key": source_chat_key,
                    "env_vars": env_vars or {},
                },
            ) as resp:
                resp.raise_for_status()
                chunk_count = 0
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if not raw:
                        continue
                    try:
                        chunk = json.loads(raw)
                    except Exception:
                        logger.debug(
                            f"[cc_client] SSE JSON parse failed, skipping: "
                            f"raw={raw[:200]!r} workspace={workspace_id}"
                        )
                        continue
                    chunk_type = chunk.get("type")
                    if chunk_type == "chunk":
                        chunk_count += 1
                        yield chunk.get("chunk", "")
                    elif chunk_type == "queued":
                        if on_queued is not None:
                            await on_queued(chunk)
                    elif chunk_type in ("tool_call", "tool_result"):
                        yield chunk
                    elif chunk_type == "error":
                        err_msg = chunk.get("message", "stream error")
                        logger.warning(
                            f"[cc_client] SSE error event: {err_msg!r} "
                            f"workspace={workspace_id} source_chat_key={source_chat_key!r}"
                        )
                        raise CCSandboxError(err_msg)
                logger.debug(
                    f"[cc_client] SSE stream closed normally: "
                    f"workspace={workspace_id} chunks={chunk_count}"
                )

    async def reset_session(self, workspace_id: str = "default") -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self._base_url}/api/v1/workspaces/{workspace_id}/session/reset")
            resp.raise_for_status()

    async def get_tools(self) -> List[str]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self._base_url}/api/v1/capabilities/tools")
            resp.raise_for_status()
            data = resp.json()
            return list(data.get("tools") or [])

    async def refresh_tools(self) -> List[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self._base_url}/api/v1/capabilities/tools/refresh")
            resp.raise_for_status()
            data = resp.json()
            return list(data.get("tools") or [])

    async def get_sandbox_status(self, workspace_id: str = "default") -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self._base_url}/api/v1/workspaces/{workspace_id}")
            if resp.status_code == 200:
                return dict(resp.json())
            return {}

    async def get_cc_version(self) -> str:
        """从 /api/v1/status 获取沙盒版本号。"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/v1/status")
                if resp.status_code == 200:
                    return str(resp.json().get("version") or "unknown")
        except Exception:
            pass
        return "unknown"

    async def get_sandbox_versions(self) -> "dict[str, str | None]":
        """从 /api/v1/status 一次获取沙盒版本与 Claude Code CLI 版本。"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/api/v1/status")
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "cc_version": str(data.get("version") or "unknown"),
                        "claude_code_version": data.get("claude_version") or None,
                    }
        except Exception:
            pass
        return {"cc_version": None, "claude_code_version": None}

    async def get_workspace_queue(self, workspace_id: str = "default") -> dict:
        """获取工作区任务队列状态（当前任务 + 等待列表）。"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/api/v1/workspaces/{workspace_id}/queue")
                if resp.status_code == 200:
                    return dict(resp.json())
        except Exception:
            pass
        return {"workspace_id": workspace_id, "current_task": None, "queued_tasks": [], "queue_length": 0}

    async def force_cancel_current_task(self, workspace_id: str = "default") -> bool:
        """强制取消工作区当前正在运行的任务。"""
        logger.info(f"[cc_client] Requesting force cancel: workspace={workspace_id}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(f"{self._base_url}/api/v1/workspaces/{workspace_id}/queue/current")
                if resp.status_code == 200:
                    cancelled = bool(resp.json().get("cancelled", False))
                    logger.info(f"[cc_client] Force cancel result: cancelled={cancelled} workspace={workspace_id}")
                    return cancelled
                logger.warning(f"[cc_client] Force cancel unexpected status: {resp.status_code} workspace={workspace_id}")
        except Exception as e:
            logger.warning(f"[cc_client] Force cancel failed: {e} workspace={workspace_id}")
        return False

    async def get_pending_results(self, workspace_id: str = "default") -> list[dict]:
        """取出并消费指定工作区的所有待投递结果（消费后从 CC 暂存区移除）。

        用于 NA 重启后恢复 CC 在断线期间完成的任务结果。
        返回 list[dict]，每条包含: id, workspace_id, source_chat_key, result, created_at, expires_at
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self._base_url}/api/v1/workspaces/{workspace_id}/pending-results"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return list(data.get("results") or [])
        except Exception:
            pass
        return []
